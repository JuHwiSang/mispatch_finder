from __future__ import annotations

import functools
from typing import Callable, Concatenate, Dict, ParamSpec, TypeVar

from .config import (
    get_cache_dir,
    get_ecosystem,
    get_github_token,
    get_logs_dir,
    get_model_api_key,
    get_prompt_diff_max_chars,
    get_results_dir,
)
from .container import Container

P = ParamSpec("P")
R = TypeVar("R")


def _get_default_config() -> dict:
    """Get default configuration dictionary."""
    return {
        "github_token": get_github_token(),
        "llm_api_key": get_model_api_key(),
        "llm_provider_name": "openai",
        "llm_model_name": "gpt-4",
        "cache_dir": get_cache_dir(),
        "results_dir": get_results_dir(),
        "logs_dir": get_logs_dir(),
        "mcp_port": 18080,
        "prompt_diff_max_chars": get_prompt_diff_max_chars(),
        "list_limit": 500,
        "ecosystem": get_ecosystem(),
    }


def with_container(
    func: Callable[Concatenate[Container, P], R]
) -> Callable[P, R]:
    """Automate container creation, configuration, and resource management.
    
    Preserves type hints while injecting container as the first argument.
    Maps CLI-friendly parameter names to internal config keys.
    """

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        container = Container()

        # Map CLI parameter names to config keys
        param_to_config = {
            "provider": "llm_provider_name",
            "model": "llm_model_name",
            "api_key": "llm_api_key",
        }

        # Override config with kwargs that match config keys
        config = _get_default_config()
        config_keys = config.keys()
        
        for param_name, value in kwargs.items():
            if value is None:
                continue
            # Map parameter name to config key if needed
            config_key = param_to_config.get(param_name, param_name)
            if config_key in config_keys:
                config[config_key] = value

        container.config.from_dict(config)
        container.init_resources()
        try:
            return func(container, *args, **kwargs)
        finally:
            container.shutdown_resources()

    return wrapper


@with_container
def run_analysis(
    container: Container,
    *,
    ghsa: str,
    force_reclone: bool = False,
    provider: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
    github_token: str | None = None,
) -> Dict[str, object]:
    """Run analysis via use case."""
    uc = container.run_analysis()
    return uc.execute(ghsa=ghsa, force_reclone=force_reclone)


@with_container
def list_ghsa_ids(container: Container, **kwargs) -> list[str]:
    """List available GHSA IDs."""
    uc = container.list_ghsa()
    return uc.execute()


@with_container
def list_ghsa_with_metadata(container: Container, limit: int = 500, ecosystem: str | None = None, **kwargs) -> list:
    """List GHSA IDs with full metadata (repos, commits, size).

    Args:
        container: Dependency injection container
        limit: Maximum number of vulnerabilities to return
        ecosystem: Ecosystem to filter by (npm, pypi, etc.). If None, uses config default.
    """
    vuln_repo = container.vuln_repo()
    eco = ecosystem if ecosystem is not None else get_ecosystem()
    return vuln_repo.list_with_metadata(limit=limit, ecosystem=eco)


@with_container
def clear_all_caches(container: Container, **kwargs) -> None:
    """Clear all caches."""
    uc = container.clear_cache_uc()
    uc.execute()


@with_container
def show_log(container: Container, ghsa: str | None, verbose: bool, **kwargs) -> list[str]:
    """Show log summary or details for a specific GHSA."""
    uc = container.show_log()
    return uc.execute(ghsa, verbose)
