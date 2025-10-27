from __future__ import annotations

import os
from pathlib import Path

from platformdirs import PlatformDirs


APP_NAME = "mispatch_finder"


def _dirs() -> PlatformDirs:
    return PlatformDirs(appname=APP_NAME, appauthor=False)


def _get_home_dir() -> Path:
    """Resolve the application home directory.

    Precedence:
    - MISPATCH_HOME if set
    - platformdirs user_cache_dir as base
    """
    env = os.environ.get("MISPATCH_HOME")
    if env:
        home = Path(os.path.expanduser(os.path.expandvars(env)))
    else:
        home = Path(_dirs().user_cache_dir)
    home.mkdir(parents=True, exist_ok=True)
    return home


def get_cache_dir() -> Path:
    # Use MISPATCH_HOME base; no per-dir env required
    path = _get_home_dir() / "cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_results_dir() -> Path:
    # Use MISPATCH_HOME base; no per-dir env required
    path = _get_home_dir() / "results"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_logs_dir() -> Path:
    # Use MISPATCH_HOME base; no per-dir env required
    path = _get_home_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_github_token(env_var: str = "GITHUB_TOKEN") -> str | None:
    return os.environ.get(env_var)


def get_model_api_key(env_var: str = "MODEL_API_KEY") -> str | None:
    """Return the unified model API key from env.

    Primary: MODEL_API_KEY
    Fallbacks: OPENAI_API_KEY, ANTHROPIC_API_KEY
    """
    return (
        os.environ.get(env_var)
        or os.environ.get("OPENAI_API_KEY")
        or os.environ.get("ANTHROPIC_API_KEY")
    )


def get_prompt_diff_max_chars(env_var: str = "MISPATCH_DIFF_MAX_CHARS") -> int:
    """Maximum characters of diff included in prompt (middle-truncated if exceeded)."""
    default = 200_000
    val = os.environ.get(env_var)
    if not val:
        return default
    num = int(val)
    return num if num > 0 else default


def get_ecosystem(env_var: str = "MISPATCH_ECOSYSTEM") -> str:
    """Get the target vulnerability ecosystem.

    Supported ecosystems: npm, pypi, Maven, Go, etc.
    See cve_collector documentation for full list.

    Default: npm
    """
    return os.environ.get(env_var, "npm")


def get_default_filter_expr(env_var: str = "MISPATCH_FILTER_EXPR") -> str:
    """Get the default filter expression for vulnerability listing.

    Filter uses asteval syntax with available variables:
    - ghsa_id, cve_id, has_cve, severity, summary, description
    - published_at, modified_at, ecosystem, repo_slug
    - stars, size_bytes, repo_count, commit_count, poc_count

    Note: Many fields can be None, so use 'is not None' checks before comparisons.

    Default: "stars is not None and stars>=100 and size_bytes is not None and size_bytes<=10_000_000"
    (Repositories with ≥100 stars and ≤10MB size)
    """
    return os.environ.get(
        env_var,
        "stars is not None and stars>=100 and size_bytes is not None and size_bytes<=10_000_000"
    )


