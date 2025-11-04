"""Tests for 'mcp' CLI command.

Note: The mcp command starts a long-running server with an infinite loop,
making it difficult to test with runner.invoke(). These tests focus on
validation and argument parsing. Core functionality is tested in test_usecases.py.
"""
from typer.testing import CliRunner

from mispatch_finder.app.cli import app


runner = CliRunner()


def test_mcp_missing_ghsa_argument():
    """Test mcp command requires GHSA argument."""
    result = runner.invoke(app, ["mcp"])
    assert result.exit_code != 0
    # Should fail due to missing required argument


def test_mcp_invalid_mode():
    """Test mcp command with invalid mode validation."""
    result = runner.invoke(app, ["mcp", "GHSA-TEST-1234-5678", "--mode", "invalid"])
    assert result.exit_code == 1
    # Typer's CliRunner captures err=True output in result.output
    assert "Invalid mode" in result.output
    assert "Must be 'stdio' or 'streamable-http'" in result.output


def test_mcp_invalid_mode_old_names():
    """Test that old mode names (local/tunnel/internal/external) are rejected."""
    result1 = runner.invoke(app, ["mcp", "GHSA-TEST", "--mode", "local"])
    assert result1.exit_code == 1
    assert "Invalid mode" in result1.output

    result2 = runner.invoke(app, ["mcp", "GHSA-TEST", "--mode", "tunnel"])
    assert result2.exit_code == 1
    assert "Invalid mode" in result2.output

    result3 = runner.invoke(app, ["mcp", "GHSA-TEST", "--mode", "internal"])
    assert result3.exit_code == 1
    assert "Invalid mode" in result3.output

    result4 = runner.invoke(app, ["mcp", "GHSA-TEST", "--mode", "external"])
    assert result4.exit_code == 1
    assert "Invalid mode" in result4.output


def test_mcp_streamable_http_requires_port():
    """Test that streamable-http mode requires --port."""
    result = runner.invoke(app, ["mcp", "GHSA-TEST", "--mode", "streamable-http"])
    assert result.exit_code == 1
    assert "--port is required for streamable-http mode" in result.output


# Note: Further CLI tests are omitted because:
# 1. The mcp command runs an infinite loop (while True: time.sleep(1))
# 2. runner.invoke() cannot handle long-running commands without hanging
# 3. Core functionality is thoroughly tested at UseCase level (test_usecases.py)
# 4. Mocking the infinite loop is complex and doesn't add significant value
#
# If CLI-level integration tests are needed, consider:
# - Using threading/multiprocessing with timeout
# - Testing in a separate process with termination signal
# - Adding a hidden --test-mode flag that skips the infinite loop
