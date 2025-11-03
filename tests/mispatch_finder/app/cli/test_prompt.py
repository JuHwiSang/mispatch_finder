"""Tests for 'prompt' CLI command."""
import pytest
from pathlib import Path
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
from tests.mispatch_finder.app.conftest import (
    create_test_repo,
    MockVulnerabilityRepository,
    MockRepository,
)


runner = CliRunner()


@pytest.fixture
def mock_container_for_prompt(tmp_path, test_config, monkeypatch):
    """Fixture to override container with mocks for prompt tests."""
    repo_dir, c1, c2 = create_test_repo(tmp_path)

    def create_mock_container():
        c = Container()
        c.config.from_pydantic(test_config)
        c.vuln_data.override(
            providers.Singleton(
                MockVulnerabilityRepository,
                repo_url=str(repo_dir),
                commit=c2,
            )
        )
        c.repo.override(
            providers.Factory(
                MockRepository,
                repo_dir=repo_dir,
                commit=c2,
            )
        )
        return c

    monkeypatch.setattr("mispatch_finder.app.cli.Container", create_mock_container)
    return repo_dir, c1, c2


def test_prompt_command_basic(mock_container_for_prompt, test_config):
    """Test that prompt command outputs the raw prompt."""
    result = runner.invoke(app, ["prompt", "GHSA-TEST-1234-5678"])

    assert result.exit_code == 0
    assert "You are a security reviewer" in result.stdout
    assert "GHSA-TEST-1234-5678" in result.stdout
    assert "test/repo" in result.stdout  # Repository name from mock


def test_prompt_command_includes_diff(mock_container_for_prompt, test_config):
    """Test that prompt command includes the diff section."""
    result = runner.invoke(app, ["prompt", "GHSA-9999-8888-7777"])

    assert result.exit_code == 0
    assert "--- DIFF (unified) ---" in result.stdout
    assert "print('v2')" in result.stdout  # Diff content from mock


def test_prompt_command_with_force_reclone(mock_container_for_prompt, test_config):
    """Test that prompt command accepts --force-reclone flag."""
    result = runner.invoke(app, ["prompt", "GHSA-TEST-1234-5678", "--force-reclone"])

    assert result.exit_code == 0
    assert "You are a security reviewer" in result.stdout


def test_prompt_command_e2e(tmp_path):
    """E2E test: prompt command generates complete prompt."""
    test_config = AppConfig(
        directories=DirectoryConfig(home=tmp_path),
        llm=LLMConfig(api_key="test-key", provider_name="openai", model_name="gpt-4"),
        github=GitHubConfig(token="test-token"),
        vulnerability=VulnerabilityConfig(ecosystem="npm"),
        analysis=AnalysisConfig(diff_max_chars=200_000),
    )

    repo_dir, c1, c2 = create_test_repo(tmp_path)

    # Create container
    container = Container()
    container.config.from_pydantic(test_config)

    # Override with mocks
    container.vuln_data.override(
        providers.Singleton(
            MockVulnerabilityRepository,
            repo_url=str(repo_dir),
            commit=c2,
        )
    )
    container.repo.override(
        providers.Factory(
            MockRepository,
            repo_dir=repo_dir,
            commit=c2,
        )
    )

    # Execute (mimics CLI implementation)
    uc = container.prompt_uc()
    result = uc.execute(ghsa="GHSA-TEST", force_reclone=False)

    assert isinstance(result, str)
    assert "GHSA-TEST" in result
    assert "You are a security reviewer" in result
    assert "--- DIFF (unified) ---" in result
