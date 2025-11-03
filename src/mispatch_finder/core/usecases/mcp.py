from __future__ import annotations

import secrets
from pathlib import Path

from ..ports import MCPServerPort


class MCPUseCase:
    """Use case for starting standalone MCP server.

    Provides a persistent MCP server that can be accessed externally or internally,
    with optional authentication.
    """

    def __init__(
        self,
        *,
        mcp_server: MCPServerPort,
    ) -> None:
        self._mcp_server = mcp_server

    def execute(
        self,
        *,
        port: int,
        use_tunnel: bool,
        use_auth: bool,
        current_workdir: Path | None = None,
        previous_workdir: Path | None = None,
    ) -> dict[str, str | None]:
        """Start MCP server with specified configuration.

        Args:
            port: Port number for the MCP server
            use_tunnel: Whether to expose server via external tunnel
            use_auth: Whether to enable authentication (generates random token)
            current_workdir: Path to current repository (optional)
            previous_workdir: Path to previous repository (optional)

        Returns:
            Dictionary with server info:
                - local_url: Local server URL
                - public_url: Public tunnel URL (if use_tunnel=True)
                - auth_token: Authentication token (if use_auth=True)
        """
        # Generate authentication token if requested
        auth_token = secrets.token_urlsafe(32) if use_auth else "no-auth-required"

        # Start MCP server
        ctx = self._mcp_server.start_servers(
            current_workdir=current_workdir,
            previous_workdir=previous_workdir,
            auth_token=auth_token,
            use_tunnel=use_tunnel,
        )

        # Return server information
        return {
            "local_url": ctx.local_url,
            "public_url": ctx.public_url,
            "auth_token": auth_token if use_auth else None,
        }
