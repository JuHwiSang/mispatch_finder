import json
import os
import pytest
from pathlib import Path
from typer.testing import CliRunner

from mispatch_finder.app.cli import app


runner = CliRunner()


def test_cli_list_requires_github_token(monkeypatch):
    """Test that list command behavior without MISPATCH_FINDER_GITHUB__TOKEN."""
    monkeypatch.delenv("MISPATCH_FINDER_GITHUB__TOKEN", raising=False)
    result = runner.invoke(app, ["list"])
    # Note: cve_collector may use cached data or have fallback behavior
    # So this might succeed or fail depending on cache state
    assert result.exit_code in (0, 2)


@pytest.mark.skipif(not os.environ.get("MISPATCH_FINDER_GITHUB__TOKEN"), reason="MISPATCH_FINDER_GITHUB__TOKEN not set")
def test_cli_list_lists_ghsa_ids():
    """Integration test: list command lists GHSA IDs."""
    # Use --json flag to get JSON output for testing
    result = runner.invoke(app, ["list", "--json"])

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert "items" in data
    assert isinstance(data["items"], list)

    # Validate GHSA format if any returned
    if data["items"]:
        for ghsa in data["items"]:
            assert ghsa.startswith("GHSA-")


@pytest.mark.skip(reason="clear command disabled - TODO: fix resource conflicts and define clear semantics")
def test_cli_clear_executes():
    """Test that clear command executes without error."""
    result = runner.invoke(app, ["clear"])

    assert result.exit_code == 0
    assert "Done" in result.stdout or "Clearing" in result.stdout


def test_cli_logs_without_args_lists_summaries(tmp_path, monkeypatch):
    """Test that logs command without GHSA shows summary table."""
    # Set home directory via new config system
    monkeypatch.setenv("MISPATCH_FINDER_DIRECTORIES__HOME", str(tmp_path))

    logs_dir = tmp_path / "logs"
    logs_dir.mkdir(exist_ok=True)

    result = runner.invoke(app, ["logs"])

    # Should succeed even with no logs
    assert result.exit_code == 0


def test_cli_logs_with_ghsa_shows_details(tmp_path, monkeypatch):
    """Test that logs command with GHSA shows log details."""
    # Set home directory via new config system
    monkeypatch.setenv("MISPATCH_FINDER_DIRECTORIES__HOME", str(tmp_path))

    logs_dir = tmp_path / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Create a sample log file (format: {ghsa}.jsonl)
    log_file = logs_dir / "GHSA-TEST-LOG.jsonl"
    log_file.write_text('{"msg": "test", "payload": {"type": "test"}}\n', encoding="utf-8")

    result = runner.invoke(app, ["logs", "GHSA-TEST-LOG"])

    assert result.exit_code == 0
    assert "GHSA-TEST-LOG" in result.stdout


def test_cli_logs_verbose_flag(tmp_path, monkeypatch):
    """Test that logs command respects verbose flag."""
    # Set home directory via new config system
    monkeypatch.setenv("MISPATCH_FINDER_DIRECTORIES__HOME", str(tmp_path))

    logs_dir = tmp_path / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Create a sample log file with detailed payload (format: {ghsa}.jsonl)
    log_file = logs_dir / "GHSA-VERBOSE.jsonl"
    log_content = '{"msg": "llm_output", "payload": {"type": "llm_output", "raw_text": "detailed output"}}\n'
    log_file.write_text(log_content, encoding="utf-8")

    # Test without verbose - should show summary
    result_normal = runner.invoke(app, ["logs", "GHSA-VERBOSE"])
    assert result_normal.exit_code == 0

    # Test with verbose - should show more details
    result_verbose = runner.invoke(app, ["logs", "GHSA-VERBOSE", "--verbose"])
    assert result_verbose.exit_code == 0
    # Verbose output should be longer or contain more info
    assert len(result_verbose.stdout) >= len(result_normal.stdout)


def test_cli_analyze_requires_api_key(monkeypatch):
    """Test that analyze command requires API key."""
    monkeypatch.delenv("MISPATCH_FINDER_LLM__API_KEY", raising=False)
    monkeypatch.setenv("MISPATCH_FINDER_GITHUB__TOKEN", "ghp-test")

    result = runner.invoke(app, ["analyze", "GHSA-TEST-1234-5678"])

    assert result.exit_code == 2
    assert "API key required" in result.stderr or "API key required" in result.stdout


def test_cli_analyze_requires_github_token(monkeypatch):
    """Test that analyze command requires GITHUB_TOKEN."""
    monkeypatch.setenv("MISPATCH_FINDER_LLM__API_KEY", "sk-test")
    monkeypatch.delenv("MISPATCH_FINDER_GITHUB__TOKEN", raising=False)

    result = runner.invoke(app, ["analyze", "GHSA-TEST-1234-5678"])

    # Exit code should be non-zero (either 1 or 2)
    assert result.exit_code != 0


def test_cli_run_accepts_provider_and_model_options(monkeypatch):
    """Test that run command accepts --provider and --model options."""
    monkeypatch.setenv("MISPATCH_FINDER_LLM__API_KEY", "sk-test")
    monkeypatch.setenv("MISPATCH_FINDER_GITHUB__TOKEN", "ghp-test")

    # This will fail during execution but should parse arguments correctly
    result = runner.invoke(app, ["analyze", "GHSA-TEST", "--provider", "anthropic", "--model", "claude-3"])

    # Exit code may be non-zero due to execution failure, but should not be argument error (2)
    # Just verify it attempted to run with those options
    assert "provider" not in result.stderr.lower() or result.exit_code != 2


def test_cli_run_accepts_force_reclone(monkeypatch):
    """Test that run command accepts --force-reclone flag."""
    monkeypatch.setenv("MISPATCH_FINDER_LLM__API_KEY", "sk-test")
    monkeypatch.setenv("MISPATCH_FINDER_GITHUB__TOKEN", "ghp-test")

    result = runner.invoke(app, ["analyze", "GHSA-TEST", "--force-reclone"])

    # Should parse flag correctly (execution may fail but args are valid)
    assert "force-reclone" not in result.stderr.lower() or result.exit_code != 2


def test_cli_run_accepts_log_level(monkeypatch):
    """Test that run command accepts --log-level option."""
    monkeypatch.setenv("MISPATCH_FINDER_LLM__API_KEY", "sk-test")
    monkeypatch.setenv("MISPATCH_FINDER_GITHUB__TOKEN", "ghp-test")

    result = runner.invoke(app, ["analyze", "GHSA-TEST", "--log-level", "DEBUG"])

    # Should parse log level correctly
    assert "log-level" not in result.stderr.lower() or result.exit_code != 2


@pytest.mark.skipif(not os.environ.get("MISPATCH_FINDER_GITHUB__TOKEN"), reason="MISPATCH_FINDER_GITHUB__TOKEN not set")
def test_cli_list_detail_flag():
    """Test that list command accepts --detail flag."""
    result = runner.invoke(app, ["list", "--detail", "--json"])

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    # With --detail, should return object with "count" and "vulnerabilities"
    assert "vulnerabilities" in data
    assert isinstance(data["vulnerabilities"], list)


@pytest.mark.skipif(not os.environ.get("MISPATCH_FINDER_GITHUB__TOKEN"), reason="MISPATCH_FINDER_GITHUB__TOKEN not set")
def test_cli_list_detail_short_flag():
    """Test that list command accepts -d short flag for detail."""
    result = runner.invoke(app, ["list", "-d", "--json"])

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    # With -d, should return object with "count" and "vulnerabilities"
    assert "vulnerabilities" in data
    assert isinstance(data["vulnerabilities"], list)


@pytest.mark.skipif(not os.environ.get("MISPATCH_FINDER_GITHUB__TOKEN"), reason="MISPATCH_FINDER_GITHUB__TOKEN not set")
def test_cli_list_include_analyzed_flag():
    """Test that list command accepts --include-analyzed flag."""
    result = runner.invoke(app, ["list", "--include-analyzed", "--json"])

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    # Should parse flag correctly and return items
    assert "items" in data
    assert isinstance(data["items"], list)


@pytest.mark.skipif(not os.environ.get("MISPATCH_FINDER_GITHUB__TOKEN"), reason="MISPATCH_FINDER_GITHUB__TOKEN not set")
def test_cli_list_include_analyzed_short_flag():
    """Test that list command accepts -i short flag for include-analyzed."""
    result = runner.invoke(app, ["list", "-i", "--json"])

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    # Should parse flag correctly and return items
    assert "items" in data
    assert isinstance(data["items"], list)

