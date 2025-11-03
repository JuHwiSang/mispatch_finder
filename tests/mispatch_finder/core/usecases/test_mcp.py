"""Tests for MCPUseCase."""
from pathlib import Path

from mispatch_finder.core.usecases.mcp import MCPUseCase

from tests.mispatch_finder.core.usecases.conftest import FakeMCP, FakeVulnRepo, FakeRepo, FakeTokenGen


def test_execute_with_tunnel_and_auth():
    """Test MCP server start with tunnel and authentication."""
    mcp = FakeMCP()
    vuln_data = FakeVulnRepo()
    repo = FakeRepo()
    token_gen = FakeTokenGen()
    uc = MCPUseCase(mcp_server=mcp, vuln_data=vuln_data, repo=repo, token_gen=token_gen)

    result = uc.execute(
        ghsa="GHSA-TEST-1234-5678",
        port=8080,
        use_tunnel=True,
        use_auth=True,
    )

    # Check that vulnerability was fetched
    assert vuln_data.fetched == ["GHSA-TEST-1234-5678"]

    # Check that tunnel was enabled
    assert mcp.last_use_tunnel is True

    # Check result structure
    assert result["local_url"] == "http://127.0.0.1:18080"
    assert result["public_url"] == "https://test.lhr.life"
    assert result["auth_token"] is not None
    assert len(result["auth_token"]) > 0  # Random token generated


def test_execute_without_tunnel():
    """Test MCP server start without tunnel (local mode)."""
    mcp = FakeMCP()
    vuln_data = FakeVulnRepo()
    repo = FakeRepo()
    token_gen = FakeTokenGen()
    uc = MCPUseCase(mcp_server=mcp, vuln_data=vuln_data, repo=repo, token_gen=token_gen)

    result = uc.execute(
        ghsa="GHSA-TEST-1234-5678",
        port=8080,
        use_tunnel=False,
        use_auth=False,
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
    vuln_data = FakeVulnRepo()
    repo = FakeRepo()
    token_gen = FakeTokenGen()
    uc = MCPUseCase(mcp_server=mcp, vuln_data=vuln_data, repo=repo, token_gen=token_gen)

    result = uc.execute(
        ghsa="GHSA-TEST-1234-5678",
        port=8080,
        use_tunnel=True,
        use_auth=False,
    )

    # Check result structure
    assert result["local_url"] == "http://127.0.0.1:18080"
    assert result["public_url"] == "https://test.lhr.life"
    assert result["auth_token"] is None  # No auth token when auth disabled


def test_auth_token_generation():
    """Test that auth tokens are generated via TokenGenerator."""
    mcp = FakeMCP()
    vuln_data = FakeVulnRepo()
    repo = FakeRepo()
    token_gen = FakeTokenGen()
    uc = MCPUseCase(mcp_server=mcp, vuln_data=vuln_data, repo=repo, token_gen=token_gen)

    # Generate two tokens
    result1 = uc.execute(ghsa="GHSA-1111-2222-3333", port=8080, use_tunnel=False, use_auth=True)
    result2 = uc.execute(ghsa="GHSA-4444-5555-6666", port=8080, use_tunnel=False, use_auth=True)

    # Both should have the same token from FakeTokenGen
    assert result1["auth_token"] == "fake-token-12345"
    assert result2["auth_token"] == "fake-token-12345"


def test_port_parameter_passed_correctly():
    """Test that port parameter is accepted (though not used in fake)."""
    mcp = FakeMCP()
    vuln_data = FakeVulnRepo()
    repo = FakeRepo()
    token_gen = FakeTokenGen()
    uc = MCPUseCase(mcp_server=mcp, vuln_data=vuln_data, repo=repo, token_gen=token_gen)

    # Different port numbers should not cause errors
    result1 = uc.execute(ghsa="GHSA-TEST", port=8080, use_tunnel=False, use_auth=False)
    result2 = uc.execute(ghsa="GHSA-TEST", port=9090, use_tunnel=False, use_auth=False)
    result3 = uc.execute(ghsa="GHSA-TEST", port=18080, use_tunnel=False, use_auth=False)

    # All should succeed
    assert result1["local_url"] is not None
    assert result2["local_url"] is not None
    assert result3["local_url"] is not None


def test_workdirs_prepared_from_ghsa():
    """Test that workdirs are prepared from GHSA."""
    mcp = FakeMCP()
    vuln_data = FakeVulnRepo()
    repo = FakeRepo()
    token_gen = FakeTokenGen()
    uc = MCPUseCase(mcp_server=mcp, vuln_data=vuln_data, repo=repo, token_gen=token_gen)

    result = uc.execute(
        ghsa="GHSA-TEST-1234-5678",
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

    # First invocation
    result1 = uc.execute(
        ghsa="GHSA-1111",
        port=8080,
        use_tunnel=True,
        use_auth=True,
    )

    # Second invocation with different parameters
    result2 = uc.execute(
        ghsa="GHSA-2222",
        port=9090,
        use_tunnel=False,
        use_auth=False,
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

    # Check that different GHSAs were fetched
    assert vuln_data.fetched == ["GHSA-1111", "GHSA-2222"]


def test_auth_token_uses_token_generator():
    """Test that auth token is generated via TokenGeneratorPort."""
    mcp = FakeMCP()
    vuln_data = FakeVulnRepo()
    repo = FakeRepo()
    token_gen = FakeTokenGen()
    uc = MCPUseCase(mcp_server=mcp, vuln_data=vuln_data, repo=repo, token_gen=token_gen)

    result = uc.execute(ghsa="GHSA-TEST", port=8080, use_tunnel=False, use_auth=True)

    # Should use FakeTokenGen's token
    assert result["auth_token"] == "fake-token-12345"
