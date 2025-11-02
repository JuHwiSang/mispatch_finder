"""Tests for 'analyze' CLI command."""
import json
import shutil
import pytest
from pathlib import Path
from git import Repo
from typer.testing import CliRunner
from dependency_injector import providers

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
from mispatch_finder.infra.mcp.tunnel import Tunnel
from tests.mispatch_finder.app.conftest import (
    MockVulnerabilityRepository,
    MockLLM,
    MockMCPServer,
    DummyTunnel,
    MockRepository,
)


runner = CliRunner()


def _init_repo_with_two_commits(tmp_path: Path) -> tuple[Path, str, str]:
    """Create a git repo with two commits for E2E testing."""
    if tmp_path.exists():
        shutil.rmtree(tmp_path)
    repo_dir = tmp_path / "repo"
    repo = Repo.init(repo_dir)
    (repo_dir / "a.txt").write_text("one", encoding="utf-8")
    repo.index.add(["a.txt"])
    c1 = repo.index.commit(
        "first",
        author_date="2024-02-01T12:34:56+0900",
        commit_date="2024-02-01T12:34:56+0900",
    ).hexsha
    (repo_dir / "a.txt").write_text("one\ntwo", encoding="utf-8")
    repo.index.add(["a.txt"])
    c2 = repo.index.commit(
        "second",
        author_date="2024-02-01T13:34:56+0900",
        commit_date="2024-02-01T13:34:56+0900",
    ).hexsha
    repo.close()
    return repo_dir, c1, c2


def test_analyze_requires_api_key(monkeypatch):
    """Test that analyze command requires API key."""
    monkeypatch.delenv("MISPATCH_FINDER_LLM__API_KEY", raising=False)
    monkeypatch.setenv("MISPATCH_FINDER_GITHUB__TOKEN", "ghp-test")

    result = runner.invoke(app, ["analyze", "GHSA-TEST-1234-5678"])

    assert result.exit_code == 2
    assert "API key required" in result.stderr or "API key required" in result.stdout


def test_analyze_requires_github_token(monkeypatch):
    """Test that analyze command requires GITHUB_TOKEN."""
    monkeypatch.setenv("MISPATCH_FINDER_LLM__API_KEY", "sk-test")
    monkeypatch.delenv("MISPATCH_FINDER_GITHUB__TOKEN", raising=False)

    result = runner.invoke(app, ["analyze", "GHSA-TEST-1234-5678"])

    # Exit code should be non-zero (either 1 or 2)
    assert result.exit_code != 0


def test_analyze_accepts_provider_and_model_options(monkeypatch):
    """Test that analyze command accepts --provider and --model options."""
    monkeypatch.setenv("MISPATCH_FINDER_LLM__API_KEY", "sk-test")
    monkeypatch.setenv("MISPATCH_FINDER_GITHUB__TOKEN", "ghp-test")

    # This will fail during execution but should parse arguments correctly
    result = runner.invoke(app, ["analyze", "GHSA-TEST", "--provider", "anthropic", "--model", "claude-3"])

    # Exit code may be non-zero due to execution failure, but should not be argument error (2)
    # Just verify it attempted to run with those options
    assert "provider" not in result.stderr.lower() or result.exit_code != 2


def test_analyze_accepts_force_reclone(monkeypatch):
    """Test that analyze command accepts --force-reclone flag."""
    monkeypatch.setenv("MISPATCH_FINDER_LLM__API_KEY", "sk-test")
    monkeypatch.setenv("MISPATCH_FINDER_GITHUB__TOKEN", "ghp-test")

    result = runner.invoke(app, ["analyze", "GHSA-TEST", "--force-reclone"])

    # Should parse flag correctly (execution may fail but args are valid)
    assert "force-reclone" not in result.stderr.lower() or result.exit_code != 2


def test_analyze_accepts_log_level(monkeypatch):
    """Test that analyze command accepts --log-level option."""
    monkeypatch.setenv("MISPATCH_FINDER_LLM__API_KEY", "sk-test")
    monkeypatch.setenv("MISPATCH_FINDER_GITHUB__TOKEN", "ghp-test")

    result = runner.invoke(app, ["analyze", "GHSA-TEST", "--log-level", "DEBUG"])

    # Should parse log level correctly
    assert "log-level" not in result.stderr.lower() or result.exit_code != 2


def test_analyze_accepts_json_flag(monkeypatch):
    """Test that analyze command accepts --json flag."""
    monkeypatch.setenv("MISPATCH_FINDER_LLM__API_KEY", "sk-test")
    monkeypatch.setenv("MISPATCH_FINDER_GITHUB__TOKEN", "ghp-test")

    result = runner.invoke(app, ["analyze", "GHSA-TEST", "--json"])

    # Should parse flag correctly (execution may fail but args are valid)
    assert "json" not in result.stderr.lower() or result.exit_code != 2


def test_analyze_nonexistent_ghsa_removes_log_file(tmp_path, monkeypatch):
    """Test that analyze command removes log file when GHSA doesn't exist."""
    from mispatch_finder.core.domain.exceptions import GHSANotFoundError

    # Create a mock vulnerability adapter that raises GHSANotFoundError
    class FailingVulnerabilityAdapter:
        def __init__(self, **kwargs):
            pass

        def fetch_metadata(self, ghsa: str):
            # Simulate GHSA not found (404 from API)
            raise GHSANotFoundError(ghsa)

    # Patch VulnerabilityDataAdapter to return failing adapter
    from mispatch_finder.infra import vulnerability_data as vuln_module
    original_adapter = vuln_module.VulnerabilityDataAdapter
    monkeypatch.setattr(vuln_module, "VulnerabilityDataAdapter", FailingVulnerabilityAdapter)

    # Setup environment
    monkeypatch.setenv("MISPATCH_FINDER_LLM__API_KEY", "sk-test")
    monkeypatch.setenv("MISPATCH_FINDER_GITHUB__TOKEN", "ghp-test")
    monkeypatch.setenv("MISPATCH_FINDER_DIRECTORIES__HOME", str(tmp_path))

    # Create logs directory and pre-create log file
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / "GHSA-NONEXIST-1234.jsonl"
    log_file.write_text('{"type": "test"}\n', encoding="utf-8")
    assert log_file.exists()

    # Execute with nonexistent GHSA
    result = runner.invoke(app, ["analyze", "GHSA-NONEXIST-1234"])

    # Should exit with error code 1
    assert result.exit_code == 1
    # Error message should mention GHSA not found
    assert "GHSA not found" in result.stderr or "GHSA not found" in result.stdout

    # Log file should be removed
    assert not log_file.exists()

    # Restore original adapter
    monkeypatch.setattr(vuln_module, "VulnerabilityDataAdapter", original_adapter)


def test_analyze_end_to_end(tmp_path, monkeypatch):
    """E2E test: analyze command with mocked dependencies."""
    base, c1, c2 = _init_repo_with_two_commits(tmp_path)

    # Mock Tunnel to avoid real network calls
    def fake_start_tunnel(host, port):
        return f"http://{host}:{port}", DummyTunnel()

    monkeypatch.setattr(Tunnel, "start_tunnel", fake_start_tunnel)

    # Create test config
    test_config = AppConfig(
        directories=DirectoryConfig(home=tmp_path),
        llm=LLMConfig(
            api_key="test-key",
            provider_name="openai",
            model_name="gpt-4",
        ),
        github=GitHubConfig(token="test-token"),
        vulnerability=VulnerabilityConfig(ecosystem="npm"),
        analysis=AnalysisConfig(diff_max_chars=200_000),
    )

    # Set runtime GHSA (required for logger)
    test_config.runtime.ghsa = "GHSA-TEST-E2E"

    # Create mocked container
    def create_mocked_container():
        container = Container()
        container.config.from_pydantic(test_config)

        # Override with mocks
        container.vuln_data.override(
            providers.Singleton(
                MockVulnerabilityRepository,
                repo_url=base.as_posix(),
                commit=c2,
            )
        )
        container.repo.override(
            providers.Factory(
                MockRepository,
                repo_dir=base,
                commit=c2,
            )
        )
        container.llm.override(providers.Factory(MockLLM))
        container.mcp_server.override(providers.Factory(MockMCPServer))

        return container

    # Execute (mimics CLI implementation)
    container = create_mocked_container()
    uc = container.analyze_uc()
    result = uc.execute(ghsa="GHSA-TEST-E2E", force_reclone=True)

    # Check AnalysisResult fields
    assert result.ghsa == "GHSA-TEST-E2E"
    assert result.verdict == "good"  # current_risk
    assert result.severity == "good"  # patch_risk
    assert result.rationale == "Mock LLM response"  # reason
    assert result.raw_text is not None

    # Also verify raw_text contains expected JSON
    data = json.loads(result.raw_text) if isinstance(result.raw_text, str) else result.raw_text
    assert isinstance(data, dict)
    assert data["patch_risk"] == "good"
    assert data["current_risk"] == "good"
    assert data["reason"] == "Mock LLM response"
