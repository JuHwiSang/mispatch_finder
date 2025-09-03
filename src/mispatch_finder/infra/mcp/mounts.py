from __future__ import annotations

from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from fastmcp import FastMCP
from repo_read_mcp import make_mcp_server as make_repo_mcp
from jsts_debugger import make_mcp_server as make_debug_mcp


def _has_node_project(root: Path) -> bool:
    return (root / "package.json").exists()


@dataclass
class ServerMap:
    """Mapping of mounted prefix to FastMCP servers (dataclass variant).

    pre_repo and pre_debug are optional since a parent commit or JS/TS project may be absent.
    post_repo is expected, post_debug may be absent if no JS/TS project.
    """
    post_repo: FastMCP | None = None
    post_debug: FastMCP | None = None
    pre_repo: FastMCP | None = None
    pre_debug: FastMCP | None = None


def create_child_servers(
    *,
    workdir_post: Optional[Path],
    workdir_pre: Optional[Path],
) -> ServerMap:
    """Instantiate child MCP servers for repo_read_mcp and jsts_debugger.

    Returns dict keyed by prefix: {"pre/repo": FastMCP, "pre/debug": FastMCP, ...}
    Missing entries are simply omitted.
    """
    servers = ServerMap()

    if workdir_post:
        servers.post_repo = make_repo_mcp(name="post-repo", project_path=str(workdir_post))
        if _has_node_project(workdir_post):
            servers.post_debug = make_debug_mcp(name="post-debug", project_path=str(workdir_post))

    if workdir_pre:
        servers.pre_repo = make_repo_mcp(name="pre-repo", project_path=str(workdir_pre))
        if _has_node_project(workdir_pre):
            servers.pre_debug = make_debug_mcp(name="pre-debug", project_path=str(workdir_pre))

    return servers


