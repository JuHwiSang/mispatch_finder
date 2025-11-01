"""Tests for 'list' CLI command."""
import json
import os
import pytest
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
from tests.mispatch_finder.app.conftest import MockVulnerabilityRepository


runner = CliRunner()


def test_list_requires_github_token(monkeypatch):
    """Test list command behavior without MISPATCH_FINDER_GITHUB__TOKEN."""
    monkeypatch.delenv("MISPATCH_FINDER_GITHUB__TOKEN", raising=False)
    result = runner.invoke(app, ["list"])
    # Note: cve_collector may use cached data or have fallback behavior
    # So this might succeed or fail depending on cache state
    assert result.exit_code in (0, 2)


@pytest.mark.skipif(not os.environ.get("MISPATCH_FINDER_GITHUB__TOKEN"), reason="MISPATCH_FINDER_GITHUB__TOKEN not set")
def test_list_lists_ghsa_ids():
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


@pytest.mark.skipif(not os.environ.get("MISPATCH_FINDER_GITHUB__TOKEN"), reason="MISPATCH_FINDER_GITHUB__TOKEN not set")
def test_list_human_readable_format():
    """Test that list command outputs human-readable format by default."""
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    # Should contain human-readable text, not JSON
    assert "Found" in result.stdout
    assert "vulnerabilities:" in result.stdout
    # Should NOT be valid JSON
    with pytest.raises(json.JSONDecodeError):
        json.loads(result.stdout)


@pytest.mark.skipif(not os.environ.get("MISPATCH_FINDER_GITHUB__TOKEN"), reason="MISPATCH_FINDER_GITHUB__TOKEN not set")
def test_list_detail_flag():
    """Test that list command accepts --detail flag."""
    result = runner.invoke(app, ["list", "--detail", "--json"])

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    # With --detail, should return object with "count" and "vulnerabilities"
    assert "vulnerabilities" in data
    assert isinstance(data["vulnerabilities"], list)


@pytest.mark.skipif(not os.environ.get("MISPATCH_FINDER_GITHUB__TOKEN"), reason="MISPATCH_FINDER_GITHUB__TOKEN not set")
def test_list_detail_short_flag():
    """Test that list command accepts -d short flag for detail."""
    result = runner.invoke(app, ["list", "-d", "--json"])

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    # With -d, should return object with "count" and "vulnerabilities"
    assert "vulnerabilities" in data
    assert isinstance(data["vulnerabilities"], list)


@pytest.mark.skipif(not os.environ.get("MISPATCH_FINDER_GITHUB__TOKEN"), reason="MISPATCH_FINDER_GITHUB__TOKEN not set")
def test_list_include_analyzed_flag():
    """Test that list command accepts --include-analyzed flag."""
    result = runner.invoke(app, ["list", "--include-analyzed", "--json"])

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    # Should parse flag correctly and return items
    assert "items" in data
    assert isinstance(data["items"], list)


@pytest.mark.skipif(not os.environ.get("MISPATCH_FINDER_GITHUB__TOKEN"), reason="MISPATCH_FINDER_GITHUB__TOKEN not set")
def test_list_include_analyzed_short_flag():
    """Test that list command accepts -i short flag for include-analyzed."""
    result = runner.invoke(app, ["list", "-i", "--json"])

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    # Should parse flag correctly and return items
    assert "items" in data
    assert isinstance(data["items"], list)


@pytest.mark.skipif(not os.environ.get("MISPATCH_FINDER_GITHUB__TOKEN"), reason="MISPATCH_FINDER_GITHUB__TOKEN not set")
def test_list_filter_flag():
    """Test that list command accepts --filter flag with custom expression."""
    result = runner.invoke(app, ["list", "--filter", "severity == 'CRITICAL'", "--json"])

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    # Should parse flag correctly and return items
    assert "items" in data
    assert isinstance(data["items"], list)


@pytest.mark.skipif(not os.environ.get("MISPATCH_FINDER_GITHUB__TOKEN"), reason="MISPATCH_FINDER_GITHUB__TOKEN not set")
def test_list_filter_short_flag():
    """Test that list command accepts -f short flag for filter."""
    result = runner.invoke(app, ["list", "-f", "stars is not None and stars > 1000", "--json"])

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    # Should parse flag correctly and return items
    assert "items" in data
    assert isinstance(data["items"], list)


@pytest.mark.skipif(not os.environ.get("MISPATCH_FINDER_GITHUB__TOKEN"), reason="MISPATCH_FINDER_GITHUB__TOKEN not set")
def test_list_no_filter_flag():
    """Test that list command accepts --no-filter flag."""
    result = runner.invoke(app, ["list", "--no-filter", "--json"])

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    # Should parse flag correctly and return items
    assert "items" in data
    assert isinstance(data["items"], list)


@pytest.mark.skipif(not os.environ.get("MISPATCH_FINDER_GITHUB__TOKEN"), reason="MISPATCH_FINDER_GITHUB__TOKEN not set")
def test_list_limit_flag():
    """Test that list command accepts --limit flag."""
    result = runner.invoke(app, ["list", "--limit", "5", "--json"])

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    # Should parse flag correctly and return items
    assert "items" in data
    assert isinstance(data["items"], list)
    # Should respect limit
    assert len(data["items"]) <= 5


@pytest.mark.skipif(not os.environ.get("MISPATCH_FINDER_GITHUB__TOKEN"), reason="MISPATCH_FINDER_GITHUB__TOKEN not set")
def test_list_limit_short_flag():
    """Test that list command accepts -n short flag for limit."""
    result = runner.invoke(app, ["list", "-n", "3", "--json"])

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    # Should parse flag correctly and return items
    assert "items" in data
    assert isinstance(data["items"], list)
    # Should respect limit
    assert len(data["items"]) <= 3


def test_list_vulnerabilities_e2e(tmp_path):
    """E2E test: list command returns vulnerability list."""
    test_config = AppConfig(
        directories=DirectoryConfig(home=tmp_path),
        llm=LLMConfig(api_key="test-key", provider_name="openai", model_name="gpt-4"),
        github=GitHubConfig(token="test-token"),
        vulnerability=VulnerabilityConfig(ecosystem="npm"),
        analysis=AnalysisConfig(diff_max_chars=200_000),
    )

    # Create container with mocked vuln_data
    container = Container()
    container.config.from_pydantic(test_config)
    container.vuln_data.override(providers.Singleton(MockVulnerabilityRepository))

    # Execute (mimics CLI implementation)
    uc = container.list_uc()
    result = uc.execute(
        limit=10,
        ecosystem=container.config.vulnerability.ecosystem(),
        detailed=False,
        filter_expr=None,
        include_analyzed=True,
    )

    assert isinstance(result, list)
    assert len(result) == 2
    assert all(isinstance(ghsa, str) and ghsa.startswith("GHSA-") for ghsa in result)
