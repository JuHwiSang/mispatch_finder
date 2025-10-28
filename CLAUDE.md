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

2. **`list`** - List available vulnerabilities
   ```bash
   mispatch-finder list                                    # Unanalyzed IDs only (default filter applied)
   mispatch-finder list --all                             # Include already analyzed
   mispatch-finder list --detailed                        # List with full metadata
   mispatch-finder list --limit 10                        # Limit to 10 results
   mispatch-finder list --filter "stars > 1000"          # Custom filter
   mispatch-finder list --no-filter                       # Disable filter (all vulnerabilities)
   ```
   - UseCase: `ListUseCase` ([core/usecases/list.py](src/mispatch_finder/core/usecases/list.py))
   - Facade: `list_vulnerabilities()` ([app/main.py](src/mispatch_finder/app/main.py))
   - **Default behavior**: Shows only unanalyzed vulnerabilities (use `--all` to include analyzed)
   - **Default filter**: `stars >= 100 and size <= 10MB` (configurable via `MISPATCH_FILTER_EXPR`)

3. **`clear`** - Clear all caches
   ```bash
   mispatch-finder clear
   ```
   - UseCase: `ClearCacheUseCase` ([core/usecases/clear_cache.py](src/mispatch_finder/core/usecases/clear_cache.py))
   - Facade: `clear()` ([app/main.py](src/mispatch_finder/app/main.py))

4. **`logs [GHSA-ID]`** - Show analysis logs
   ```bash
   mispatch-finder logs                    # Summary of all runs
   mispatch-finder logs GHSA-xxxx-xxxx-xxxx --verbose  # Detailed logs for specific GHSA
   ```
   - UseCase: `LogsUseCase` ([core/usecases/logs.py](src/mispatch_finder/core/usecases/logs.py))
   - Facade: `logs()` ([app/main.py](src/mispatch_finder/app/main.py))

5. **`batch`** - Run batch analysis
   ```bash
   mispatch-finder batch --limit 10 --provider openai --model gpt-4
   mispatch-finder batch --filter "severity == 'CRITICAL'" --limit 5
   mispatch-finder batch --no-filter --limit 100
   ```
   - **Exception**: No UseCase or Facade - implemented directly in `cli.py` only
   - **Rationale**: `batch` is a CLI orchestration helper that spawns subprocess calls to `analyze`
     - Each analysis runs in isolated process (clean memory, independent failure)
     - Uses `subprocess.run()` to invoke `mispatch-finder analyze <GHSA>` repeatedly
     - Only handles CLI concerns: progress display, filtering pending tasks, limiting runs
     - No business logic - just loops through vulnerabilities and delegates to existing `analyze` command
   - **Future consideration**: If batch logic becomes complex (e.g., parallel execution, retry strategies, distributed jobs), consider extracting to `BatchUseCase` in core layer. For now, simple subprocess loop in CLI is most efficient.

## Core Domain Models

### Vulnerability
```python
@dataclass(frozen=True)
class Vulnerability:
    ghsa_id: str
    repository: Repository
    commit_hash: str
    cve_id: str | None = None
    summary: str | None = None
    severity: str | None = None  # "CRITICAL", "HIGH", "MEDIUM", "LOW"
```

### Repository
```python
@dataclass(frozen=True)
class Repository:
    owner: str
    name: str
    ecosystem: str | None = None  # "npm", "pypi", "go"
    star_count: int | None = None
    size_kb: int | None = None
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
   - ~~`list_ghsa_ids()`~~ → `list_vulnerabilities()`
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

### Phase 8: Type Hints Modernization (2025-10)
11. **Migrated to Python 3.13+ Type Hint Syntax**
    - **Legacy typing removed**: Replaced all `from typing import List, Dict, Tuple, Optional, Union`
    - **Modern syntax adopted**:
      - `List[T]` → `list[T]`
      - `Dict[K, V]` → `dict[K, V]`
      - `Tuple[T1, T2]` → `tuple[T1, T2]`
      - `Optional[T]` → `T | None`
      - `Union[A, B]` → `A | B`
    - **Exception**: `typing.Literal`, `typing.Protocol`, `typing.TYPE_CHECKING` retained (not deprecated)
    - **Import organization**: Fixed all mid-function imports, moved to file top
      - `cli.py`: Moved `Vulnerability` import from line 110, 180 → top
      - `main.py`: Moved `ListUseCase` import from line 116 → top
      - `to_jsonable.py`: Moved `asdict` import from line 32 → top
    - **Files updated**: 20 files across all layers
      - Core: `models.py`, `usecases/*.py`, `services/*.py`
      - Infra: `vulnerability_data.py`, `repository.py`, `result_store.py`, `log_store.py`, `mcp_server.py`, `llm_adapters/*.py`, `mcp/tunnel.py`
      - App: `config.py`, `main.py`, `cli.py`
      - Shared: `log_summary.py`, `to_jsonable.py`
    - **Rationale**:
      - Align with Python 3.13+ best practices
      - Cleaner, more readable type hints
      - Remove unnecessary `typing` module imports
      - Improve code maintainability and consistency

### Phase 9: CLI Logging Simplification (2025-10)
12. **Removed infra dependency from CLI layer**
    - **Problem**: `cli.py` was importing `infra.logging` (build_json_console_handler, build_json_file_handler)
    - **Solution**: CLI now uses simpler logging approach:
      - User-facing messages → `typer.echo()` (stdout) and `typer.echo(err=True)` (stderr)
      - Debugging/internal logs → Standard library `logging.basicConfig()`
      - Structured JSON logging (`AnalysisLogger`) remains in `infra/logging/` for core/business logic only
    - **Changes**:
      - Removed `from ..infra.logging import ...` in `cli.py`
      - Replaced structured log setup with simple `logging.basicConfig()`
      - Added user-friendly status messages: "Starting analysis: {ghsa}", "Log file: {path}", etc.
      - Error messages use `typer.echo(err=True)` + `raise typer.Exit(code=2)`
    - **Benefits**:
      - Clean layer separation: CLI → app layer only, no infra dependencies
      - Simpler CLI code focused on user interaction
      - Structured logging stays where it belongs (infra, used by core services)
    - **Rationale**:
      - CLI is user-facing interface - needs simple, readable output
      - Structured JSON logs are for analysis workflow (core/infra concern)
      - Following typer framework conventions (native echo methods)

### Phase 10: Configuration System Overhaul (2025-10)
13. **Migrated to Pydantic BaseSettings for Type-Safe Configuration**
    - **Problem**: Spaghetti config logic with `_get_default_config()`, env reads scattered everywhere, test isolation failures
    - **Solution**: Pydantic BaseSettings with hierarchical structure
      - `AppConfig` (root) → `DirectoryConfig`, `VulnerabilityConfig`, `LLMConfig`, `GitHubConfig`, `AnalysisConfig`
      - All settings load from environment variables with `MISPATCH_FINDER_` prefix
      - Nested config via double underscore: `MISPATCH_FINDER_LLM__API_KEY`, `MISPATCH_FINDER_GITHUB__TOKEN`
      - Computed fields using `@computed_field` and `@property` for derived paths
    - **Changes**:
      - **config.py**: Complete rewrite with Pydantic models
        - `DirectoryConfig`: `home`, computed `cache_dir`, `results_dir`, `logs_dir`
        - `LLMConfig`: `api_key`, `provider_name`, `model_name`
        - `GitHubConfig`: `token`
        - `VulnerabilityConfig`: `ecosystem`, `filter_expr`
        - `AnalysisConfig`: `diff_max_chars`
      - **container.py**: `providers.Configuration(pydantic_settings=[AppConfig])`
      - **main.py**: Removed `with_container` decorator and global singleton
        - ❌ `_container` global variable
        - ❌ `get_container()` with singleton pattern
        - ✅ `_create_container(config)` - creates fresh container each time
        - All facade functions accept optional `config: AppConfig | None` parameter
      - **cli.py**: Updated to new env var names
        - ❌ `GITHUB_TOKEN`, `MODEL_API_KEY`
        - ✅ `MISPATCH_FINDER_GITHUB__TOKEN`, `MISPATCH_FINDER_LLM__API_KEY`
      - **Tests**: Explicit `AppConfig` instantiation for test isolation
        - `test_config` fixture creates `AppConfig` with test-specific values
        - All fixtures patch `_create_container` instead of using global state
    - **Environment Variables**:
      ```bash
      # Required
      export MISPATCH_FINDER_GITHUB__TOKEN=ghp_xxx
      export MISPATCH_FINDER_LLM__API_KEY=sk-xxx

      # Optional (with defaults)
      export MISPATCH_FINDER_LLM__PROVIDER_NAME=openai
      export MISPATCH_FINDER_LLM__MODEL_NAME=gpt-4
      export MISPATCH_FINDER_VULNERABILITY__ECOSYSTEM=npm
      export MISPATCH_FINDER_DIRECTORIES__HOME=/custom/path
      export MISPATCH_FINDER_ANALYSIS__DIFF_MAX_CHARS=200000
      ```
    - **Benefits**:
      - ✅ **Test isolation**: No more global state, each test gets fresh container
      - ✅ **Type safety**: Pydantic validates at runtime, IDE autocomplete works
      - ✅ **No spaghetti**: Single source of truth for configuration
      - ✅ **Immutable**: `frozen=True` prevents accidental modification
      - ✅ **Clear flow**: Env vars → `AppConfig` → `Container` → Services
    - **Migration impact**: Updated 20+ files across all layers
    - **Dependencies added**: `pydantic>=2.0.0`, `pydantic-settings>=2.0.0`

## Key Files & Locations

### Application Layer
- **CLI**: [app/cli.py](src/mispatch_finder/app/cli.py) - Typer-based CLI commands
- **Container**: [app/container.py](src/mispatch_finder/app/container.py) - DI container with Pydantic support
- **Config**: [app/config.py](src/mispatch_finder/app/config.py) - Pydantic BaseSettings configuration models
- **Main**: [app/main.py](src/mispatch_finder/app/main.py) - Facade functions (`analyze`, `list_vulnerabilities`, `clear`, `logs`)

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
- `MISPATCH_HOME` - Base directory for all data (default: platform-specific cache dir)
- `MISPATCH_ECOSYSTEM` - Default ecosystem filter (default: "npm")
- `MISPATCH_FILTER_EXPR` - Default vulnerability filter expression (default: "stars is not None and stars>=100 and size_bytes is not None and size_bytes<=10_000_000")
- `MISPATCH_DIFF_MAX_CHARS` - Max diff characters in prompt (default: 200,000)

### Code Style Guidelines

#### Python Version & Type Hints
- **Target**: Python 3.13+ syntax
- **Type hints**: Use modern built-in types, no legacy `typing` imports needed:
  - ✅ `list[str]`, `dict[str, int]`, `tuple[int, str]`
  - ❌ `List[str]`, `Dict[str, int]`, `Tuple[int, str]` (deprecated)
  - ✅ `str | None` (union types with `|`)
  - ❌ `Union[str, None]`, `Optional[str]` (use only when needed for compatibility)
- **Exception**: Use `typing.Optional`, `typing.Union` only in Protocol definitions or when overload is needed

#### Import Organization
1. **Location**: Always at file top, never inside functions (no lazy imports unless absolutely necessary)
2. **Order**: Follow standard Python convention:
   - Standard library (`from __future__ import annotations`, `import os`, etc.)
   - Third-party packages (`import typer`, `from dependency_injector import ...`)
   - Local imports (`from ..core.ports import ...`, `from .config import ...`)
3. **Format**: One import per line for readability

#### Naming Conventions
1. **Commands/Functions**: Clear action verbs (e.g., `analyze`, `list`, `clear`)
2. **Files**: Match command/UseCase names (e.g., `analyze.py`, not `run_analysis.py`)
3. **Variables**: Descriptive names
   - `vuln_data` (not `vuln_repo` - clarity over brevity)
   - `detailed` (boolean flag for full vs. simple output)
4. **Ports vs Adapters**:
   - Port interfaces: `*Port` suffix (e.g., `VulnerabilityDataPort`)
   - Adapter implementations: `*Adapter` or descriptive name (e.g., `VulnerabilityDataAdapter`, `AnalysisLogger`)

#### Architecture Rules
1. **Dependency Direction**: Core → Ports ← Infra (strict dependency inversion)
2. **Business Logic**: In `core/services/`, not in UseCases or Infra
3. **UseCases**: Thin orchestration only, delegate to services
4. **Ports**: Protocol definitions in `core/ports.py`, never concrete implementations

#### API Design
1. **Boolean flags**: Use explicit `detailed: bool = False` instead of multiple method names
2. **Return types**: Use `Union` return types with proper overloads when return type depends on parameter
3. **Filtering**: Pass filter expressions as strings (e.g., `filter_expr: str | None`) rather than complex objects

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
