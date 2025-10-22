from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

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


def get_github_token(env_var: str = "GITHUB_TOKEN") -> Optional[str]:
    return os.environ.get(env_var)


def get_model_api_key(env_var: str = "MODEL_API_KEY") -> Optional[str]:
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


