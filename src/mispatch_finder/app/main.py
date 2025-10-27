from __future__ import annotations

import functools
from typing import Callable, Concatenate, ParamSpec, TypeVar

from .config import (
    get_cache_dir,
    get_default_filter_expr,
    get_ecosystem,
    get_github_token,
    get_logs_dir,
    get_model_api_key,
    get_prompt_diff_max_chars,
    get_results_dir,
)
from .container import Container
from ..core.domain.models import Vulnerability
from ..core.usecases.list import ListUseCase

P = ParamSpec("P")
R = TypeVar("R")


def _get_default_config() -> dict[str, object]:
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
        "list_limit": 10,
        "ecosystem": get_ecosystem(),
        "default_filter_expr": get_default_filter_expr(),
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
def analyze(
    container: Container,
    *,
    ghsa: str,
    force_reclone: bool = False,
    provider: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
    github_token: str | None = None,
) -> dict[str, object]:
    """Run analysis via use case."""
    uc = container.analyze_uc()
    return uc.execute(ghsa=ghsa, force_reclone=force_reclone)


@with_container
def list_vulnerabilities(
    container: Container,
    detailed: bool = False,
    filter_expr: str | None = None,
    **kwargs
) -> list[str] | list[Vulnerability]:
    """List vulnerabilities with optional detailed metadata.

    Args:
        detailed: If True, return full Vulnerability objects; if False, return GHSA IDs only
        filter_expr: Optional asteval filter expression (None = use default from config)

    Returns:
        list[str] if detailed=False, list[Vulnerability] if detailed=True
    """
    # Create use case with custom parameters
    limit: int = int(container.config.list_limit())
    ecosystem: str = str(container.config.ecosystem())

    # Handle filter: None = use default, empty string = no filter, otherwise = custom filter
    actual_filter: str | None
    if filter_expr is None:
        actual_filter = str(container.config.default_filter_expr())
    elif filter_expr == "":
        actual_filter = None  # No filter
    else:
        actual_filter = filter_expr

    uc = ListUseCase(
        vuln_data=container.vuln_data(),
        limit=limit,
        ecosystem=ecosystem,
        detailed=detailed,
        filter_expr=actual_filter,
    )
    return uc.execute()


@with_container
def list_ids(container: Container, **kwargs) -> list[str]:
    """List available GHSA IDs without default filter (backward compatibility).

    Note: This function does NOT apply the default filter to maintain backward compatibility.
    Use list_vulnerabilities() for filtered results.
    """
    from ..core.usecases.list import ListUseCase

    limit: int = int(container.config.list_limit())
    ecosystem: str = str(container.config.ecosystem())

    # Explicitly no filter for backward compatibility
    uc = ListUseCase(
        vuln_data=container.vuln_data(),
        limit=limit,
        ecosystem=ecosystem,
        detailed=False,
        filter_expr=None,
    )
    return uc.execute()


@with_container
def clear(container: Container, **kwargs) -> None:
    """Clear all caches."""
    uc = container.clear_cache_uc()
    uc.execute()


@with_container
def logs(container: Container, ghsa: str | None, verbose: bool, **kwargs) -> list[str]:
    """Show log summary or details for a specific GHSA."""
    uc = container.logs_uc()
    return uc.execute(ghsa, verbose)
