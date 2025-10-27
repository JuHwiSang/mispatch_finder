from __future__ import annotations

from dependency_injector import containers, providers

from ..core.ports import DefaultTokenGenerator
from ..core.usecases.analyze import AnalyzeUseCase
from ..core.usecases.list import ListUseCase
from ..core.usecases.clear_cache import ClearCacheUseCase
from ..core.usecases.logs import LogsUseCase
from ..core.services import DiffService, JsonExtractor, AnalysisOrchestrator
from ..infra.vulnerability_data import VulnerabilityDataAdapter
from ..infra.repository import Repository
from ..infra.mcp_server import MCPServer
from ..infra.llm import LLM
from ..infra.result_store import ResultStore
from ..infra.log_store import LogStore
from ..infra.cache import Cache
from ..infra.logging import AnalysisLogger


class Container(containers.DeclarativeContainer):
    # Configuration
    config = providers.Configuration()

    # Adapters with injected config
    vuln_data = providers.Singleton(
        VulnerabilityDataAdapter,
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

    # Logger
    logger = providers.Singleton(AnalysisLogger, logger_name="mispatch_finder")

    # LLM adapter (parameterized)
    llm = providers.Factory(
        LLM,
        provider=config.llm_provider_name,
        model=config.llm_model_name,
        api_key=config.llm_api_key,
    )

    # Domain services
    diff_service = providers.Factory(
        DiffService,
        repo=repo,
        max_chars=config.prompt_diff_max_chars.as_int(),
    )

    json_extractor = providers.Singleton(JsonExtractor)

    analysis_orchestrator = providers.Factory(
        AnalysisOrchestrator,
        vuln_data=vuln_data,
        repo=repo,
        mcp=mcp_server,
        llm=llm,
        token_gen=token_gen,
        logger=logger,
        diff_service=diff_service,
        json_extractor=json_extractor,
    )

    # Use cases
    analyze_uc = providers.Factory(
        AnalyzeUseCase,
        orchestrator=analysis_orchestrator,
        store=result_store,
    )

    list_uc = providers.Factory(
        ListUseCase,
        vuln_data=vuln_data,
        limit=config.list_limit.as_int(),
        ecosystem=config.ecosystem,
    )

    clear_cache_uc = providers.Factory(
        ClearCacheUseCase,
        cache=cache,
        vuln_data=vuln_data,
    )

    logs_uc = providers.Factory(
        LogsUseCase,
        log_store=log_store,
    )
