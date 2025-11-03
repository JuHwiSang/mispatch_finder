from __future__ import annotations

from ..ports import MCPServerPort, VulnerabilityDataPort, RepositoryPort, TokenGeneratorPort


class MCPUseCase:
    """Use case for starting standalone MCP server.

    Provides a persistent MCP server that can be accessed externally or internally,
    with optional authentication. Prepares repository workdirs from GHSA ID.
    """

    def __init__(
        self,
        *,
        mcp_server: MCPServerPort,
        vuln_data: VulnerabilityDataPort,
        repo: RepositoryPort,
        token_gen: TokenGeneratorPort,
    ) -> None:
        self._mcp_server = mcp_server
        self._vuln_data = vuln_data
        self._repo = repo
        self._token_gen = token_gen

    def execute(
        self,
        *,
        ghsa: str,
        port: int,
        use_tunnel: bool,
        use_auth: bool,
        force_reclone: bool = False,
    ) -> dict[str, str | None]:
        """Start MCP server with specified configuration.

        Args:
            ghsa: GitHub Security Advisory ID
            port: Port number for the MCP server
            use_tunnel: Whether to expose server via external tunnel
            use_auth: Whether to enable authentication (generates random token)
            force_reclone: Force re-clone of repositories (default: False)

        Returns:
            Dictionary with server info:
                - local_url: Local server URL
                - public_url: Public tunnel URL (if use_tunnel=True)
                - auth_token: Authentication token (if use_auth=True)
        """
        # Fetch vulnerability metadata
        vuln = self._vuln_data.fetch_metadata(ghsa)

        # Prepare repository workdirs
        repo_url = vuln.repository.url
        current_workdir, previous_workdir = self._repo.prepare_workdirs(
            repo_url=repo_url,
            commit=vuln.commit_hash,
            force_reclone=force_reclone,
        )

        # Generate authentication token if requested
        auth_token = self._token_gen.generate() if use_auth else "no-auth-required"

        # Start MCP server
        ctx = self._mcp_server.start_servers(
            current_workdir=current_workdir,
            previous_workdir=previous_workdir,
            auth_token=auth_token,
            port=port,
            use_tunnel=use_tunnel,
        )

        # Return server information
        return {
            "local_url": ctx.local_url,
            "public_url": ctx.public_url,
            "auth_token": auth_token if use_auth else None,
        }
