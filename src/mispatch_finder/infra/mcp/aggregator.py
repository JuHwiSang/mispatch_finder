from __future__ import annotations

import threading
from typing import Tuple

from fastmcp import FastMCP
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier

from mispatch_finder.infra.mcp.mounts import ServerMap


class _ServerHandle:
    def __init__(self, app: FastMCP, thread: threading.Thread, port: int) -> None:
        self.app = app
        self.thread = thread
        self.port = port


def start_main_server(servers: ServerMap, *, auth_token: str, port: int = 18080) -> Tuple[str, _ServerHandle]:
    """Start the main FastMCP app and mount children under prefixes.

    Returns (local_url, server_handle)
    """
    auth = StaticTokenVerifier(tokens={auth_token: {"client_id": "mispatch-run"}})
    app = FastMCP(name="mispatch-finder", instructions="Mispatch Finder aggregator", auth=auth)

    if servers.post_repo:
        app.mount(prefix="post_repo", server=servers.post_repo)
    if servers.post_debug:
        app.mount(prefix="post_debug", server=servers.post_debug)
    if servers.pre_repo:
        app.mount(prefix="pre_repo", server=servers.pre_repo)
    if servers.pre_debug:
        app.mount(prefix="pre_debug", server=servers.pre_debug)

    # TODO: add auth middleware when exposing via SSE HTTP server

    def run_app() -> None:
        # Start blocking HTTP/SSE server
        app.run(transport="streamable-http", port=port)

    t = threading.Thread(target=run_app, daemon=True)
    t.start()
    local_url = f"http://127.0.0.1:{port}"
    return local_url, _ServerHandle(app=app, thread=t, port=port)


def stop_main_server(handle: _ServerHandle) -> None:
    # FastMCP currently lacks a public programmatic shutdown; rely on daemon thread exit on process end.
    _ = handle


