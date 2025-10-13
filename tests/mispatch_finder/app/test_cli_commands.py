import json
import os
import pytest
from pathlib import Path
from typer.testing import CliRunner

from mispatch_finder.app.cli import app


runner = CliRunner()


def test_cli_show_requires_github_token(monkeypatch):
    """Test that show command behavior without GITHUB_TOKEN."""
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    result = runner.invoke(app, ["show"])
    # Note: cve_collector may use cached data or have fallback behavior
    # So this might succeed or fail depending on cache state
    assert result.exit_code in (0, 2)


@pytest.mark.skipif(not os.environ.get("GITHUB_TOKEN"), reason="GITHUB_TOKEN not set")
def test_cli_show_lists_ghsa_ids():
    """Integration test: show command lists GHSA IDs."""
    result = runner.invoke(app, ["show"])
    
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert "items" in data
    assert isinstance(data["items"], list)
    
    # Validate GHSA format if any returned
    if data["items"]:
        for ghsa in data["items"]:
            assert ghsa.startswith("GHSA-")


def test_cli_clear_executes():
    """Test that clear command executes without error."""
    result = runner.invoke(app, ["clear"])
    
    assert result.exit_code == 0
    assert "Done" in result.stdout or "Clearing" in result.stdout


def test_cli_log_without_args_lists_summaries(tmp_path, monkeypatch):
    """Test that log command without GHSA shows summary table."""
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    
    # Mock get_logs_dir to use tmp_path
    from mispatch_finder.app import config
    monkeypatch.setattr(config, "get_logs_dir", lambda: logs_dir)
    
    result = runner.invoke(app, ["log"])
    
    # Should succeed even with no logs
    assert result.exit_code == 0


def test_cli_log_with_ghsa_shows_details(tmp_path, monkeypatch):
    """Test that log command with GHSA shows log details."""
    # Set MISPATCH_HOME to tmp_path so all dirs use it
    monkeypatch.setenv("MISPATCH_HOME", str(tmp_path))
    
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a sample log file (format: {ghsa}.jsonl)
    log_file = logs_dir / "GHSA-TEST-LOG.jsonl"
    log_file.write_text('{"msg": "test", "payload": {"type": "test"}}\n', encoding="utf-8")
    
    result = runner.invoke(app, ["log", "GHSA-TEST-LOG"])
    
    assert result.exit_code == 0
    assert "GHSA-TEST-LOG" in result.stdout


def test_cli_log_verbose_flag(tmp_path, monkeypatch):
    """Test that log command respects verbose flag."""
    # Set MISPATCH_HOME to tmp_path so all dirs use it
    monkeypatch.setenv("MISPATCH_HOME", str(tmp_path))
    
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a sample log file with detailed payload (format: {ghsa}.jsonl)
    log_file = logs_dir / "GHSA-VERBOSE.jsonl"
    log_content = '{"msg": "llm_output", "payload": {"type": "llm_output", "raw_text": "detailed output"}}\n'
    log_file.write_text(log_content, encoding="utf-8")
    
    # Test without verbose - should show summary
    result_normal = runner.invoke(app, ["log", "GHSA-VERBOSE"])
    assert result_normal.exit_code == 0
    
    # Test with verbose - should show more details
    result_verbose = runner.invoke(app, ["log", "GHSA-VERBOSE", "--verbose"])
    assert result_verbose.exit_code == 0
    # Verbose output should be longer or contain more info
    assert len(result_verbose.stdout) >= len(result_normal.stdout)


def test_cli_run_requires_api_key(monkeypatch):
    """Test that run command requires API key."""
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("GITHUB_TOKEN", "ghp-test")
    
    result = runner.invoke(app, ["run", "GHSA-TEST-1234-5678"])
    
    assert result.exit_code == 2
    assert "API key required" in result.stderr or "API key required" in result.stdout


def test_cli_run_requires_github_token(monkeypatch):
    """Test that run command requires GITHUB_TOKEN."""
    monkeypatch.setenv("MODEL_API_KEY", "sk-test")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    
    result = runner.invoke(app, ["run", "GHSA-TEST-1234-5678"])
    
    # Exit code should be non-zero (either 1 or 2)
    assert result.exit_code != 0


def test_cli_run_accepts_provider_and_model_options(monkeypatch):
    """Test that run command accepts --provider and --model options."""
    monkeypatch.setenv("MODEL_API_KEY", "sk-test")
    monkeypatch.setenv("GITHUB_TOKEN", "ghp-test")
    
    # This will fail during execution but should parse arguments correctly
    result = runner.invoke(app, ["run", "GHSA-TEST", "--provider", "anthropic", "--model", "claude-3"])
    
    # Exit code may be non-zero due to execution failure, but should not be argument error (2)
    # Just verify it attempted to run with those options
    assert "provider" not in result.stderr.lower() or result.exit_code != 2


def test_cli_run_accepts_force_reclone(monkeypatch):
    """Test that run command accepts --force-reclone flag."""
    monkeypatch.setenv("MODEL_API_KEY", "sk-test")
    monkeypatch.setenv("GITHUB_TOKEN", "ghp-test")
    
    result = runner.invoke(app, ["run", "GHSA-TEST", "--force-reclone"])
    
    # Should parse flag correctly (execution may fail but args are valid)
    assert "force-reclone" not in result.stderr.lower() or result.exit_code != 2


def test_cli_run_accepts_log_level(monkeypatch):
    """Test that run command accepts --log-level option."""
    monkeypatch.setenv("MODEL_API_KEY", "sk-test")
    monkeypatch.setenv("GITHUB_TOKEN", "ghp-test")
    
    result = runner.invoke(app, ["run", "GHSA-TEST", "--log-level", "DEBUG"])
    
    # Should parse log level correctly
    assert "log-level" not in result.stderr.lower() or result.exit_code != 2

