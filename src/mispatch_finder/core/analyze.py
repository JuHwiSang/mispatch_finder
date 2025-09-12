from __future__ import annotations

import secrets
from dataclasses import asdict
import re
from typing import Any, Dict

from ..app.models import AnalysisRequest, AnalysisResult
from ..app.config import get_cache_dir
from ..infra.cve import fetch_ghsa_metadata
from ..infra.git_repo import prepare_repos
from ..infra.git_repo import get_commit_diff_text
from ..infra.mcp.mounts import create_child_servers
from ..infra.mcp.aggregator import start_main_server, stop_main_server
from ..infra.mcp.tunnel import Tunnel
from ..infra.llm import call_llm
from ..app.prompts import build_prompt
from ..app.config import get_prompt_diff_max_chars


class Analyzer:
    """Session-scoped analyzer with an ephemeral MCP auth token.

    Token is generated per-instance and never persisted.
    """

    def __init__(self) -> None:
        self._mcp_token: str = secrets.token_urlsafe(32)

    @property
    def mcp_token(self) -> str:
        return self._mcp_token

    def analyze(self, req: AnalysisRequest) -> Dict[str, Any]:
        # 1) GHSA metadata
        meta = fetch_ghsa_metadata(req.ghsa, github_token=req.github_token)

        # 2) repos
        cache_dir = get_cache_dir()
        post, pre = prepare_repos(
            cache_dir=cache_dir,
            repo_url=meta.repo_url,
            commit=meta.commit,
            parent_commit=meta.parent_commit,
            force_reclone=req.force_reclone,
        )
        print('\nrepo prepared')

        # 3) Build diff (may be large) and prepare MCP
        # Use the actual worktree as the repo dir; GitPython can open a worktree path.
        base_worktree = post or pre
        diff_full = ""
        if base_worktree is not None:
            diff_full = get_commit_diff_text(base_repo_dir=base_worktree, commit=meta.commit)
        max_chars = get_prompt_diff_max_chars()
        diff_text = diff_full
        if len(diff_full) > max_chars:
            # Middle truncate to keep head and tail
            head = diff_full[: max_chars // 2]
            tail = diff_full[-(max_chars - len(head)) :]
            diff_text = head + "\n...\n" + tail
        print('\ndiff prepared')

        # MCP mount & server
        servers = create_child_servers(workdir_post=post, workdir_pre=pre)
        print('\nservers created')
        local_url, main_handle = start_main_server(servers, auth_token=self._mcp_token)
        print('\nmain server started')

        # 4) tunnel
        m = re.match(r"^https?://([^/:]+):(\d+)$", local_url)
        if not m:
            raise ValueError(f"Invalid local URL: {local_url}")
        else:
            host, port = m.group(1), int(m.group(2))
        public_url, tunnel_handle = Tunnel.start_tunnel(host, port)
        print('\ntunnel started')
        # 5) LLM call (prompt TBD)
        # meta is GHSAInfo; build_prompt expects Dict[str, str]. Create a narrow view.
        prompt = build_prompt(
            req.ghsa,
            {"repo_url": meta.repo_url, "commit": meta.commit},
            has_pre=pre is not None,
            has_post=post is not None,
            diff_text=diff_text,
        )
        print('\nprompt built')
        print('------------PROMPT START-----------')
        print(prompt)
        print('------------PROMPT END-----------')
        raw_text = call_llm(
            provider=req.provider,
            model=req.model,
            api_key=req.api_key,
            mcp_url=public_url + '/mcp',
            mcp_token=self._mcp_token,
            prompt=prompt,
        )
        print('\nllm called')
        # Teardown
        try:
            tunnel_handle.stop_tunnel()
        finally:
            stop_main_server(main_handle)

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
        return asdict(result)


