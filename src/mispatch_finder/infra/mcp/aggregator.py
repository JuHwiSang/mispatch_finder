from __future__ import annotations

import threading
from typing import Tuple

from fastmcp import FastMCP
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier
from fastmcp.server.middleware.logging import LoggingMiddleware
from mispatch_finder.infra.mcp.wiretap_logging import WiretapLoggingMiddleware

from mispatch_finder.infra.mcp.mounts import ServerMap
from mispatch_finder.shared.list_tools import list_tools


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
    app = FastMCP(name="mispatch-finder", instructions="Mispatch Finder aggregator", auth=auth, stateless_http=True)
    app.add_middleware(LoggingMiddleware(include_payloads=True))
    app.add_middleware(WiretapLoggingMiddleware(logger_name=__name__))

    handle = _ServerHandle(app=app, thread=threading.current_thread(), port=port)

    if servers.current_repo:
        app.mount(prefix="current_repo", server=servers.current_repo)
    if servers.previous_repo:
        app.mount(prefix="previous_repo", server=servers.previous_repo)

    # TODO: add auth middleware when exposing via SSE HTTP server
    
    print("List tools: ", list_tools(app))

    def run_app() -> None:
        # Start blocking HTTP/SSE server
        app.run(transport="streamable-http", port=port)

    t = threading.Thread(target=run_app, daemon=True)
    t.start()
    local_url = f"http://127.0.0.1:{port}"
    handle.thread = t
    return local_url, handle


def stop_main_server(handle: _ServerHandle) -> None:
    # FastMCP currently lacks a public programmatic shutdown; rely on daemon thread exit on process end.
    _ = handle

    return None
