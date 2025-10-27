# Claude Code Context - Mispatch Finder

## Project Overview

**Mispatch Finder** is a security analysis tool that detects potential mispatch vulnerabilities in software patches. It analyzes GitHub Security Advisories (GHSA) to identify cases where security patches may have been incorrectly applied or missed entirely.

### Architecture

The project follows **Domain-Driven Design (DDD)** with clean architecture principles:

```
src/mispatch_finder/
├── app/                    # Application Layer (CLI, DI Container, Config)
├── core/                   # Core Domain Layer (Business Logic)
│   ├── domain/            # Domain Models & Entities
│   ├── services/          # Domain Services (Business Logic)
│   ├── usecases/          # Use Cases (Application Logic)
│   └── ports.py           # Port Interfaces (Dependency Inversion)
├── infra/                 # Infrastructure Layer (Adapters)
│   ├── llm_adapters/      # LLM Provider Adapters (OpenAI, Anthropic)
│   ├── logging/           # Structured Logging
│   └── mcp/              # Model Context Protocol Servers
└── shared/                # Shared Utilities
```

## Key Design Principles

### 1. Dependency Inversion
- **Core never depends on infra** - only on Ports (protocols)
- Infra implements Ports and is injected via DI container
- Example: `AnalysisOrchestrator` uses `LoggerPort`, not `AnalysisLogger`

### 2. Service Layer Pattern
- Business logic resides in `core/services/`:
  - `DiffService`: Diff generation and truncation
  - `JsonExtractor`: JSON extraction from LLM responses
  - `AnalysisOrchestrator`: Complete analysis workflow coordination
- UseCases are thin orchestration layers (73% code reduction achieved)

### 3. Ports & Adapters
All external dependencies are abstracted through Ports:
- `VulnerabilityDataPort` → `VulnerabilityDataAdapter` (cve_collector adapter)
- `RepositoryPort` → `GitRepository` (git operations)
- `MCPServerPort` → `MCPServer` (MCP server management)
- `LLMPort` → `LLM` (LLM API adapter)
- `LoggerPort` → `AnalysisLogger` (structured logging)
- `ResultStorePort`, `LogStorePort`, `CachePort`, `TokenGeneratorPort`

## CLI Commands

Command format: `mispatch-finder <command> [options]`

### Available Commands

1. **`analyze <GHSA-ID>`** - Analyze a single vulnerability
   ```bash
   mispatch-finder analyze GHSA-xxxx-xxxx-xxxx --provider openai --model gpt-4
   ```
   - UseCase: `AnalyzeUseCase` ([core/usecases/analyze.py](src/mispatch_finder/core/usecases/analyze.py))
   - Facade: `analyze()` ([app/main.py:81](src/mispatch_finder/app/main.py#L81))

2. **`list`** - List available GHSA IDs
   ```bash
   mispatch-finder list
   ```
   - UseCase: `ListUseCase` ([core/usecases/list.py](src/mispatch_finder/core/usecases/list.py))
   - Facade: `list_ids()` ([app/main.py:97](src/mispatch_finder/app/main.py#L97))

3. **`clear`** - Clear all caches
   ```bash
   mispatch-finder clear
   ```
   - UseCase: `ClearCacheUseCase` ([core/usecases/clear_cache.py](src/mispatch_finder/core/usecases/clear_cache.py))
   - Facade: `clear()` ([app/main.py:104](src/mispatch_finder/app/main.py#L104))

4. **`logs [GHSA-ID]`** - Show analysis logs
   ```bash
   mispatch-finder logs                    # Summary of all runs
   mispatch-finder logs GHSA-xxxx-xxxx-xxxx --verbose  # Detailed logs for specific GHSA
   ```
   - UseCase: `LogsUseCase` ([core/usecases/logs.py](src/mispatch_finder/core/usecases/logs.py))
   - Facade: `logs()` ([app/main.py:111](src/mispatch_finder/app/main.py#L111))

5. **`batch`** - Run batch analysis
   ```bash
   mispatch-finder batch --limit 10 --provider openai --model gpt-4
   ```

## Core Domain Models

### Vulnerability
```python
@dataclass(frozen=True)
class Vulnerability:
    ghsa_id: str
    repository: Repository
    commit_hash: str
    cve_id: Optional[str] = None
    summary: Optional[str] = None
    severity: Optional[str] = None  # "CRITICAL", "HIGH", "MEDIUM", "LOW"
```

### Repository
```python
@dataclass(frozen=True)
class Repository:
    owner: str
    name: str
    ecosystem: Optional[str] = None  # "npm", "pypi", "go"
    star_count: Optional[int] = None
    size_kb: Optional[int] = None
```

## Recent Refactoring (2025-01)

### Phase 1-3: Architecture Overhaul
1. **Service Layer Extraction**
   - Extracted business logic from infra → `core/services/`
   - Created `DiffService`, `JsonExtractor`, `AnalysisOrchestrator`
   - Reduced UseCase complexity by 73% (156 lines → 42 lines)

2. **Logging Infrastructure**
   - Moved logging to `infra/logging/` with DI injection
   - Created `LoggerPort` for dependency inversion
   - Structured JSON logging with payload support

3. **Directory Cleanup**
   - Removed unnecessary `infra/adapters/` nesting
   - Moved all adapters to `infra/` directly

### Phase 4: Naming Consistency
4. **CLI Command Naming** (Clear action verbs)
   - ~~`run`~~ → `analyze`
   - ~~`show`~~ → `list` (for GHSA listing)
   - ~~`all`~~ → `batch`
   - ~~`log`~~ → `logs`

5. **UseCase Renaming** (Match command names)
   - ~~`RunAnalysisUseCase`~~ → `AnalyzeUseCase`
   - ~~`ListGHSAUseCase`~~ → `ListUseCase`
   - ~~`ShowLogUseCase`~~ → `LogsUseCase`
   - Files: `analyze.py`, `list.py`, `logs.py`

6. **Main Facade Functions**
   - ~~`run_analysis()`~~ → `analyze()`
   - ~~`list_ghsa_ids()`~~ → `list_ids()`
   - ~~`clear_all_caches()`~~ → `clear()`
   - ~~`show_log()`~~ → `logs()`

7. **Removed Unused Code**
   - Deleted `list_ghsa_with_metadata()` from all layers (ports, adapters, tests)
   - Removed duplicate `shared/json_logging.py`

### Phase 5: Code Style
8. **Import Organization**
   - All imports moved to file top (no mid-function imports)
   - Example: `cli.py` now imports `get_github_token` at line 14 instead of line 66

### Phase 6: LLM Adapter Migration (2025-10)
9. **Migrated itdev_llm_adapter to infra/llm_adapters/**
   - Moved from separate module → `infra/llm_adapters/`
   - No longer an external dependency, now part of infra layer
   - Structure:
     - `types.py`: Data types (Toolset, LLMResponse, TokenUsage, Provider)
     - `interface.py`: LLMHostedMCPAdapter protocol
     - `openai_adapter.py`: OpenAI Responses API implementation
     - `anthropic_adapter.py`: Anthropic Messages API implementation
     - `factory.py`: get_adapter() factory function
   - Updated imports in `infra/llm.py`: `from .llm_adapters import Toolset, get_adapter`
   - Migrated tests to `tests/mispatch_finder/infra/llm_adapters/`
   - Reason: No need for separate module, simpler as infra component

### Phase 7: Vulnerability Data Naming Clarity (2025-10)
10. **Renamed VulnerabilityRepository to VulnerabilityDataAdapter**
    - **Port**: `VulnerabilityRepositoryPort` → `VulnerabilityDataPort`
    - **Adapter**: `VulnerabilityRepository` → `VulnerabilityDataAdapter`
    - **File**: `vulnerability_repository.py` → `vulnerability_data.py`
    - **Variables**: All `vuln_repo` → `vuln_data` (container, usecases, services, tests)
    - **Rationale**:
      - Clear distinction from `RepositoryPort` (git operations)
      - "VulnerabilityData" emphasizes data fetching role vs. "Repository" pattern confusion
      - Shorter variable name `vuln_data` improves readability
    - **Impact**: Updated all layers (ports, infra, usecases, services, tests, docs)

## Key Files & Locations

### Application Layer
- **CLI**: [app/cli.py](src/mispatch_finder/app/cli.py) - Typer-based CLI commands
- **Container**: [app/container.py](src/mispatch_finder/app/container.py) - Dependency injection configuration
- **Config**: [app/config.py](src/mispatch_finder/app/config.py) - Environment variable handling
- **Main**: [app/main.py](src/mispatch_finder/app/main.py) - Facade functions with `@with_container` decorator

### Core Layer
- **Domain Models**: [core/domain/models.py](src/mispatch_finder/core/domain/models.py)
- **Prompt Builder**: [core/domain/prompt.py](src/mispatch_finder/core/domain/prompt.py)
- **Services**:
  - [core/services/diff_service.py](src/mispatch_finder/core/services/diff_service.py)
  - [core/services/json_extractor.py](src/mispatch_finder/core/services/json_extractor.py)
  - [core/services/analysis_orchestrator.py](src/mispatch_finder/core/services/analysis_orchestrator.py)
- **Ports**: [core/ports.py](src/mispatch_finder/core/ports.py) - All protocol interfaces

### Infrastructure Layer
- **Vulnerability Data Adapter**: [infra/vulnerability_data.py](src/mispatch_finder/infra/vulnerability_data.py) - cve_collector adapter
- **Git Repository**: [infra/git_repo.py](src/mispatch_finder/infra/git_repo.py) - Git operations
- **LLM**: [infra/llm.py](src/mispatch_finder/infra/llm.py) - LLM API adapter (uses llm_adapters)
- **LLM Adapters**: [infra/llm_adapters/](src/mispatch_finder/infra/llm_adapters/) - Provider implementations
  - [types.py](src/mispatch_finder/infra/llm_adapters/types.py) - Data types (Toolset, LLMResponse, TokenUsage)
  - [interface.py](src/mispatch_finder/infra/llm_adapters/interface.py) - LLMHostedMCPAdapter protocol
  - [openai_adapter.py](src/mispatch_finder/infra/llm_adapters/openai_adapter.py) - OpenAI Responses API
  - [anthropic_adapter.py](src/mispatch_finder/infra/llm_adapters/anthropic_adapter.py) - Anthropic Messages API
  - [factory.py](src/mispatch_finder/infra/llm_adapters/factory.py) - Adapter factory (get_adapter)
- **MCP Server**: [infra/mcp_server.py](src/mispatch_finder/infra/mcp_server.py) - MCP server management
- **Logging**: [infra/logging/](src/mispatch_finder/infra/logging/) - Structured logging components
- **Stores**: [infra/store.py](src/mispatch_finder/infra/store.py), [infra/log_store.py](src/mispatch_finder/infra/log_store.py)

## Testing Strategy

- **Unit Tests** (`tests/mispatch_finder/core/`): Fast tests with fake implementations
- **Integration Tests** (`tests/mispatch_finder/infra/`): Tests with real dependencies
- **E2E Tests** (`tests/mispatch_finder/app/`): Full workflow with mocked external services

### Key Test Files
- [tests/core/test_services.py](tests/mispatch_finder/core/test_services.py) - Service layer tests
- [tests/core/test_usecases.py](tests/mispatch_finder/core/test_usecases.py) - UseCase tests with fakes
- [tests/core/test_usecases_logs.py](tests/mispatch_finder/core/test_usecases_logs.py) - Logs UseCase scenarios
- [tests/app/test_main_facade.py](tests/mispatch_finder/app/test_main_facade.py) - Facade function tests
- [tests/app/conftest.py](tests/mispatch_finder/app/conftest.py) - Shared fixtures with mocks

## Development Workflow

### Running Tests
```bash
pytest tests/                           # All tests
pytest tests/mispatch_finder/core/     # Core unit tests only
pytest tests/mispatch_finder/app/      # E2E tests only
```

### Environment Variables
Required:
- `GITHUB_TOKEN` - GitHub personal access token
- `MODEL_API_KEY` or `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` - LLM API key

Optional:
- `CACHE_DIR` - Cache directory (default: platform-specific)
- `RESULTS_DIR` - Results output directory
- `LOGS_DIR` - Log storage directory
- `ECOSYSTEM` - Default ecosystem filter (default: "npm")

### Code Style Guidelines
1. **Imports**: Always at file top, never inside functions
2. **Naming**: Clear action verbs for commands/functions
3. **File names**: Match command/UseCase names (e.g., `analyze.py`, not `run_analysis.py`)
4. **Dependencies**: Core → Ports ← Infra (strict dependency inversion)
5. **Business Logic**: In `core/services/`, not in UseCases or Infra

## External Dependencies

- **cve_collector**: Vulnerability data source (GitHub Security Advisories + OSV)
- **repo_read_mcp**: MCP server for repository reading
- **dependency-injector**: DI container framework
- **typer**: CLI framework
- **GitPython**: Git operations
- **openai**: OpenAI SDK (used by infra/llm_adapters/openai_adapter.py)
- **anthropic**: Anthropic SDK (used by infra/llm_adapters/anthropic_adapter.py)

## Notes for Future Development

1. **Adding New Commands**:
   - Create UseCase in `core/usecases/`
   - Add facade function in `app/main.py` with `@with_container`
   - Add CLI command in `app/cli.py`
   - Export in `__init__.py`
   - Add tests in `tests/app/test_main_facade.py` and `tests/core/test_usecases.py`

2. **Adding New External Dependencies**:
   - Define Port in `core/ports.py`
   - Implement adapter in `infra/`
   - Register in `app/container.py`
   - Use Port type in core layer, never import from infra

3. **Business Logic Changes**:
   - Modify `core/services/` classes, not UseCases
   - Keep UseCases thin (orchestration only)
   - Update corresponding tests in `tests/core/test_services.py`
