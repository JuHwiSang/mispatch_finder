from __future__ import annotations

from dependency_injector import containers, providers

from ..core.ports import DefaultTokenGenerator
from ..core.usecases.run_analysis import RunAnalysisUseCase
from ..core.usecases.list_ghsa import ListGHSAUseCase
from ..core.usecases.clear_cache import ClearCacheUseCase
from ..core.usecases.show_log import ShowLogUseCase
from ..infra.adapters.vulnerability_repository import VulnerabilityRepository
from ..infra.adapters.repository import Repository
from ..infra.adapters.mcp_server import MCPServer
from ..infra.adapters.llm import LLM
from ..infra.adapters.result_store import ResultStore
from ..infra.adapters.log_store import LogStore
from ..infra.adapters.cache import Cache


class Container(containers.DeclarativeContainer):
    # Configuration
    config = providers.Configuration()

    # Adapters with injected config
    vuln_repo = providers.Singleton(
        VulnerabilityRepository,
        github_token=config.github_token,
    )

    repo = providers.Singleton(
        Repository,
        cache_dir=config.cache_dir,
    )

    mcp_server = providers.Factory(
        MCPServer,
        port=config.mcp_port.as_int(),
    )

    result_store = providers.Singleton(
        ResultStore,
        results_dir=config.results_dir,
    )

    log_store = providers.Singleton(
        LogStore,
        logs_dir=config.logs_dir,
    )

    cache = providers.Singleton(
        Cache,
        cache_dir=config.cache_dir,
    )

    token_gen = providers.Singleton(DefaultTokenGenerator)

    # LLM adapter (parameterized)
    llm = providers.Factory(
        LLM,
        provider=config.llm_provider_name,
        model=config.llm_model_name,
        api_key=config.llm_api_key,
    )

    # Use cases
    run_analysis = providers.Factory(
        RunAnalysisUseCase,
        vuln_repo=vuln_repo,
        repo=repo,
        mcp=mcp_server,
        llm=llm,
        store=result_store,
        token_gen=token_gen,
        prompt_diff_max_chars=config.prompt_diff_max_chars.as_int(),
    )

    list_ghsa = providers.Factory(
        ListGHSAUseCase,
        vuln_repo=vuln_repo,
        limit=config.list_limit.as_int(),
    )

    clear_cache_uc = providers.Factory(
        ClearCacheUseCase,
        cache=cache,
        vuln_repo=vuln_repo,
    )

    show_log = providers.Factory(
        ShowLogUseCase,
        log_store=log_store,
    )
