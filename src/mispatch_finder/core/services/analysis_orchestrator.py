from __future__ import annotations

from dataclasses import asdict

from ..domain.models import AnalysisResult, Vulnerability
from ..domain.prompt import build_prompt
from ..ports import (
    LLMPort,
    LoggerPort,
    MCPServerPort,
    RepositoryPort,
    TokenGeneratorPort,
    VulnerabilityDataPort,
)
from .diff_service import DiffService
from .json_extractor import JsonExtractor


class AnalysisOrchestrator:
    """Orchestrates the complete analysis workflow.

    Coordinates between domain services and infrastructure adapters
    to perform vulnerability analysis.
    """

    def __init__(
        self,
        *,
        vuln_data: VulnerabilityDataPort,
        repo: RepositoryPort,
        mcp: MCPServerPort,
        llm: LLMPort,
        token_gen: TokenGeneratorPort,
        logger: LoggerPort,
        diff_service: DiffService,
        json_extractor: JsonExtractor,
    ) -> None:
        self._vuln_data = vuln_data
        self._repo = repo
        self._mcp = mcp
        self._llm = llm
        self._token_gen = token_gen
        self._logger = logger
        self._diff_service = diff_service
        self._json_extractor = json_extractor

    def analyze(self, *, ghsa: str, force_reclone: bool = False) -> dict[str, object]:
        """Execute complete analysis workflow for a GHSA.

        Args:
            ghsa: GHSA identifier
            force_reclone: Whether to force re-clone repository

        Returns:
            Analysis result as dictionary
        """
        mcp_token = self._token_gen.generate()
        mcp_ctx = None

        try:
            # 1) Fetch GHSA metadata
            vuln = self._vuln_data.fetch_metadata(ghsa)
            self._logger.info("ghsa_meta", payload={
                "type": "ghsa_meta",
                "ghsa": ghsa,
                "vulnerability": {
                    "repo_url": vuln.repository.url,
                    "commit": vuln.commit_hash,
                    "cve_id": vuln.cve_id,
                    "severity": vuln.severity,
                },
            })

            # 2) Prepare repositories
            current, previous = self._repo.prepare_workdirs(
                repo_url=vuln.repository.url,
                commit=vuln.commit_hash,
                force_reclone=force_reclone,
            )
            self._logger.info("repos_prepared", payload={
                "type": "repos_prepared",
                "workdirs": {
                    "current": str(current) if current else None,
                    "previous": str(previous) if previous else None,
                },
            })

            # 3) Generate diff
            base_worktree = current or previous
            diff_result = self._diff_service.generate_diff(
                workdir=base_worktree,
                commit=vuln.commit_hash,
            )
            self._logger.info("diff_built", payload={
                "type": "diff_built",
                "full_len": diff_result.full_len,
                "included_len": diff_result.included_len,
                "truncated": diff_result.was_truncated,
            })

            # 4) Start MCP servers + tunnel
            mcp_ctx = self._mcp.start_servers(
                current_workdir=current,
                previous_workdir=previous,
                auth_token=mcp_token,
            )
            self._logger.info("mcp_ready", payload={
                "type": "mcp_ready",
                "local_url": mcp_ctx.local_url,
                "public_url": mcp_ctx.public_url,
                "has_current": mcp_ctx.has_current,
                "has_previous": mcp_ctx.has_previous,
            })

            # 5) Build prompt and call LLM
            prompt = build_prompt(
                ghsa=ghsa,
                repo_url=vuln.repository.url,
                commit=vuln.commit_hash,
                has_previous=mcp_ctx.has_previous,
                has_current=mcp_ctx.has_current,
                diff_text=diff_result.truncated_text,
            )

            raw_text = self._llm.call(
                prompt=prompt,
                mcp_url=mcp_ctx.public_url + '/mcp',
                mcp_token=mcp_token,
            )

            # 6) Extract JSON from LLM response
            extracted_json = self._json_extractor.extract(raw_text)

            # 7) Build result
            result = AnalysisResult(
                ghsa=ghsa,
                provider="",  # Will be filled from logs
                model="",  # Will be filled from logs
                verdict=None,
                severity=None,
                rationale=None,
                evidence=None,
                poc_idea=None,
                raw_text=extracted_json,
            )
            payload = asdict(result)
            self._logger.info("final_result", payload={
                "type": "final_result",
                "result": payload,
            })

            return payload

        finally:
            if mcp_ctx is not None:
                try:
                    mcp_ctx.cleanup()
                except Exception:
                    self._logger.exception("mcp_cleanup_error")
