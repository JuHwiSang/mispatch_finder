from __future__ import annotations

from pathlib import Path

from platformdirs import PlatformDirs
from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


APP_NAME = "mispatch_finder"


def _default_home() -> Path:
    """Get default home directory using platformdirs."""
    return Path(PlatformDirs(appname=APP_NAME, appauthor=False).user_cache_dir)


class DirectoryConfig(BaseSettings):
    """Directory configuration with computed paths."""

    home: Path = Field(
        default_factory=_default_home,
        description="Base directory for all mispatch_finder data",
    )

    @computed_field
    @property
    def cache_dir(self) -> Path:
        """Cache directory for cloned repositories."""
        path = self.home / "cache"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @computed_field
    @property
    def results_dir(self) -> Path:
        """Results directory for analysis outputs."""
        path = self.home / "results"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @computed_field
    @property
    def logs_dir(self) -> Path:
        """Logs directory for analysis logs."""
        path = self.home / "logs"
        path.mkdir(parents=True, exist_ok=True)
        return path


class VulnerabilityConfig(BaseSettings):
    """Vulnerability filtering configuration."""

    ecosystem: str = Field(
        default="npm",
        description="Target vulnerability ecosystem (npm, pypi, Maven, Go, etc.)",
    )

    filter_expr: str = Field(
        default="stars is not None and stars>=100 and size_bytes is not None and size_bytes<=10_000_000",
        description=(
            "Default filter expression for vulnerability listing. "
            "Available variables: ghsa_id, cve_id, severity, stars, size_bytes, etc. "
            "Uses asteval syntax."
        ),
    )


class LLMConfig(BaseSettings):
    """LLM configuration."""

    api_key: str | None = Field(
        default=None,
        description="LLM API key (supports OpenAI, Anthropic, etc.)",
    )

    provider_name: str = Field(
        default="openai",
        description="LLM provider (openai, anthropic)",
    )

    model_name: str = Field(
        default="gpt-5",
        description="LLM model name",
    )


class GitHubConfig(BaseSettings):
    """GitHub configuration."""

    token: str | None = Field(
        default=None,
        description="GitHub personal access token",
    )


class AnalysisConfig(BaseSettings):
    """Analysis-specific settings."""

    diff_max_chars: int = Field(
        default=200_000,
        description="Maximum diff characters to include in LLM prompt (middle-truncated if exceeded)",
    )


class AppConfig(BaseSettings):
    """Root application configuration.

    All configuration is loaded from environment variables with MISPATCH_FINDER_ prefix.
    Use double underscore for nested config: MISPATCH_FINDER_LLM__API_KEY

    Example env vars:
        # Required
        export MISPATCH_FINDER_GITHUB__TOKEN=ghp_xxxxxxxxxxxxx
        export MISPATCH_FINDER_LLM__API_KEY=sk-xxxxxxxxxxxxx

        # Optional (with defaults)
        export MISPATCH_FINDER_LLM__PROVIDER_NAME=openai
        export MISPATCH_FINDER_LLM__MODEL_NAME=gpt-4
        export MISPATCH_FINDER_VULNERABILITY__ECOSYSTEM=npm
        export MISPATCH_FINDER_DIRECTORIES__HOME=/custom/path
        export MISPATCH_FINDER_ANALYSIS__DIFF_MAX_CHARS=200000
    """

    model_config = SettingsConfigDict(
        env_prefix="MISPATCH_FINDER_",
        env_nested_delimiter="__",
        frozen=True,
        extra="forbid",
    )

    directories: DirectoryConfig = Field(default_factory=DirectoryConfig)
    vulnerability: VulnerabilityConfig = Field(default_factory=VulnerabilityConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    github: GitHubConfig = Field(default_factory=GitHubConfig)
    analysis: AnalysisConfig = Field(default_factory=AnalysisConfig)
