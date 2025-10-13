from __future__ import annotations

import logging
from dataclasses import asdict

from ..domain.models import AnalysisResult
from ..domain.prompt import build_prompt
from ..ports import (
    VulnerabilityRepositoryPort,
    RepositoryPort,
    MCPServerPort,
    LLMPort,
    ResultStorePort,
    TokenGeneratorPort,
)

logger = logging.getLogger(__name__)


class RunAnalysisUseCase:
    def __init__(
        self,
        *,
        vuln_repo: VulnerabilityRepositoryPort,
        repo: RepositoryPort,
        mcp: MCPServerPort,
        llm: LLMPort,
        store: ResultStorePort,
        token_gen: TokenGeneratorPort,
        prompt_diff_max_chars: int,
    ) -> None:
        self._vuln_repo = vuln_repo
        self._repo = repo
        self._mcp = mcp
        self._llm = llm
        self._store = store
        self._token_gen = token_gen
        self._prompt_diff_max_chars = prompt_diff_max_chars

    def execute(self, *, ghsa: str, force_reclone: bool = False) -> dict:
        mcp_token = self._token_gen.generate()
        mcp_ctx = None

        try:
            # 1) Fetch GHSA metadata
            meta = self._vuln_repo.fetch_metadata(ghsa)
            logger.info("ghsa_meta", extra={
                "payload": {
                    "type": "ghsa_meta",
                    "ghsa": ghsa,
                    "meta": {
                        "repo_url": meta.repo_url,
                        "commit": meta.commit,
                        "parent_commit": meta.parent_commit,
                    },
                }
            })

            # 2) Prepare repos
            current, previous = self._repo.prepare_workdirs(
                repo_url=meta.repo_url,
                commit=meta.commit,
                force_reclone=force_reclone,
            )
            logger.info("repos_prepared", extra={
                "payload": {
                    "type": "repos_prepared",
                    "workdirs": {
                        "current": str(current) if current else None,
                        "previous": str(previous) if previous else None,
                    },
                }
            })

            # 3) Build diff
            base_worktree = current or previous
            diff_full = ""
            if base_worktree is not None:
                diff_full = self._repo.get_diff(workdir=base_worktree, commit=meta.commit)
            
            max_chars = self._prompt_diff_max_chars
            diff_text = diff_full
            if len(diff_full) > max_chars:
                head = diff_full[: max_chars // 2]
                tail = diff_full[-(max_chars - len(head)) :]
                diff_text = head + "\n...\n" + tail
            
            logger.info("diff_built", extra={
                "payload": {
                    "type": "diff_built",
                    "full_len": len(diff_full),
                    "included_len": len(diff_text),
                    "truncated": len(diff_full) > max_chars,
                }
            })

            # 4) Start MCP servers + tunnel
            mcp_ctx = self._mcp.start_servers(
                current_workdir=current,
                previous_workdir=previous,
                auth_token=mcp_token,
            )
            logger.info("mcp_ready", extra={
                "payload": {
                    "type": "mcp_ready",
                    "local_url": mcp_ctx.local_url,
                    "public_url": mcp_ctx.public_url,
                    "has_current": mcp_ctx.has_current,
                    "has_previous": mcp_ctx.has_previous,
                }
            })

            # 5) Build prompt and call LLM
            prompt = build_prompt(
                ghsa=ghsa,
                repo_url=meta.repo_url,
                commit=meta.commit,
                has_previous=mcp_ctx.has_previous,
                has_current=mcp_ctx.has_current,
                diff_text=diff_text,
            )
            
            # LLM adapter logs provider/model info internally
            raw_text = self._llm.call(
                prompt=prompt,
                mcp_url=mcp_ctx.public_url + '/mcp',
                mcp_token=mcp_token,
            )

            # 6) Build result (provider/model will be extracted from logs)
            result = AnalysisResult(
                ghsa=ghsa,
                provider="",  # Will be filled from logs
                model="",  # Will be filled from logs
                verdict=None,
                severity=None,
                rationale=None,
                evidence=None,
                poc_idea=None,
                raw_text=raw_text,
            )
            payload = asdict(result)
            logger.info("final_result", extra={"payload": {"type": "final_result", "result": payload}})

            # 7) Persist
            self._store.save(ghsa, payload)

            return payload
        finally:
            if mcp_ctx is not None:
                try:
                    mcp_ctx.cleanup()
                except Exception:
                    logger.exception("mcp_cleanup_error")
