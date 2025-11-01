"""Tests for 'logs' CLI command."""
import pytest
from pathlib import Path
from typer.testing import CliRunner

from mispatch_finder.app.cli import app
from mispatch_finder.app.config import (
    AppConfig,
    DirectoryConfig,
    LLMConfig,
    GitHubConfig,
    VulnerabilityConfig,
    AnalysisConfig,
)
from mispatch_finder.app.container import Container


runner = CliRunner()


def test_logs_without_args_lists_summaries(tmp_path, monkeypatch):
    """Test that logs command without GHSA shows summary table."""
    # Set home directory via new config system
    monkeypatch.setenv("MISPATCH_FINDER_DIRECTORIES__HOME", str(tmp_path))

    logs_dir = tmp_path / "logs"
    logs_dir.mkdir(exist_ok=True)

    result = runner.invoke(app, ["logs"])

    # Should succeed even with no logs
    assert result.exit_code == 0


def test_logs_with_ghsa_shows_details(tmp_path, monkeypatch):
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


def test_logs_verbose_flag(tmp_path, monkeypatch):
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


def test_logs_with_ghsa_e2e(tmp_path):
    """E2E test: logs command returns log details for specific GHSA."""
    test_config = AppConfig(
        directories=DirectoryConfig(home=tmp_path),
        llm=LLMConfig(api_key="test-key", provider_name="openai", model_name="gpt-4"),
        github=GitHubConfig(token="test-token"),
        vulnerability=VulnerabilityConfig(ecosystem="npm"),
        analysis=AnalysisConfig(diff_max_chars=200_000),
    )

    logs_dir = tmp_path / "logs"
    logs_dir.mkdir(exist_ok=True)

    log_file = logs_dir / "GHSA-TEST.jsonl"
    log_file.write_text(
        '{"message":"run_started","ghsa":"GHSA-TEST"}\n'
        '{"message":"final_result","payload":{"type":"final_result","result":{"ghsa":"GHSA-TEST"}}}\n',
        encoding="utf-8"
    )

    # Create container
    container = Container()
    container.config.from_pydantic(test_config)

    # Execute (mimics CLI implementation)
    uc = container.logs_uc()
    result = uc.execute("GHSA-TEST", verbose=False)

    assert isinstance(result, list)
    assert len(result) > 0


def test_logs_without_ghsa_e2e(tmp_path):
    """E2E test: logs command returns summary when no GHSA provided."""
    test_config = AppConfig(
        directories=DirectoryConfig(home=tmp_path),
        llm=LLMConfig(api_key="test-key", provider_name="openai", model_name="gpt-4"),
        github=GitHubConfig(token="test-token"),
        vulnerability=VulnerabilityConfig(ecosystem="npm"),
        analysis=AnalysisConfig(diff_max_chars=200_000),
    )

    logs_dir = tmp_path / "logs"
    logs_dir.mkdir(exist_ok=True)

    # Create container
    container = Container()
    container.config.from_pydantic(test_config)

    # Execute (mimics CLI implementation)
    uc = container.logs_uc()
    result = uc.execute(None, verbose=False)

    assert isinstance(result, list)
