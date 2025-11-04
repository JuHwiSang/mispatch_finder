"""Tests for MCPUseCase."""
from pathlib import Path

import pytest

from mispatch_finder.core.usecases.mcp import MCPUseCase

from tests.mispatch_finder.core.usecases.conftest import FakeMCP, FakeVulnRepo, FakeRepo, FakeTokenGen


def test_execute_streamable_http_with_tunnel_and_auth():
    """Test MCP server start in streamable-http mode with tunnel and authentication."""
    mcp = FakeMCP()
    vuln_data = FakeVulnRepo()
    repo = FakeRepo()
    token_gen = FakeTokenGen()
    uc = MCPUseCase(mcp_server=mcp, vuln_data=vuln_data, repo=repo, token_gen=token_gen)

    result = uc.execute(
        ghsa="GHSA-TEST-1234-5678",
        transport="streamable-http",
        port=8080,
        use_tunnel=True,
        use_auth=True,
    )

    # Check that vulnerability was fetched
    assert vuln_data.fetched == ["GHSA-TEST-1234-5678"]

    # Check transport mode
    assert mcp.last_transport == "streamable-http"
    assert mcp.last_use_tunnel is True

    # Check result structure
    assert result["transport"] == "streamable-http"
    assert result["local_url"] == "http://127.0.0.1:18080"
    assert result["public_url"] == "https://test.lhr.life"
    assert result["auth_token"] is not None
    assert len(result["auth_token"]) > 0  # Random token generated


def test_execute_streamable_http_without_tunnel():
    """Test MCP server start in streamable-http mode without tunnel."""
    mcp = FakeMCP()
    vuln_data = FakeVulnRepo()
    repo = FakeRepo()
    token_gen = FakeTokenGen()
    uc = MCPUseCase(mcp_server=mcp, vuln_data=vuln_data, repo=repo, token_gen=token_gen)

    result = uc.execute(
        ghsa="GHSA-TEST-1234-5678",
        transport="streamable-http",
        port=8080,
        use_tunnel=False,
        use_auth=False,
    )

    # Check transport and tunnel
    assert mcp.last_transport == "streamable-http"
    assert mcp.last_use_tunnel is False

    # Check result structure
    assert result["transport"] == "streamable-http"
    assert result["local_url"] == "http://127.0.0.1:18080"
    assert result["public_url"] is None  # No public URL when tunnel disabled
    assert result["auth_token"] is None  # No auth token when auth disabled


def test_execute_stdio_mode():
    """Test MCP server start in stdio mode."""
    mcp = FakeMCP()
    vuln_data = FakeVulnRepo()
    repo = FakeRepo()
    token_gen = FakeTokenGen()
    uc = MCPUseCase(mcp_server=mcp, vuln_data=vuln_data, repo=repo, token_gen=token_gen)

    result = uc.execute(
        ghsa="GHSA-TEST-1234-5678",
        transport="stdio",
        use_auth=False,
    )

    # Check transport mode
    assert mcp.last_transport == "stdio"

    # Check result structure (no URLs in stdio mode)
    assert result["transport"] == "stdio"
    assert result["local_url"] is None
    assert result["public_url"] is None
    assert result["auth_token"] is None


def test_execute_stdio_mode_ignores_port_and_tunnel():
    """Test that stdio mode ignores port and tunnel parameters."""
    mcp = FakeMCP()
    vuln_data = FakeVulnRepo()
    repo = FakeRepo()
    token_gen = FakeTokenGen()
    uc = MCPUseCase(mcp_server=mcp, vuln_data=vuln_data, repo=repo, token_gen=token_gen)

    result = uc.execute(
        ghsa="GHSA-TEST-1234-5678",
        transport="stdio",
        port=8080,  # Should be ignored
        use_tunnel=True,  # Should be ignored
        use_auth=False,
    )

    # Port and tunnel should be passed but have no effect in stdio mode
    assert result["transport"] == "stdio"
    assert result["local_url"] is None
    assert result["public_url"] is None


def test_auth_token_generation():
    """Test that auth tokens are generated via TokenGenerator."""
    mcp = FakeMCP()
    vuln_data = FakeVulnRepo()
    repo = FakeRepo()
    token_gen = FakeTokenGen()
    uc = MCPUseCase(mcp_server=mcp, vuln_data=vuln_data, repo=repo, token_gen=token_gen)

    # Generate two tokens
    result1 = uc.execute(ghsa="GHSA-1111-2222-3333", transport="streamable-http", port=8080, use_tunnel=False, use_auth=True)
    result2 = uc.execute(ghsa="GHSA-4444-5555-6666", transport="streamable-http", port=8080, use_tunnel=False, use_auth=True)

    # Both should have the same token from FakeTokenGen
    assert result1["auth_token"] == "fake-token-12345"
    assert result2["auth_token"] == "fake-token-12345"


def test_port_required_for_streamable_http():
    """Test that port is required for streamable-http mode."""
    mcp = FakeMCP()
    vuln_data = FakeVulnRepo()
    repo = FakeRepo()
    token_gen = FakeTokenGen()
    uc = MCPUseCase(mcp_server=mcp, vuln_data=vuln_data, repo=repo, token_gen=token_gen)

    with pytest.raises(ValueError, match="Port is required for streamable-http"):
        uc.execute(
            ghsa="GHSA-TEST",
            transport="streamable-http",
            port=None,  # Missing port
            use_auth=False,
        )


def test_invalid_transport_mode():
    """Test that invalid transport mode raises error."""
    mcp = FakeMCP()
    vuln_data = FakeVulnRepo()
    repo = FakeRepo()
    token_gen = FakeTokenGen()
    uc = MCPUseCase(mcp_server=mcp, vuln_data=vuln_data, repo=repo, token_gen=token_gen)

    with pytest.raises(ValueError, match="Invalid transport mode"):
        uc.execute(
            ghsa="GHSA-TEST",
            transport="invalid-mode",
            port=8080,
            use_auth=False,
        )


def test_workdirs_prepared_from_ghsa():
    """Test that workdirs are prepared from GHSA."""
    mcp = FakeMCP()
    vuln_data = FakeVulnRepo()
    repo = FakeRepo()
    token_gen = FakeTokenGen()
    uc = MCPUseCase(mcp_server=mcp, vuln_data=vuln_data, repo=repo, token_gen=token_gen)

    result = uc.execute(
        ghsa="GHSA-TEST-1234-5678",
        transport="streamable-http",
        port=8080,
        use_tunnel=False,
        use_auth=False,
    )

    # Verify vulnerability was fetched
    assert vuln_data.fetched == ["GHSA-TEST-1234-5678"]

    # Verify workdirs were prepared by FakeRepo
    assert mcp.last_current_workdir == Path("/fake/current")
    assert mcp.last_previous_workdir == Path("/fake/previous")
    assert result["local_url"] is not None


def test_force_reclone_parameter():
    """Test force_reclone parameter is passed to repository."""
    mcp = FakeMCP()
    vuln_data = FakeVulnRepo()
    repo = FakeRepo()
    token_gen = FakeTokenGen()
    uc = MCPUseCase(mcp_server=mcp, vuln_data=vuln_data, repo=repo, token_gen=token_gen)

    # Test with force_reclone=True
    result = uc.execute(
        ghsa="GHSA-TEST",
        transport="streamable-http",
        port=8080,
        use_tunnel=False,
        use_auth=False,
        force_reclone=True,
    )

    # Should succeed (FakeRepo doesn't track force_reclone, but parameter is accepted)
    assert result["local_url"] is not None


def test_auth_token_with_tunnel():
    """Test that auth token works with tunnel enabled."""
    mcp = FakeMCP()
    vuln_data = FakeVulnRepo()
    repo = FakeRepo()
    token_gen = FakeTokenGen()
    uc = MCPUseCase(mcp_server=mcp, vuln_data=vuln_data, repo=repo, token_gen=token_gen)

    result = uc.execute(
        ghsa="GHSA-TEST",
        transport="streamable-http",
        port=8080,
        use_tunnel=True,
        use_auth=True,
    )

    # Should have both public URL and auth token
    assert result["public_url"] is not None
    assert result["auth_token"] is not None
    assert len(result["auth_token"]) > 0
    # Auth token should be passed to MCP server
    assert mcp.last_auth_token is not None


def test_auth_token_without_tunnel():
    """Test that auth token works without tunnel (local mode)."""
    mcp = FakeMCP()
    vuln_data = FakeVulnRepo()
    repo = FakeRepo()
    token_gen = FakeTokenGen()
    uc = MCPUseCase(mcp_server=mcp, vuln_data=vuln_data, repo=repo, token_gen=token_gen)

    result = uc.execute(
        ghsa="GHSA-TEST",
        transport="streamable-http",
        port=8080,
        use_tunnel=False,
        use_auth=True,
    )

    # Should have auth token but no public URL
    assert result["public_url"] is None
    assert result["auth_token"] is not None
    assert len(result["auth_token"]) > 0


def test_multiple_invocations():
    """Test that multiple invocations work correctly."""
    mcp = FakeMCP()
    vuln_data = FakeVulnRepo()
    repo = FakeRepo()
    token_gen = FakeTokenGen()
    uc = MCPUseCase(mcp_server=mcp, vuln_data=vuln_data, repo=repo, token_gen=token_gen)

    # First invocation (streamable-http with tunnel)
    result1 = uc.execute(
        ghsa="GHSA-1111",
        transport="streamable-http",
        port=8080,
        use_tunnel=True,
        use_auth=True,
    )

    # Second invocation (streamable-http without tunnel)
    result2 = uc.execute(
        ghsa="GHSA-2222",
        transport="streamable-http",
        port=9090,
        use_tunnel=False,
        use_auth=False,
    )

    # Third invocation (stdio)
    result3 = uc.execute(
        ghsa="GHSA-3333",
        transport="stdio",
        use_auth=False,
    )

    # First should have tunnel and auth
    assert result1["transport"] == "streamable-http"
    assert result1["public_url"] is not None
    assert result1["auth_token"] is not None

    # Second should not have tunnel or auth
    assert result2["transport"] == "streamable-http"
    assert result2["public_url"] is None
    assert result2["auth_token"] is None

    # Third should be stdio
    assert result3["transport"] == "stdio"
    assert result3["local_url"] is None
    assert result3["public_url"] is None

    # Check that MCP server was called three times
    assert len(mcp.start_servers_calls) == 3
    assert mcp.start_servers_calls[0]["transport"] == "streamable-http"
    assert mcp.start_servers_calls[0]["use_tunnel"] is True
    assert mcp.start_servers_calls[1]["transport"] == "streamable-http"
    assert mcp.start_servers_calls[1]["use_tunnel"] is False
    assert mcp.start_servers_calls[2]["transport"] == "stdio"

    # Check that different GHSAs were fetched
    assert vuln_data.fetched == ["GHSA-1111", "GHSA-2222", "GHSA-3333"]


def test_auth_token_uses_token_generator():
    """Test that auth token is generated via TokenGeneratorPort."""
    mcp = FakeMCP()
    vuln_data = FakeVulnRepo()
    repo = FakeRepo()
    token_gen = FakeTokenGen()
    uc = MCPUseCase(mcp_server=mcp, vuln_data=vuln_data, repo=repo, token_gen=token_gen)

    result = uc.execute(
        ghsa="GHSA-TEST",
        transport="streamable-http",
        port=8080,
        use_tunnel=False,
        use_auth=True,
    )

    # Token should come from FakeTokenGen
    assert result["auth_token"] == "fake-token-12345"
    assert mcp.last_auth_token == "fake-token-12345"


def test_no_auth_token_uses_placeholder():
    """Test that when auth is disabled, placeholder token is used."""
    mcp = FakeMCP()
    vuln_data = FakeVulnRepo()
    repo = FakeRepo()
    token_gen = FakeTokenGen()
    uc = MCPUseCase(mcp_server=mcp, vuln_data=vuln_data, repo=repo, token_gen=token_gen)

    result = uc.execute(
        ghsa="GHSA-TEST",
        transport="streamable-http",
        port=8080,
        use_tunnel=False,
        use_auth=False,
    )

    # No auth token returned to user
    assert result["auth_token"] is None

    # But MCP server gets placeholder token
    assert mcp.last_auth_token == "no-auth-required"
