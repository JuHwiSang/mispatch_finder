from __future__ import annotations

import logging
import re
import threading
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier
from fastmcp.server.middleware.logging import LoggingMiddleware
from repo_read_mcp import make_mcp_server as make_repo_mcp

from ..core.ports import MCPServerContext, MCPServerPort, LoggerPort
from ..shared.list_tools import list_tools
from .mcp.tunnel import Tunnel
from .mcp.wiretap_logging import WiretapLoggingMiddleware

# Keep standard logger for low-level debug logs (tool listing, etc.)
debug_logger = logging.getLogger(__name__)


class MCPServer:
    def __init__(self, *, port: int = 18080, logger: LoggerPort) -> None:
        self._port = port
        self._logger = logger

    def start_servers(
        self,
        *,
        current_workdir: Path | None,
        previous_workdir: Path | None,
        auth_token: str,
    ) -> MCPServerContext:
        # 1) Create child repo servers
        current_repo = None
        previous_repo = None
        
        if current_workdir:
            current_repo = make_repo_mcp(name="current-repo", project_path=str(current_workdir))
        
        if previous_workdir:
            previous_repo = make_repo_mcp(name="previous-repo", project_path=str(previous_workdir))

        # 2) Create and start aggregator
        auth = StaticTokenVerifier(tokens={auth_token: {"client_id": "mispatch-run"}})
        app = FastMCP(
            name="mispatch-finder",
            instructions="Mispatch Finder aggregator",
            auth=auth,
            stateless_http=True,
        )
        app.add_middleware(LoggingMiddleware(include_payloads=True))
        app.add_middleware(WiretapLoggingMiddleware())

        if current_repo:
            app.mount(prefix="current_repo", server=current_repo)
        if previous_repo:
            app.mount(prefix="previous_repo", server=previous_repo)

        debug_logger.debug(f"Mounted tools: {list_tools(app)}")

        # Start aggregator in daemon thread
        def run_app() -> None:
            app.run(transport="streamable-http", port=self._port)

        thread = threading.Thread(target=run_app, daemon=True)
        thread.start()
        local_url = f"http://127.0.0.1:{self._port}"

        self._logger.info(
            "aggregator_started",
            type="aggregator_started",
            local_url=local_url,
            mounted={
                "current_repo": bool(current_repo),
                "previous_repo": bool(previous_repo),
            },
        )

        # 3) Start tunnel
        m = re.match(r"^https?://([^/:]+):(\d+)$", local_url)
        if not m:
            raise ValueError(f"Invalid local URL: {local_url}")
        host, port = m.group(1), int(m.group(2))
        public_url, tunnel_handle = Tunnel.start_tunnel(host, port)

        self._logger.info(
            "tunnel_started",
            type="tunnel_started",
            public_url=public_url,
        )

        # 4) Build context with cleanup
        ctx = MCPServerContext(
            local_url=local_url,
            public_url=public_url,
            has_current=bool(current_repo),
            has_previous=bool(previous_repo),
        )

        def cleanup() -> None:
            self._logger.info("mcp_cleanup_start")
            try:
                tunnel_handle.stop_tunnel()
            except Exception:
                self._logger.exception("tunnel_stop_error")
            # FastMCP has no shutdown API; daemon thread will exit on process end
            self._logger.info("mcp_cleanup_done")

        ctx.cleanup = cleanup
        return ctx
