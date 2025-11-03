"""Tests for MCPUseCase."""
from pathlib import Path

from mispatch_finder.core.usecases.mcp import MCPUseCase

from tests.mispatch_finder.core.usecases.conftest import FakeMCP


class TestMCPUseCase:
    """Tests for MCPUseCase."""

    def test_execute_with_tunnel_and_auth(self):
        """Test MCP server start with tunnel and authentication."""
        mcp = FakeMCP()
        uc = MCPUseCase(mcp_server=mcp)

        result = uc.execute(
            port=8080,
            use_tunnel=True,
            use_auth=True,
            current_workdir=Path("/fake/current"),
            previous_workdir=Path("/fake/previous"),
        )

        # Check that tunnel was enabled
        assert mcp.last_use_tunnel is True

        # Check result structure
        assert result["local_url"] == "http://127.0.0.1:18080"
        assert result["public_url"] == "https://test.lhr.life"
        assert result["auth_token"] is not None
        assert len(result["auth_token"]) > 0  # Random token generated

    def test_execute_without_tunnel(self):
        """Test MCP server start without tunnel (internal mode)."""
        mcp = FakeMCP()
        uc = MCPUseCase(mcp_server=mcp)

        result = uc.execute(
            port=8080,
            use_tunnel=False,
            use_auth=False,
            current_workdir=Path("/fake/current"),
            previous_workdir=None,
        )

        # Check that tunnel was disabled
        assert mcp.last_use_tunnel is False

        # Check result structure
        assert result["local_url"] == "http://127.0.0.1:18080"
        assert result["public_url"] is None  # No public URL when tunnel disabled
        assert result["auth_token"] is None  # No auth token when auth disabled

    def test_execute_without_auth(self):
        """Test MCP server start with tunnel but without authentication."""
        mcp = FakeMCP()
        uc = MCPUseCase(mcp_server=mcp)

        result = uc.execute(
            port=8080,
            use_tunnel=True,
            use_auth=False,
            current_workdir=None,
            previous_workdir=None,
        )

        # Check result structure
        assert result["local_url"] == "http://127.0.0.1:18080"
        assert result["public_url"] == "https://test.lhr.life"
        assert result["auth_token"] is None  # No auth token when auth disabled

    def test_auth_token_generation(self):
        """Test that auth tokens are randomly generated."""
        mcp = FakeMCP()
        uc = MCPUseCase(mcp_server=mcp)

        # Generate two tokens
        result1 = uc.execute(port=8080, use_tunnel=False, use_auth=True)
        result2 = uc.execute(port=8080, use_tunnel=False, use_auth=True)

        # Tokens should be different (random)
        assert result1["auth_token"] != result2["auth_token"]
        # Both should be non-empty
        assert result1["auth_token"] is not None and len(result1["auth_token"]) > 0
        assert result2["auth_token"] is not None and len(result2["auth_token"]) > 0
