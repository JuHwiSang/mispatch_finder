from __future__ import annotations

from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from fastmcp import FastMCP
from repo_read_mcp import make_mcp_server as make_repo_mcp


@dataclass
class ServerMap:
    """Mapping of mounted prefix to FastMCP servers (dataclass variant).

    Only repo_read_mcp servers are mounted for previous/current states.
    previous_repo is optional since a parent commit may be absent.
    current_repo is expected.
    """
    current_repo: FastMCP | None = None
    previous_repo: FastMCP | None = None


def create_child_servers(
    *,
    workdir_current: Optional[Path],
    workdir_previous: Optional[Path],
) -> ServerMap:
    """Instantiate child MCP servers for repo_read_mcp only.

    Returns mapping object with optional previous/current repo servers.
    """
    servers = ServerMap()

    if workdir_current:
        servers.current_repo = make_repo_mcp(name="current-repo", project_path=str(workdir_current))

    if workdir_previous:
        servers.previous_repo = make_repo_mcp(name="previous-repo", project_path=str(workdir_previous))

    return servers


