"""Tests for Pydantic BaseSettings configuration."""
import pytest
from pathlib import Path

from mispatch_finder.app.config import (
    AppConfig,
    DirectoryConfig,
    LLMConfig,
    GitHubConfig,
    VulnerabilityConfig,
    AnalysisConfig,
)


def test_directory_config_default_home():
    """Test that DirectoryConfig uses default home from platformdirs."""
    # DirectoryConfig should use platformdirs by default
    config = DirectoryConfig()
    assert config.home.exists()


def test_directory_config_computed_paths(tmp_path):
    """Test that computed paths are created automatically."""
    config = DirectoryConfig(home=tmp_path)

    # Computed fields should return Path objects
    assert isinstance(config.cache_dir, Path)
    assert isinstance(config.results_dir, Path)
    assert isinstance(config.logs_dir, Path)

    # Directories should be created automatically
    assert config.cache_dir.exists()
    assert config.results_dir.exists()
    assert config.logs_dir.exists()

    # Paths should be relative to home
    assert config.cache_dir == tmp_path / "cache"
    assert config.results_dir == tmp_path / "results"
    assert config.logs_dir == tmp_path / "logs"


def test_llm_config_defaults():
    """Test LLM config default values."""
    config = LLMConfig()

    assert config.api_key is None
    assert config.provider_name == "openai"
    assert config.model_name == "gpt-5"


def test_github_config_defaults():
    """Test GitHub config default values."""
    config = GitHubConfig()
    assert config.token is None


def test_vulnerability_config_defaults():
    """Test vulnerability config default values."""
    config = VulnerabilityConfig()

    assert config.ecosystem == "npm"
    assert "stars" in config.filter_expr
    assert "100" in config.filter_expr


def test_analysis_config_defaults():
    """Test analysis config default values."""
    config = AnalysisConfig()
    assert config.diff_max_chars == 200_000


def test_app_config_from_env(monkeypatch):
    """Test AppConfig loads from environment variables."""
    monkeypatch.setenv("MISPATCH_FINDER_LLM__API_KEY", "test-key")
    monkeypatch.setenv("MISPATCH_FINDER_GITHUB__TOKEN", "test-token")
    monkeypatch.setenv("MISPATCH_FINDER_LLM__PROVIDER_NAME", "anthropic")
    monkeypatch.setenv("MISPATCH_FINDER_VULNERABILITY__ECOSYSTEM", "pypi")
    monkeypatch.setenv("MISPATCH_FINDER_ANALYSIS__DIFF_MAX_CHARS", "300000")

    config = AppConfig()

    assert config.llm.api_key == "test-key"
    assert config.github.token == "test-token"
    assert config.llm.provider_name == "anthropic"
    assert config.vulnerability.ecosystem == "pypi"
    assert config.analysis.diff_max_chars == 300000


def test_app_config_explicit_values(tmp_path):
    """Test AppConfig with explicitly provided values."""
    config = AppConfig(
        directories=DirectoryConfig(home=tmp_path),
        llm=LLMConfig(
            api_key="explicit-key",
            provider_name="openai",
            model_name="gpt-4",
        ),
        github=GitHubConfig(token="explicit-token"),
        vulnerability=VulnerabilityConfig(ecosystem="maven"),
        analysis=AnalysisConfig(diff_max_chars=100000),
    )

    assert config.directories.home == tmp_path
    assert config.llm.api_key == "explicit-key"
    assert config.github.token == "explicit-token"
    assert config.vulnerability.ecosystem == "maven"
    assert config.analysis.diff_max_chars == 100000


def test_app_config_frozen():
    """Test that AppConfig is immutable."""
    from pydantic import ValidationError

    config = AppConfig()

    # Pydantic v2 frozen models raise ValidationError when trying to modify
    with pytest.raises(ValidationError, match="frozen"):
        config.llm = LLMConfig(api_key="new-key")  # type: ignore


def test_app_config_nested_env_delimiter(monkeypatch):
    """Test nested config with double underscore delimiter."""
    monkeypatch.setenv("MISPATCH_FINDER_LLM__MODEL_NAME", "gpt-5")

    config = AppConfig()

    assert config.llm.model_name == "gpt-5"


def test_directory_config_custom_home(tmp_path):
    """Test DirectoryConfig with custom home directory."""
    custom_home = tmp_path / "custom"
    config = DirectoryConfig(home=custom_home)

    assert config.home == custom_home
    assert config.cache_dir == custom_home / "cache"
    assert config.results_dir == custom_home / "results"
    assert config.logs_dir == custom_home / "logs"
