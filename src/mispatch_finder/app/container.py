from __future__ import annotations

from dependency_injector import containers, providers

from .config import AppConfig
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
from ..infra.analysis_store import AnalysisStore
from ..infra.cache import Cache
from ..infra.logging import AnalysisLogger


class Container(containers.DeclarativeContainer):
    """DI container with Pydantic BaseSettings support."""

    # Configuration - supports Pydantic models
    config = providers.Configuration(pydantic_settings=[AppConfig()])

    # Adapters with injected config
    vuln_data = providers.Singleton(
        VulnerabilityDataAdapter,
        github_token=config.github.token,
        cache_dir=config.directories.cache_dir,
    )

    repo = providers.Singleton(
        Repository,
        cache_dir=config.directories.cache_dir,
    )

    analysis_store = providers.Singleton(
        AnalysisStore,
        analysis_dir=config.directories.logs_dir,
    )

    cache = providers.Singleton(
        Cache,
        cache_dir=config.directories.cache_dir,
    )

    token_gen = providers.Singleton(DefaultTokenGenerator)

    # Logger (Resource: manages lifecycle with init/shutdown)
    logger = providers.Resource(
        AnalysisLogger,
        ghsa=config.runtime.ghsa,
        logs_dir=config.directories.logs_dir,
        logger_name=config.logging.logger_name,
        console_output=config.logging.console_output,
        level=config.logging.level,
    )

    # MCP Server (now with logger injection)
    mcp_server = providers.Factory(
        MCPServer,
        port=18080,  # Default MCP port
        logger=logger,
    )

    # LLM adapter (now with logger injection)
    llm = providers.Factory(
        LLM,
        provider=config.llm.provider_name,
        model=config.llm.model_name,
        api_key=config.llm.api_key,
        logger=logger,
    )

    # Domain services
    diff_service = providers.Factory(
        DiffService,
        repo=repo,
        max_chars=config.analysis.diff_max_chars,
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
    )

    list_uc = providers.Factory(
        ListUseCase,
        vuln_data=vuln_data,
        analysis_store=analysis_store,
    )

    clear_cache_uc = providers.Factory(
        ClearCacheUseCase,
        cache=cache,
        vuln_data=vuln_data,
    )

    logs_uc = providers.Factory(
        LogsUseCase,
        analysis_store=analysis_store,
    )
