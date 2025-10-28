from __future__ import annotations

from .config import AppConfig
from .container import Container
from ..core.domain.models import Vulnerability
from ..core.usecases.list import ListUseCase


def _create_container(config: AppConfig | None = None) -> Container:
    """Create and initialize a container.

    Args:
        config: Optional config. If None, loads from environment variables.

    Returns:
        Initialized container instance
    """
    container = Container()

    if config is None:
        # Load from environment variables (BaseSettings default behavior)
        config = AppConfig()

    container.config.from_pydantic(config)
    container.init_resources()

    return container


def analyze(
    ghsa: str,
    *,
    provider: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
    github_token: str | None = None,
    force_reclone: bool = False,
    config: AppConfig | None = None,
) -> dict[str, object]:
    """Analyze a vulnerability for potential mispatches.

    Args:
        ghsa: GHSA identifier (e.g., GHSA-xxxx-xxxx-xxxx)
        provider: LLM provider override (optional)
        model: LLM model override (optional)
        api_key: LLM API key override (optional, otherwise from config/env)
        github_token: GitHub token override (optional, otherwise from config/env)
        force_reclone: Force re-clone of repository cache
        config: Optional config for testing. If None, loads from env vars.

    Returns:
        Analysis result dictionary

    Raises:
        ValueError: If required credentials are missing
    """
    container = _create_container(config)

    # Runtime params override config
    llm_api_key = api_key or container.config.llm.api_key()
    gh_token = github_token or container.config.github.token()

    if not llm_api_key:
        raise ValueError("API key required via MISPATCH_FINDER_LLM__API_KEY")
    if not gh_token:
        raise ValueError("GitHub token required via MISPATCH_FINDER_GITHUB__TOKEN")

    # Override LLM config if runtime params provided
    if provider or model or api_key:
        # Create new LLM instance with overrides
        from ..infra.llm import LLM

        llm = LLM(
            provider=provider or container.config.llm.provider_name(),
            model=model or container.config.llm.model_name(),
            api_key=llm_api_key,
        )
        # Temporarily override orchestrator's LLM
        orchestrator = container.analysis_orchestrator()
        orchestrator._llm = llm
    else:
        orchestrator = container.analysis_orchestrator()

    # Execute use case
    uc = container.analyze_uc()
    return uc.execute(ghsa=ghsa, force_reclone=force_reclone)


def list_vulnerabilities(
    detailed: bool = False,
    filter_expr: str | None = None,
    config: AppConfig | None = None,
) -> list[str] | list[Vulnerability]:
    """List available vulnerabilities from the database.

    Args:
        detailed: If True, return full Vulnerability objects; if False, return GHSA IDs
        filter_expr: Filter expression (None = use default, "" = no filter)
        config: Optional config for testing. If None, loads from env vars.

    Returns:
        list[str] if detailed=False, list[Vulnerability] if detailed=True
    """
    container = _create_container(config)

    # Handle filter: None = use default, "" = no filter, otherwise = custom
    actual_filter: str | None
    if filter_expr is None:
        actual_filter = container.config.vulnerability.filter_expr()
    elif filter_expr == "":
        actual_filter = None  # No filter
    else:
        actual_filter = filter_expr

    # Create use case with parameters
    limit = 10  # Default list limit
    ecosystem = container.config.vulnerability.ecosystem()

    uc = ListUseCase(
        vuln_data=container.vuln_data(),
        limit=limit,
        ecosystem=ecosystem,
        detailed=detailed,
        filter_expr=actual_filter,
    )
    return uc.execute()


def clear(config: AppConfig | None = None) -> None:
    """Clear all caches.

    Args:
        config: Optional config for testing. If None, loads from env vars.
    """
    container = _create_container(config)
    uc = container.clear_cache_uc()
    uc.execute()


def logs(
    ghsa: str | None = None,
    verbose: bool = False,
    config: AppConfig | None = None,
) -> list[str]:
    """Show analysis logs.

    Args:
        ghsa: Optional GHSA ID. If None, shows summary of all runs.
        verbose: Show detailed information
        config: Optional config for testing. If None, loads from env vars.

    Returns:
        List of log lines
    """
    container = _create_container(config)
    uc = container.logs_uc()
    return uc.execute(ghsa, verbose)
