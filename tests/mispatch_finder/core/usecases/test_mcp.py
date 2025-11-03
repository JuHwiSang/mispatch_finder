"""Tests for MCPUseCase."""
from pathlib import Path

from mispatch_finder.core.usecases.mcp import MCPUseCase

from tests.mispatch_finder.core.usecases.conftest import FakeMCP


def test_execute_with_tunnel_and_auth():
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


def test_execute_without_tunnel():
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


def test_execute_without_auth():
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


def test_auth_token_generation():
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


def test_port_parameter_passed_correctly():
    """Test that port parameter is accepted (though not used in fake)."""
    mcp = FakeMCP()
    uc = MCPUseCase(mcp_server=mcp)

    # Different port numbers should not cause errors
    result1 = uc.execute(port=8080, use_tunnel=False, use_auth=False)
    result2 = uc.execute(port=9090, use_tunnel=False, use_auth=False)
    result3 = uc.execute(port=18080, use_tunnel=False, use_auth=False)

    # All should succeed
    assert result1["local_url"] is not None
    assert result2["local_url"] is not None
    assert result3["local_url"] is not None


def test_current_workdir_only():
    """Test MCP server with only current workdir."""
    mcp = FakeMCP()
    uc = MCPUseCase(mcp_server=mcp)

    result = uc.execute(
        port=8080,
        use_tunnel=False,
        use_auth=False,
        current_workdir=Path("/fake/current"),
        previous_workdir=None,
    )

    # Verify workdir was passed to MCP server
    assert mcp.last_current_workdir == Path("/fake/current")
    assert mcp.last_previous_workdir is None
    assert result["local_url"] is not None


def test_previous_workdir_only():
    """Test MCP server with only previous workdir."""
    mcp = FakeMCP()
    uc = MCPUseCase(mcp_server=mcp)

    result = uc.execute(
        port=8080,
        use_tunnel=False,
        use_auth=False,
        current_workdir=None,
        previous_workdir=Path("/fake/previous"),
    )

    # Verify workdir was passed to MCP server
    assert mcp.last_current_workdir is None
    assert mcp.last_previous_workdir == Path("/fake/previous")
    assert result["local_url"] is not None


def test_both_workdirs():
    """Test MCP server with both current and previous workdirs."""
    mcp = FakeMCP()
    uc = MCPUseCase(mcp_server=mcp)

    result = uc.execute(
        port=8080,
        use_tunnel=False,
        use_auth=False,
        current_workdir=Path("/fake/current"),
        previous_workdir=Path("/fake/previous"),
    )

    # Verify both workdirs were passed
    assert mcp.last_current_workdir == Path("/fake/current")
    assert mcp.last_previous_workdir == Path("/fake/previous")
    assert result["local_url"] is not None


def test_no_workdirs():
    """Test MCP server with no workdirs (standalone mode)."""
    mcp = FakeMCP()
    uc = MCPUseCase(mcp_server=mcp)

    result = uc.execute(
        port=8080,
        use_tunnel=False,
        use_auth=False,
        current_workdir=None,
        previous_workdir=None,
    )

    # Verify no workdirs were passed
    assert mcp.last_current_workdir is None
    assert mcp.last_previous_workdir is None
    assert result["local_url"] is not None


def test_auth_token_with_tunnel():
    """Test that auth token works with tunnel enabled."""
    mcp = FakeMCP()
    uc = MCPUseCase(mcp_server=mcp)

    result = uc.execute(
        port=8080,
        use_tunnel=True,
        use_auth=True,
        current_workdir=None,
        previous_workdir=None,
    )

    # Should have both public URL and auth token
    assert result["public_url"] is not None
    assert result["auth_token"] is not None
    assert len(result["auth_token"]) > 0
    # Auth token should be passed to MCP server
    assert mcp.last_auth_token is not None


def test_auth_token_without_tunnel():
    """Test that auth token works without tunnel (internal mode)."""
    mcp = FakeMCP()
    uc = MCPUseCase(mcp_server=mcp)

    result = uc.execute(
        port=8080,
        use_tunnel=False,
        use_auth=True,
        current_workdir=None,
        previous_workdir=None,
    )

    # Should have auth token but no public URL
    assert result["public_url"] is None
    assert result["auth_token"] is not None
    assert len(result["auth_token"]) > 0


def test_multiple_invocations():
    """Test that multiple invocations work correctly."""
    mcp = FakeMCP()
    uc = MCPUseCase(mcp_server=mcp)

    # First invocation
    result1 = uc.execute(
        port=8080,
        use_tunnel=True,
        use_auth=True,
        current_workdir=Path("/fake/current1"),
        previous_workdir=None,
    )

    # Second invocation with different parameters
    result2 = uc.execute(
        port=9090,
        use_tunnel=False,
        use_auth=False,
        current_workdir=Path("/fake/current2"),
        previous_workdir=Path("/fake/previous2"),
    )

    # Both should succeed independently
    assert result1["public_url"] is not None  # First has tunnel
    assert result1["auth_token"] is not None  # First has auth

    assert result2["public_url"] is None  # Second has no tunnel
    assert result2["auth_token"] is None  # Second has no auth

    # Check that MCP server was called twice
    assert len(mcp.start_servers_calls) == 2
    assert mcp.start_servers_calls[0]["use_tunnel"] is True
    assert mcp.start_servers_calls[1]["use_tunnel"] is False


def test_auth_token_length():
    """Test that generated auth tokens have reasonable length."""
    mcp = FakeMCP()
    uc = MCPUseCase(mcp_server=mcp)

    result = uc.execute(port=8080, use_tunnel=False, use_auth=True)

    # secrets.token_urlsafe(32) generates ~43 characters (32 bytes base64)
    token = result["auth_token"]
    assert token is not None
    assert len(token) >= 40  # Should be at least 40 characters
    assert len(token) <= 50  # Should not be excessively long
