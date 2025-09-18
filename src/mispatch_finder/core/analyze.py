from __future__ import annotations

import secrets
from dataclasses import asdict
import re
import logging
from typing import Optional

from ..app.models import AnalysisRequest, AnalysisResult
from ..app.config import get_cache_dir
from ..infra.cve import fetch_ghsa_metadata
from ..infra.git_repo import prepare_repos
from ..infra.git_repo import get_commit_diff_text
from ..infra.mcp.mounts import create_child_servers
from ..infra.mcp.aggregator import start_main_server, stop_main_server, _ServerHandle
from ..infra.mcp.tunnel import Tunnel
from ..infra.llm import call_llm
from ..app.prompts import build_prompt
from ..app.config import get_prompt_diff_max_chars

logger = logging.getLogger(__name__)


class Analyzer:
    """Session-scoped analyzer with an ephemeral MCP auth token.

    Token is generated per-instance and never persisted.
    """

    def __init__(self) -> None:
        self._mcp_token: str = secrets.token_urlsafe(32)
        self._tunnel_handle: Optional[Tunnel] = None
        self._main_handle: Optional[_ServerHandle] = None
        self._closed: bool = False

    @property
    def mcp_token(self) -> str:
        return self._mcp_token

    def analyze(self, req: AnalysisRequest) -> dict:
        try:
            # 1) GHSA metadata
            meta = fetch_ghsa_metadata(req.ghsa, github_token=req.github_token)
            logger.info("ghsa_meta", extra={
                "payload": {
                    "type": "ghsa_meta",
                    "ghsa": req.ghsa,
                    "meta": {
                        "repo_url": meta.repo_url,
                        "commit": meta.commit,
                        "parent_commit": meta.parent_commit,
                    },
                }
            })

            # 2) repos
            cache_dir = get_cache_dir()
            post, pre = prepare_repos(
                cache_dir=cache_dir,
                repo_url=meta.repo_url,
                commit=meta.commit,
                parent_commit=meta.parent_commit,
                force_reclone=req.force_reclone,
            )
            logger.info("repos_prepared", extra={
                "payload": {
                    "type": "repos_prepared",
                    "workdirs": {"post": str(post) if post else None, "pre": str(pre) if pre else None},
                }
            })

            # 3) Build diff (may be large) and prepare MCP
            base_worktree = post or pre
            diff_full = ""
            if base_worktree is not None:
                diff_full = get_commit_diff_text(base_repo_dir=base_worktree, commit=meta.commit)
            max_chars = get_prompt_diff_max_chars()
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

            # MCP mount & server
            servers = create_child_servers(workdir_post=post, workdir_pre=pre)
            local_url, main_handle = start_main_server(servers, auth_token=self._mcp_token)
            self._main_handle = main_handle
            logger.info("aggregator_started", extra={
                "payload": {
                    "type": "aggregator_started",
                    "local_url": local_url,
                    "mounted": {
                        "post_repo": bool(servers.post_repo),
                        "post_debug": bool(servers.post_debug),
                        "pre_repo": bool(servers.pre_repo),
                        "pre_debug": bool(servers.pre_debug),
                    },
                }
            })

            # 4) tunnel
            m = re.match(r"^https?://([^/:]+):(\d+)$", local_url)
            if not m:
                raise ValueError(f"Invalid local URL: {local_url}")
            host, port = m.group(1), int(m.group(2))
            public_url, tunnel_handle = Tunnel.start_tunnel(host, port)
            self._tunnel_handle = tunnel_handle
            logger.info("tunnel_started", extra={
                "payload": {
                    "type": "tunnel_started",
                    "public_url": public_url,
                }
            })
            # 5) LLM call
            prompt = build_prompt(
                req.ghsa,
                {"repo_url": meta.repo_url, "commit": meta.commit},
                has_pre=pre is not None,
                has_post=post is not None,
                diff_text=diff_text,
            )
            logger.info("llm_input", extra={
                "payload": {
                    "type": "llm_input",
                    "provider": req.provider,
                    "model": req.model,
                    "prompt_len": len(prompt),
                    "prompt": prompt,
                }
            })
            raw_text = call_llm(
                provider=req.provider,
                model=req.model,
                api_key=req.api_key,
                mcp_url=public_url + '/mcp',
                mcp_token=self._mcp_token,
                prompt=prompt,
                usage_sink=None,
            )
            logger.info("llm_output", extra={
                "payload": {
                    "type": "llm_output",
                    "raw_text_len": len(raw_text) if raw_text is not None else 0,
                    "raw_text": raw_text,
                }
            })

            result = AnalysisResult(
                ghsa=req.ghsa,
                provider=req.provider,
                model=req.model,
                verdict=None,
                severity=None,
                rationale=None,
                evidence=None,
                poc_idea=None,
                raw_text=raw_text,
            )
            payload = asdict(result)

            logger.info("final_result", extra={"payload": {"type": "final_result", "result": payload}})

            return payload
        finally:
            self.close()

    def close(self) -> None:
        """Close any resources started by this Analyzer.

        Idempotent and safe to call multiple times.
        """
        if self._closed:
            return
        
        logger.info("closing analyzer")
        # Stop tunnel first to avoid exposing a useless public endpoint
        if self._tunnel_handle is not None:
            try:
                self._tunnel_handle.stop_tunnel()
            except Exception:
                logger.exception("analyzer_close_tunnel_error")
            finally:
                self._tunnel_handle = None
        # Stop main MCP server (best-effort; currently a no-op in FastMCP)
        if self._main_handle is not None:
            try:
                stop_main_server(self._main_handle)
            except Exception:
                logger.exception("analyzer_close_main_server_error")
            finally:
                self._main_handle = None
                
        logger.info("analyzer closed")
        self._closed = True


