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
│   ├── logging/           # Structured Logging & Log Parsing
│   └── mcp/              # Model Context Protocol Servers
└── shared/                # Shared Utilities (non-infra)
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
- `AnalysisStorePort` → `AnalysisStore` (read JSONL logs)
- `CachePort`, `TokenGeneratorPort`

## CLI Commands

Command format: `mispatch-finder <command> [options]`

### Available Commands

1. **`analyze <GHSA-ID>`** - Analyze a single vulnerability
   ```bash
   mispatch-finder analyze GHSA-xxxx-xxxx-xxxx --provider openai --model gpt-4
   ```
   - UseCase: `AnalyzeUseCase` ([core/usecases/analyze.py](src/mispatch_finder/core/usecases/analyze.py))
   - CLI Command: `analyze()` ([app/cli.py:96](src/mispatch_finder/app/cli.py#L96))

2. **`list`** - List available vulnerabilities
   ```bash
   mispatch-finder list                                    # Unanalyzed IDs only (default filter applied)
   mispatch-finder list --include-analyzed                # Include already analyzed (-i)
   mispatch-finder list --detail                          # List with full metadata (-d)
   mispatch-finder list --limit 10                        # Limit to 10 results (-n)
   mispatch-finder list --filter "stars > 1000"          # Custom filter (-f)
   mispatch-finder list --no-filter                       # Disable filter (all vulnerabilities)
   ```
   - UseCase: `ListUseCase` ([core/usecases/list.py](src/mispatch_finder/core/usecases/list.py))
   - CLI Command: `list_command()` ([app/cli.py:87](src/mispatch_finder/app/cli.py#L87))
   - **Default behavior**: Shows only unanalyzed vulnerabilities (use `--include-analyzed` to include analyzed)
   - **Default filter**: `stars >= 100 and size <= 10MB` (configurable via `MISPATCH_FILTER_EXPR`)

3. **`clear`** - Clear all caches
   ```bash
   mispatch-finder clear
   ```
   - UseCase: `ClearCacheUseCase` ([core/usecases/clear_cache.py](src/mispatch_finder/core/usecases/clear_cache.py))
   - CLI Command: `clear_command()` ([app/cli.py:235](src/mispatch_finder/app/cli.py#L235))

4. **`logs [GHSA-ID]`** - Show analysis logs
   ```bash
   mispatch-finder logs                    # Summary of all runs
   mispatch-finder logs GHSA-xxxx-xxxx-xxxx --verbose  # Detailed logs for specific GHSA
   ```
   - UseCase: `LogsUseCase` ([core/usecases/logs.py](src/mispatch_finder/core/usecases/logs.py))
   - CLI Command: `logs()` ([app/cli.py:250](src/mispatch_finder/app/cli.py#L250))

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

### Phase 11: CLI and Main Module Consolidation (2025-10)
14. **Merged main.py into cli.py**
    - **Problem**: Unnecessary separation between facade functions (`main.py`) and CLI commands (`cli.py`)
    - **Solution**: Consolidated all application layer code into single `cli.py` module
      - Deleted `app/main.py` entirely
      - CLI commands directly contain business logic (container creation + use case execution)
      - Tests use same pattern: create Container → execute UseCase (test actual implementation)
    - **Changes**:
      - **cli.py**: CLI commands create container and execute use cases inline
        - `analyze()`: Creates Container, executes AnalyzeUseCase (lines 28-80)
        - `list_command()`: Creates Container, executes ListUseCase (lines 83-155)
        - `clear_command()`: Creates Container, executes ClearCacheUseCase (lines 158-170)
        - `logs()`: Creates Container, executes LogsUseCase (lines 173-185)
        - `batch()`: Creates Container, executes ListUseCase to fetch candidates (lines 188+)
      - **Tests**: All tests consolidated in E2E file
        - `test_main_e2e.py`: E2E tests create Container and execute UseCase (mimics CLI implementation)
        - `conftest.py`: Provides mock implementations for testing
        - Tests validate actual implementation behavior
        - Deleted `test_main_facade.py` (no longer needed - no facades to test)
      - **__init__.py**: Cleared all exports (public API will be in future `app/api.py`)
    - **Benefits**:
      - ✅ **Simpler structure**: No facade layer, no test helpers - just direct implementation
      - ✅ **Direct flow**: CLI command → Container → UseCase (one pattern everywhere)
      - ✅ **Less code**: Removed ~150 lines of facade + test helper boilerplate
      - ✅ **Better tests**: Tests validate real implementation, not test-specific wrappers
    - **Architecture**:
      - `cli.py` structure: CLI Commands only (self-contained, no helpers)
      - CLI commands handle: argument parsing, container creation, use case execution, output formatting
      - Tests replicate same pattern to test actual behavior
    - **Rationale**: No need for facades (used once) or test helpers (tests should test real code)

### Phase 12: Type System Cleanup (2025-10)
15. **Removed unnecessary cast() usage**
    - **Problem**: Excessive `cast()` usage in CLI due to Union return types from `ListUseCase.execute()`
    - **Analysis**: Python's type system cannot infer return type based on runtime parameter values
      - `execute()` returns `list[str] | list[Vulnerability]` depending on `detailed` parameter
      - Type checkers cannot track parameter value from constructor through to method return
      - Attempted solutions: `@overload` with `Literal` types → Still insufficient for type inference
    - **Solution**: Pragmatic approach with minimal type annotations
      - **CLI**: Use explicit type annotations with `# type: ignore[assignment]` at call sites
        ```python
        ghsa_ids: list[str] = uc.execute(..., detailed=False)  # type: ignore[assignment]
        vulns: list[Vulnerability] = uc.execute(..., detailed=True)  # type: ignore[assignment]
        ```
      - **Tests (Fake)**: Added `@overload` to `FakeVulnRepo.list_vulnerabilities()` matching Port signatures
      - **Tests (UseCase)**: Used `cast()` only where type narrowing is needed for assertions
    - **Changes**:
      - **cli.py**: Removed `from typing import cast`, added type annotations at execute() calls
      - **list.py**: Simplified to single Union return type with clear docstring
      - **test_usecases.py**: Added `@overload` to FakeVulnRepo, used `cast()` for detailed tests
      - **test_main_e2e.py**: Updated to new UseCase signature
    - **Benefits**:
      - ✅ **Cleaner code**: No cast() in production CLI code
      - ✅ **Explicit intent**: Type annotations show what we expect at each call site
      - ✅ **Pragmatic**: Accepts type system limitations, uses `type: ignore` only where needed
    - **Rationale**: Type perfection not worth complexity; runtime correctness + clear intent > perfect static types

### Phase 13: UseCase Parameter Refactoring (2025-10)
16. **Separated DI dependencies from runtime parameters**
    - **Problem**: `ListUseCase` mixed DI dependencies with runtime parameters in `__init__()`
      - All parameters (vuln_data, limit, ecosystem, detailed, filter_expr) in constructor
      - Required creating new UseCase instance for each different parameter set
      - Violated Single Responsibility: constructor doing dependency injection AND configuration
    - **Analysis**: Reviewed all UseCases for parameter placement
      - ✅ `AnalyzeUseCase`: Already correct (DI in `__init__`, runtime in `execute`)
      - ❌ `ListUseCase`: All parameters in `__init__`, empty `execute()`
      - ✅ `ClearCacheUseCase`: Already correct
      - ✅ `LogsUseCase`: Already correct
    - **Solution**: Moved runtime parameters from `__init__` to `execute()`
      - **Before**:
        ```python
        def __init__(self, *, vuln_data, limit, ecosystem, detailed, filter_expr): ...
        def execute(self) -> list[str] | list[Vulnerability]: ...
        ```
      - **After**:
        ```python
        def __init__(self, *, vuln_data): ...  # DI only
        def execute(self, *, limit, ecosystem, detailed, filter_expr) -> ...: ...  # Runtime params
        ```
    - **Changes**:
      - **core/usecases/list.py**:
        - Moved limit, ecosystem, detailed, filter_expr to `execute()` signature
        - Added comprehensive docstring with parameter descriptions
      - **app/cli.py**:
        - `list_command()`: Create UseCase once, call execute() with parameters
        - `batch()`: Same pattern update
      - **Tests**: Updated all test cases to new signature
        - `test_usecases.py`: 4 tests updated
        - `test_main_e2e.py`: 1 test updated
    - **Benefits**:
      - ✅ **Reusability**: Single UseCase instance can be called multiple times with different params
      - ✅ **Clear separation**: DI concerns vs. business parameters
      - ✅ **Testability**: Easier to test different parameter combinations
      - ✅ **Consistency**: All UseCases now follow same pattern
    - **Design Principle**:
      - `__init__` = Dependencies (Ports, Services) injected via DI
      - `execute()` = Business parameters that change per invocation
    - **Impact**: Updated 5 files (1 UseCase, 1 CLI, 3 test files)

## Key Files & Locations

### Application Layer
- **CLI**: [app/cli.py](src/mispatch_finder/app/cli.py) - Typer-based CLI commands (self-contained)
  - CLI commands: `analyze()`, `list_command()`, `clear_command()`, `logs()`, `batch()`
  - Each command creates Container and executes UseCase inline
- **Container**: [app/container.py](src/mispatch_finder/app/container.py) - DI container with Pydantic support
- **Config**: [app/config.py](src/mispatch_finder/app/config.py) - Pydantic BaseSettings configuration models

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
- **Logging**: [infra/logging/](src/mispatch_finder/infra/logging/) - Structured logging & log parsing
  - [logger.py](src/mispatch_finder/infra/logging/logger.py) - AnalysisLogger (GHSA-specific JSONL + console)
  - [formatters.py](src/mispatch_finder/infra/logging/formatters.py) - JSONFormatter, HumanReadableFormatter
  - [handlers.py](src/mispatch_finder/infra/logging/handlers.py) - build_json_file_handler, build_human_console_handler
  - [log_summary.py](src/mispatch_finder/infra/logging/log_summary.py) - Log parsing & summarization
- **Analysis Store**: [infra/analysis_store.py](src/mispatch_finder/infra/analysis_store.py) - Read JSONL logs (read-only)

## Testing Strategy

- **Unit Tests** (`tests/mispatch_finder/core/`): Fast tests with fake implementations
- **Integration Tests** (`tests/mispatch_finder/infra/`): Tests with real dependencies
- **E2E Tests** (`tests/mispatch_finder/app/`): Full workflow with mocked external services

### Key Test Files
- [tests/core/test_services.py](tests/mispatch_finder/core/test_services.py) - Service layer tests
- [tests/core/test_usecases.py](tests/mispatch_finder/core/test_usecases.py) - UseCase tests with fakes (includes `FakeAnalysisStore`, `FakeLogger`)
- [tests/core/test_usecases_logs.py](tests/mispatch_finder/core/test_usecases_logs.py) - Logs UseCase scenarios
- [tests/infra/logging/test_log_summary.py](tests/mispatch_finder/infra/logging/test_log_summary.py) - Log parsing tests
- [tests/infra/test_analysis_store.py](tests/mispatch_finder/infra/test_analysis_store.py) - AnalysisStore read operations
- [tests/shared/test_json_logging.py](tests/mispatch_finder/shared/test_json_logging.py) - Handler and formatter tests
- [tests/app/cli/](tests/mispatch_finder/app/cli/) - CLI command tests by command
- [tests/app/conftest.py](tests/mispatch_finder/app/conftest.py) - Shared fixtures with mocks
- [tests/app/test_config.py](tests/mispatch_finder/app/test_config.py) - Configuration tests (including runtime mutation)

## Development Workflow

### Running Tests
```bash
pytest tests/                           # All tests
pytest tests/mispatch_finder/core/     # Core unit tests only
pytest tests/mispatch_finder/app/      # E2E tests only
```

### Environment Variables
Required:
- `MISPATCH_FINDER_GITHUB__TOKEN` - GitHub personal access token
- `MISPATCH_FINDER_LLM__API_KEY` - LLM API key (OpenAI or Anthropic)

Optional (with defaults):
- `MISPATCH_FINDER_LLM__PROVIDER_NAME` - LLM provider (default: "openai")
- `MISPATCH_FINDER_LLM__MODEL_NAME` - Model name (default: "gpt-5")
- `MISPATCH_FINDER_VULNERABILITY__ECOSYSTEM` - Default ecosystem filter (default: "npm")
- `MISPATCH_FINDER_VULNERABILITY__FILTER_EXPR` - Default vulnerability filter expression (default: "stars is not None and stars>=100 and size_bytes is not None and size_bytes<=10_000_000")
- `MISPATCH_FINDER_DIRECTORIES__HOME` - Base directory for all data (default: platform-specific cache dir)
- `MISPATCH_FINDER_ANALYSIS__DIFF_MAX_CHARS` - Max diff characters in prompt (default: 200,000)
- `MISPATCH_FINDER_LOGGING__CONSOLE_OUTPUT` - Enable console output (default: False, CLI sets to True)
- `MISPATCH_FINDER_LOGGING__LEVEL` - Logging level (default: "INFO")

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
- **pydantic**: Configuration management with BaseSettings
- **pydantic-settings**: Environment variable configuration
- **python-json-logger**: JSON log formatting (pythonjsonlogger)

## Notes for Future Development

1. **Adding New Commands**:
   - Create UseCase in `core/usecases/`
   - Add CLI command function in `app/cli.py` (create Container, execute UseCase inline)
   - Add E2E test in `tests/app/test_main_e2e.py` (replicate CLI pattern: create Container, execute UseCase)
   - Add unit tests in `tests/core/test_usecases.py`

2. **Adding New External Dependencies**:
   - Define Port in `core/ports.py`
   - Implement adapter in `infra/`
   - Register in `app/container.py`
   - Use Port type in core layer, never import from infra

3. **Business Logic Changes**:
   - Modify `core/services/` classes, not UseCases
   - Keep UseCases thin (orchestration only)
   - Update corresponding tests in `tests/core/test_services.py`

## Recent Changes (2025-11-01)

### Phase 17: cve_collector Breaking Changes (2025-11-01)
**Status**: ✅ Completed

**Changes**:
- Updated to `cve_collector` v2.0+ with `CveCollectorClient` class-based API
- **VulnerabilityDataAdapter** ([infra/vulnerability_data.py](src/mispatch_finder/infra/vulnerability_data.py)):
  - Now uses `CveCollectorClient` instead of module-level functions
  - `__init__` accepts `cache_dir`, `github_cache_ttl_days`, `osv_cache_ttl_days`
  - Removed `_ensure_token()` (client handles auth internally)
  - All methods (`fetch_metadata`, `list_vulnerabilities`, `clear_cache`) now call client methods
- **Container** ([app/container.py](src/mispatch_finder/app/container.py)):
  - Added `cache_dir` injection to `vuln_data` provider
- **Tests** ([tests/infra/test_vulnerability_data.py](tests/mispatch_finder/infra/test_vulnerability_data.py)):
  - Removed `test_vulnerability_repository_sets_env_token` (no longer applicable)
  - Updated assertions to match new API

**Impact**:
- ✅ No environment variable pollution (`GITHUB_TOKEN` no longer set in `os.environ`)
- ✅ Cache directory configuration centralized
- ✅ Client-managed state (cleaner interface)

### Phase 18: clear Command Disabled (2025-11-01)
**Status**: ⏸️ Temporarily Disabled - TODO for future

**Problem**:
1. **Resource conflict**: `cve_collector` client holds lock on `cache_dir`, preventing clear operation
2. **Unclear semantics**: Need to define what should be cleared:
   - Vulnerability data cache (`cve_collector` cache)
   - Repository clones (`cache/repos/`)
   - Analysis results (`results/`)
   - Analysis logs (`logs/`)

**Changes**:
- **CLI** ([app/cli.py](src/mispatch_finder/app/cli.py)): `clear_command()` commented out with TODO
- **Tests**: All `clear`-related tests marked with `@pytest.mark.skip`:
  - `test_cli_clear_executes()` in test_cli.py
  - `test_cli_clear_executes()` in test_cli_commands.py
  - `test_clear_cache()` in test_main_e2e.py
  - `test_clear_cache_usecase()` in test_usecases.py
  - `test_clear_cache_usecase_with_prefix()` in test_usecases.py

**TODO (Future Work)**:
1. Define clear command semantics:
   - Add subcommands: `mispatch-finder clear cache`, `mispatch-finder clear repos`, `mispatch-finder clear results`, etc.
   - Or add flags: `--cache`, `--repos`, `--results`, `--logs`, `--all`
2. Fix resource conflicts:
   - Separate cache directories for vuln_data and repos
   - Or implement proper lifecycle management (close client before clearing)
3. Re-enable command and tests once semantics are defined and conflicts resolved

### Phase 19: Iterator-Based Vulnerability Listing (2025-11-01)
**Status**: ✅ Completed

**Problem**:
- `ListUseCase` used inefficient progressive fetching with exponential backoff (1x, 2x, 4x, up to 10x limit)
- When many vulnerabilities were already analyzed, fetched unnecessarily large batches
- `cve_collector` v0.8.0+ supports `list_vulnerabilities_iter()` for lazy iteration

**Solution**: Migrated to iterator-based approach for efficient streaming

**Changes**:
1. **VulnerabilityDataPort** ([core/ports.py:73-93](src/mispatch_finder/core/ports.py#L73-L93)):
   - Added `list_vulnerabilities_iter()` method
   - Returns `Iterator[str] | Iterator[Vulnerability]` based on `detailed` parameter

2. **VulnerabilityDataAdapter** ([infra/vulnerability_data.py:170-204](src/mispatch_finder/infra/vulnerability_data.py#L170-L204)):
   - Implemented `list_vulnerabilities_iter()` using `cve_collector` client's iterator
   - Lazy iteration with GHSA ID validation and deduplication
   - Converts to domain models on-the-fly

3. **ListUseCase** ([core/usecases/list.py:47-83](src/mispatch_finder/core/usecases/list.py#L47-L83)):
   - Removed complex progressive fetching logic (97 lines → 83 lines)
   - Simple iterator consumption: fetch until `limit` reached
   - Skip analyzed items immediately during iteration (no batch processing)

4. **Tests**:
   - Added `list_vulnerabilities_iter()` to `FakeVulnRepo` with `listed_iter` tracking
   - Added `list_vulnerabilities_iter()` to `MockVulnerabilityRepository`
   - Updated all test assertions: `vuln_data.listed` → `vuln_data.listed_iter`

**Benefits**:
- ✅ **Memory efficient**: No large batch loading, stream items one by one
- ✅ **Performance**: Stop fetching immediately when limit reached
- ✅ **Code simplicity**: Removed 14 lines of complex multiplier logic
- ✅ **Scalability**: Works efficiently even with 90%+ analyzed vulnerabilities

**Type System Notes**:
- Current implementation uses `cast()` in `ListUseCase` due to Union return type limitations
- Python's type system cannot infer return type from runtime `detailed` parameter value
- When `cve_collector` improves typing (e.g., with Literal types), casts can be removed
- Iterator's Union type (`Iterator[str] | Iterator[Vulnerability]`) is a known Python typing limitation

### Phase 20: CLI Human-Readable Output (2025-11-01)
**Status**: ✅ Completed

**Problem**:
- CLI commands output raw JSON, difficult for users to read
- Need user-friendly output by default, with optional JSON for scripting

**Solution**: Implemented formatter module with `--json` flag

**Changes**:
1. **CLI Formatter** ([app/cli_formatter.py](src/mispatch_finder/app/cli_formatter.py)):
   - `format_analyze_result()`: Formats analysis results with color-coded status
   - `format_vulnerability_list()`: Formats vulnerability lists with metadata

2. **CLI Commands** ([app/cli.py](src/mispatch_finder/app/cli.py)):
   - Added `--json` flag to `analyze` and `list` commands
   - Default: Human-readable output (uses formatter)
   - `--json` flag: Raw JSON output (for scripting)

3. **Tests** ([tests/app/test_cli_formatter.py](tests/mispatch_finder/app/test_cli_formatter.py)):
   - Unit tests for both formatter functions

**Benefits**:
- ✅ **User-friendly**: Default output is readable and informative
- ✅ **Scriptable**: JSON output available via `--json` flag
- ✅ **Consistent**: Same formatting pattern across all commands

### Phase 21: CLI Option Naming Improvements (2025-11-01)
**Status**: ✅ Completed

**Problem**:
- CLI parameter names were non-intuitive:
  - `detailed` (verbose, not conventional)
  - `all_items` (unclear what "all" means)

**Solution**: Renamed for clarity and convention

**Changes**:
1. **CLI Parameters** ([app/cli.py:88-92](src/mispatch_finder/app/cli.py#L88-L92)):
   - `detailed` → `detail` (shorter, conventional)
     - Option: `--detailed` → `--detail`
     - Short flag: `-d` (unchanged)
   - `all_items` → `include_analyzed` (descriptive)
     - Option: `--all` → `--include-analyzed`
     - Short flag: `-a` → `-i` (for "include")

2. **Documentation** ([CLAUDE.md:62-74](CLAUDE.md#L62-L74)):
   - Updated all command examples
   - Updated help text references

**Benefits**:
- ✅ **More intuitive**: `--include-analyzed` clearly states what it does
- ✅ **Conventional**: `--detail` matches common CLI patterns
- ✅ **No breaking changes**: Tests unchanged (use underlying functions, not CLI options)

### Phase 22: Test Environment Variable Migration (2025-11-01)
**Status**: ✅ Completed

**Problem**:
- Test files still checked for old `GITHUB_TOKEN` environment variable
- New config system uses `MISPATCH_FINDER_GITHUB__TOKEN`
- Tests were being skipped unnecessarily

**Solution**: Updated all test skipif conditions

**Changes**:
1. **Test Files** - Updated `@pytest.mark.skipif` decorators:
   - [test_cli_commands.py](tests/mispatch_finder/app/cli/test_cli_commands.py): 6 tests
   - [test_cli.py](tests/mispatch_finder/app/cli/test_cli.py): 3 tests
   - [test_vulnerability_data.py](tests/mispatch_finder/infra/test_vulnerability_data.py): 3 tests
   - Changed: `GITHUB_TOKEN` → `MISPATCH_FINDER_GITHUB__TOKEN`
   - Updated monkeypatch calls in tests

**Benefits**:
- ✅ **Correct skipping**: Tests run when proper env var is set
- ✅ **Consistency**: All tests use same env var naming convention

### Phase 23: CLI Test Restructuring (2025-11-01)
**Status**: ✅ Completed

**Problem**:
- Test files poorly organized: `test_cli.py`, `test_cli_commands.py`, `test_main_e2e.py`
- No clear separation by command
- `test_main_e2e.py` name outdated (main.py doesn't exist anymore)

**Solution**: Restructured into command-based organization

**Changes**:
1. **New Structure** - Created `tests/app/cli/` directory:
   ```
   tests/mispatch_finder/app/
   ├── cli/
   │   ├── __init__.py
   │   ├── test_analyze.py      # analyze command tests
   │   ├── test_list.py          # list command tests
   │   ├── test_logs.py          # logs command tests
   │   └── test_batch.py         # batch command tests (TODO)
   ├── conftest.py               # Shared fixtures
   └── test_cli_formatter.py     # Formatter tests
   ```

2. **Deleted Old Files**:
   - ❌ `test_cli.py`
   - ❌ `test_cli_commands.py`
   - ❌ `test_main_e2e.py`

3. **Test Coverage by Command**:
   - **test_analyze.py** (7 tests):
     - `--provider`, `--model`, `--log-level`, `--force-reclone`, `--json`
     - API key & GitHub token validation
     - E2E test with mocked dependencies

   - **test_list.py** (14 tests):
     - `--detail` / `-d`, `--filter` / `-f`, `--no-filter`
     - `--include-analyzed` / `-i`, `--limit` / `-n`, `--json`
     - Human-readable vs JSON output
     - GitHub token validation
     - E2E test with mocked dependencies

   - **test_logs.py** (5 tests):
     - `ghsa` argument (optional)
     - `--verbose` / `-v`
     - GHSA present vs absent behavior
     - E2E tests

   - **test_batch.py** (0 tests):
     - TODO: Deferred due to subprocess complexity
     - Detailed testing guide documented in file

**Benefits**:
- ✅ **Clear organization**: One file per command
- ✅ **Easy to find**: Test location matches command name
- ✅ **Comprehensive coverage**: All CLI options tested
- ✅ **Maintainable**: Easier to add tests for new options

### Phase 24: Log Summary Infrastructure Refactoring (2025-11-02)
**Status**: ✅ Completed

**Problem**:
- `log_summary.py` was in `shared/` directory - not appropriate for infra code
- `ListUseCase` directly imported and called `summarize_logs()` function - bypassing DI
- No clear separation between log parsing utilities and business logic

**Solution**: Moved to `infra/logging/` and applied DI pattern

**Changes**:
1. **File Structure**:
   - Moved `src/mispatch_finder/shared/log_summary.py` → `src/mispatch_finder/infra/logging/log_summary.py`
   - Moved `tests/mispatch_finder/shared/test_log_summary.py` → `tests/mispatch_finder/infra/logging/test_log_summary.py`

2. **Port Extension** ([core/ports.py:187-189](src/mispatch_finder/core/ports.py#L187-L189)):
   - Added `get_analyzed_ids() -> set[str]` to `LogStorePort`
   - Returns set of GHSA IDs that have been analyzed (done=True)

3. **Adapter Implementation** ([infra/log_store.py:33-35](src/mispatch_finder/infra/log_store.py#L33-L35)):
   - Implemented `get_analyzed_ids()` in `LogStore`
   - Uses `summarize_logs()` internally to get analysis status

4. **UseCase Refactoring** ([core/usecases/list.py:16-18, 62](src/mispatch_finder/core/usecases/list.py#L16-L18)):
   - **Before**: `__init__(vuln_data, logs_dir: Path)` + direct `summarize_logs(self._logs_dir)` call
   - **After**: `__init__(vuln_data, log_store: LogStorePort)` + `self._log_store.get_analyzed_ids()`
   - Removed direct file system access from UseCase
   - Simplified filtering logic (no dict traversal, just set membership check)

5. **Container Update** ([app/container.py:101-105](src/mispatch_finder/app/container.py#L101-L105)):
   - Changed `list_uc` to inject `log_store` instead of `logs_dir`

6. **Test Updates** ([tests/core/test_usecases.py:141-152](tests/mispatch_finder/core/test_usecases.py#L141-L152)):
   - Added `FakeLogStore` class with configurable `analyzed_ids`
   - Updated all `ListUseCase` tests to use `log_store` instead of `logs_dir`
   - Added `test_list_usecase_excludes_analyzed()` to verify filtering behavior

7. **Import Updates**:
   - `core/usecases/list.py`: Updated import path
   - `infra/log_store.py`: Changed to relative import `.logging.log_summary`
   - `tests/infra/logging/test_log_summary.py`: Updated module path

**Benefits**:
- ✅ **Clear architecture**: Log parsing utilities now in proper infra layer
- ✅ **DI consistency**: All core code uses Ports, no direct infra imports
- ✅ **Better testability**: `FakeLogStore` enables easy testing
- ✅ **Simpler code**: Set membership check vs. dict traversal + property access
- ✅ **Decoupling**: UseCase no longer knows about file system paths

**Impact**: Updated 10 files (1 port, 1 adapter, 1 usecase, 1 container, 6 test files)

### Phase 25: Logging System Overhaul (2025-11-02)
**Status**: ✅ Completed

**Problem**:
1. `ResultStore` and `LogStore` were separated despite handling the same JSONL log files
2. Custom JSON formatter instead of using standard library (`python-json-logger`)
3. No dual output (file + console) - difficult to debug during CLI execution
4. Logger didn't require GHSA parameter for file naming
5. Spaghetti config logic with runtime GHSA injection unclear

**Solution**: Complete logging infrastructure redesign with configuration-driven DI

**Changes**:

1. **Store Unification**:
   - **Deleted**: `infra/result_store.py` (didn't actually exist - was conceptual confusion)
   - **Renamed**: `LogStore` → `AnalysisStore` ([infra/analysis_store.py](src/mispatch_finder/infra/analysis_store.py))
   - **Removed**: All write operations from store (JSONL written by `AnalysisLogger` only)
   - **Port Update**: `ResultStorePort`, `LogStorePort` → `AnalysisStorePort` (read-only)
     - `read_log(ghsa, verbose) -> list[str]`
     - `summarize_all(verbose) -> list[str]`
     - `get_analyzed_ids() -> set[str]`

2. **Formatter Migration** ([infra/logging/formatters.py](src/mispatch_finder/infra/logging/formatters.py)):
   - **Removed**: Custom `JSONFormatter` implementation
   - **Added**: `JSONFormatter(JsonFormatter)` extending `pythonjsonlogger.json.JsonFormatter`
     - Auto-includes: `level`, `logger`, `message`
     - Supports `payload` via `extra={"payload": data}`
   - **Added**: `HumanReadableFormatter(logging.Formatter)`
     - Format: `%(asctime)s - %(levelname)s - %(message)s`
     - For console output only

3. **Handler Factory** ([infra/logging/handlers.py](src/mispatch_finder/infra/logging/handlers.py)):
   - **Removed**: `build_json_console_handler()` (JSON not suitable for console)
   - **Added**: `build_human_console_handler()` (human-readable for CLI)
   - **Updated**: `build_json_file_handler()` uses new `JSONFormatter`

4. **Logger Redesign** ([infra/logging/logger.py](src/mispatch_finder/infra/logging/logger.py)):
   - **Required parameter**: `ghsa: str` (for log file naming: `{ghsa}.jsonl`)
   - **Dual handlers**:
     - File handler (JSONL) - always enabled
     - Console handler (human-readable) - controlled by `console_output` flag
   - **Signature**: `__init__(*, ghsa, logs_dir, logger_name, console_output, level)`
   - **Validation**: Raises `ValueError` if `ghsa` is empty

5. **Configuration System** ([app/config.py](src/mispatch_finder/app/config.py)):
   - **Added**: `LoggingConfig(BaseSettings)`
     - `logger_name: str = "mispatch_finder"`
     - `console_output: bool = False` (CLI sets to True)
     - `level: str = "INFO"`
   - **Added**: `RuntimeConfig(BaseSettings)` (frozen=False for mutation)
     - `ghsa: str | None = None` (set by CLI before container creation)
   - **Updated**: `AppConfig.frozen = False` (to allow runtime mutation)
   - **Added**: `AppConfig.logging` and `AppConfig.runtime` fields

6. **Container Update** ([app/container.py](src/mispatch_finder/app/container.py)):
   - **Changed**: Logger from `Singleton` → `Factory`
   - **Injection**: `ghsa=config.runtime.ghsa` (set at runtime by CLI)
   - **Full signature**:
     ```python
     logger = providers.Factory(
         AnalysisLogger,
         ghsa=config.runtime.ghsa,
         logs_dir=config.directories.logs_dir,
         logger_name=config.logging.logger_name,
         console_output=config.logging.console_output,
         level=config.logging.level,
     )
     ```

7. **CLI Integration** ([app/cli.py](src/mispatch_finder/app/cli.py)):
   - **Pattern**: Set runtime config → Create container → Execute
   ```python
   config = AppConfig()
   config.runtime.ghsa = ghsa  # Set GHSA for logger
   config.logging.console_output = True  # Enable console in CLI

   container = Container()
   container.config.from_pydantic(config)
   ```

8. **UseCase Simplification** ([core/usecases/analyze.py](src/mispatch_finder/core/usecases/analyze.py)):
   - **Removed**: `store` dependency (no longer saves results)
   - **Signature**: `__init__(*, orchestrator)` only
   - **Thin wrapper**: Delegates to `orchestrator.analyze()`

9. **Test Updates**:
   - **test_json_logging.py** ([tests/shared/test_json_logging.py:5-15](tests/mispatch_finder/shared/test_json_logging.py#L5-L15)):
     - Updated import: `build_json_console_handler` → `build_human_console_handler`
     - Renamed test: `test_build_json_console_handler` → `test_build_human_console_handler`
   - **test_config.py** ([tests/app/test_config.py:110-121](tests/mispatch_finder/app/test_config.py#L110-L121)):
     - Renamed: `test_app_config_frozen` → `test_app_config_allows_runtime_mutation`
     - Tests `config.runtime.ghsa` and `config.logging.console_output` mutation
   - **test_analyze.py** ([tests/app/cli/test_analyze.py:148-149](tests/mispatch_finder/app/cli/test_analyze.py#L148-L149)):
     - Added `test_config.runtime.ghsa = "GHSA-TEST-E2E"` before container creation
   - **test_usecases.py**: `FakeLogger` already compatible (no changes needed)
   - **conftest.py**: Mock implementations don't need logger updates

10. **Export Updates** ([infra/logging/__init__.py](src/mispatch_finder/infra/logging/__init__.py:4-12)):
    - Removed: `build_json_console_handler`
    - Added: `build_human_console_handler`

**Architecture Flow**:
```
CLI Command
  ↓
Set config.runtime.ghsa + config.logging.console_output
  ↓
Create Container (config → providers)
  ↓
Logger Factory creates AnalysisLogger with GHSA-specific file
  ↓
Dual output: logs/{ghsa}.jsonl + console (if enabled)
```

**Benefits**:
- ✅ **Unified storage**: Single `AnalysisStore` for reading JSONL logs
- ✅ **Standard library**: `python-json-logger` instead of custom formatter
- ✅ **Dual output**: JSONL files (always) + human console (CLI only)
- ✅ **Configuration-driven**: No override patterns, uses `RuntimeConfig`
- ✅ **GHSA-specific logs**: Each analysis writes to `logs/{ghsa}.jsonl`
- ✅ **Type-safe config**: Pydantic validates all settings
- ✅ **Clean DI**: Logger is Factory, created fresh per analysis
- ✅ **Better debugging**: Console output during CLI execution

**Dependencies Added**:
- `python-json-logger>=2.0.0` (for `pythonjsonlogger.json.JsonFormatter`)

**Files Modified**: 15 files
- Config: `config.py`, `container.py`, `cli.py`
- Infra: `formatters.py`, `handlers.py`, `logger.py`, `analysis_store.py`, `__init__.py`
- Core: `analyze.py`, `ports.py`
- Tests: `test_json_logging.py`, `test_config.py`, `test_analyze.py`, `test_usecases.py`, `test_analysis_store.py`

**Files Deleted**: 2 files
- `infra/log_store.py` (replaced by `analysis_store.py`)
- `tests/infra/test_log_store.py` (replaced by `test_analysis_store.py`)

**Impact**: Complete overhaul of logging infrastructure with cleaner architecture and better developer experience

### Phase 26: AnalysisResult Return Type Refactoring (2025-11-02)
**Status**: ✅ Completed

**Problem**:
1. `AnalysisOrchestrator.analyze()` returned untyped `dict` instead of `AnalysisResult`
2. `AnalysisResult` fields were always `None` - extracted JSON stored in `raw_text` only
3. CLI formatter expected wrong dict structure (legacy `assessment`, `token_usage` keys)
4. Log summary parsing only used `raw_text` - ignored structured fields even when available

**Solution**: Complete refactoring to use Pydantic models throughout

**Changes**:

1. **AnalysisOrchestrator** ([core/services/analysis_orchestrator.py:47-209](src/mispatch_finder/core/services/analysis_orchestrator.py#L47-L209)):
   - **Return type**: `dict[str, object]` → `AnalysisResult`
   - **JSON parsing logic** (lines 134-178): Parse extracted JSON and populate fields
     - Map `current_risk` → `verdict`
     - Map `patch_risk` → `severity`
     - Map `reason` → `rationale` (fallback to legacy `rationale`)
     - Map `poc` → `poc_idea` (fallback to legacy `poc_idea`)
     - Handle `evidence` as list or dict
     - Graceful fallback on JSON parse errors
   - **Logging**: Convert AnalysisResult to dict for JSONL serialization (lines 194-207)
   - **Removed**: `asdict()` import and final conversion

2. **AnalyzeUseCase** ([core/usecases/analyze.py:20-31](src/mispatch_finder/core/usecases/analyze.py#L20-L31)):
   - Updated return type: `dict[str, object]` → `AnalysisResult`
   - Added `AnalysisResult` import

3. **CLI analyze command** ([app/cli.py:84-100](src/mispatch_finder/app/cli.py#L84-L100)):
   - **JSON output**: Manual dict conversion for serialization
   - **Human output**: Pass `AnalysisResult` directly to formatter

4. **CLI Formatter** ([app/cli_formatter.py:8-66](src/mispatch_finder/app/cli_formatter.py#L8-L66)):
   - **Parameter type**: `dict` → `AnalysisResult`
   - **Display fields**:
     - GHSA ID, Provider, Model (lines 23-32)
     - Verdict → "Current Risk" (line 41)
     - Severity → "Patch Risk" (line 45)
     - Rationale, Evidence, PoC (lines 48-62)
   - **Removed**: Legacy dict structure handling

5. **Log Summary Parsing** ([infra/logging/log_summary.py:80-137, 175-227](src/mispatch_finder/infra/logging/log_summary.py#L80-L137)):
   - **Priority hierarchy**:
     1. Structured fields from AnalysisResult (`verdict`, `severity`, `rationale`, `poc_idea`)
     2. Fallback to `raw_text` JSON parsing (new format: `current_risk`, `patch_risk`, `reason`, `poc`)
     3. Legacy fallbacks (old format: `severity`, `rationale`, `poc_idea`)
   - Applied to both `parse_log_details()` and `parse_log_file()`

6. **Tests Updated**:
   - [test_services.py:203-208](tests/mispatch_finder/core/test_services.py#L203-L208): Check `result.ghsa`, `result.verdict`, `result.rationale`
   - [test_usecases.py:219-221](tests/mispatch_finder/core/test_usecases.py#L219-L221): Assert AnalysisResult fields
   - [test_cli_formatter.py:7-52](tests/mispatch_finder/app/test_cli_formatter.py#L7-L52): Use `AnalysisResult` instances
   - [test_analyze.py:181-193](tests/mispatch_finder/app/cli/test_analyze.py#L181-L193): Verify structured fields in E2E test

**Benefits**:
- ✅ **Type safety**: Pydantic models instead of untyped dicts
- ✅ **Proper parsing**: Extracted JSON populates structured fields immediately
- ✅ **Clean display**: Formatter uses proper field names (Current Risk, Patch Risk)
- ✅ **Smart fallbacks**: Log parsing prefers structured fields, falls back to raw_text only when needed
- ✅ **Better debugging**: All fields properly populated and visible

**Field Mapping**:
```
LLM JSON Response → AnalysisResult → Display/Logs
-------------------------------------------------
current_risk      → verdict         → Current Risk
patch_risk        → severity        → Patch Risk
reason            → rationale       → Rationale
poc               → poc_idea        → Proof of Concept
evidence          → evidence        → Evidence
```

**Impact**: Updated 10 files (1 service, 1 usecase, 1 CLI, 1 formatter, 1 log parser, 5 test files)

### Phase 27: Logger Injection for Infrastructure Components (2025-11-02)
**Status**: ✅ Completed

**Problem**:
- `LLM` and `MCPServer` classes used `logging.getLogger()` directly instead of injected `AnalysisLogger`
- LLM and MCP logs were not saved to GHSA-specific JSONL files
- Inconsistent logging across infrastructure layer (some used DI, some didn't)

**Solution**: Inject `LoggerPort` into infrastructure components that are part of analysis workflow

**Changes**:

1. **LLM** ([infra/llm.py:8-62](src/mispatch_finder/infra/llm.py#L8-L62)):
   - **Added**: `logger: LoggerPort` parameter to `__init__`
   - **Removed**: `import logging` and `logger = logging.getLogger(__name__)`
   - **Updated**: All logging calls to use `self._logger.info()`
   - **Payload format**: Changed from `extra={"payload": {...}}` to `payload={...}` (AnalysisLogger API)
   - **Logs**: `llm_input`, `llm_usage`, `llm_output` now written to GHSA-specific JSONL

2. **MCPServer** ([infra/mcp_server.py:23-106](src/mispatch_finder/infra/mcp_server.py#L23-L106)):
   - **Added**: `logger: LoggerPort` parameter to `__init__`
   - **Split logging**:
     - `self._logger` for structured logs (`aggregator_started`, `tunnel_started`, `mcp_cleanup_*`)
     - `debug_logger = logging.getLogger(__name__)` for low-level debug (tool listing)
   - **Rationale**: Structured workflow logs → AnalysisLogger, debug traces → standard logger
   - **Logs**: MCP lifecycle events now written to GHSA-specific JSONL

3. **Container** ([app/container.py:62-80](src/mispatch_finder/app/container.py#L62-L80)):
   - Reordered providers: `logger` defined before `mcp_server` and `llm`
   - Added `logger=logger` injection to both `mcp_server` and `llm` factories

4. **CLI** ([app/cli.py:72-77](src/mispatch_finder/app/cli.py#L72-L77)):
   - Added `logger=container.logger()` when overriding LLM with CLI params

**Not Changed**:
- **Tunnel** ([infra/mcp/tunnel.py](src/mispatch_finder/infra/mcp/tunnel.py)): ❌ Kept `logging.getLogger()`
  - **Rationale**: Low-level infrastructure (SSH tunnel management)
  - GHSA-agnostic network operations, not part of analysis workflow
  - Standard Python logging sufficient for debugging

**Benefits**:
- ✅ **Complete traceability**: LLM calls and MCP lifecycle in same GHSA log file
- ✅ **DDD compliance**: All analysis workflow components use injected logger
- ✅ **Layer consistency**: Infrastructure layer uniformly uses `AnalysisLogger` for structured logs
- ✅ **Separation of concerns**: Debug logs (tunnel SSH) vs. workflow logs (analysis)

**Log Flow**:
```
Analysis Workflow → AnalysisLogger → {ghsa}.jsonl
  ├── ghsa_meta (Orchestrator)
  ├── repos_prepared (Orchestrator)
  ├── diff_built (Orchestrator)
  ├── aggregator_started (MCPServer)     ← NEW
  ├── tunnel_started (MCPServer)         ← NEW
  ├── mcp_ready (Orchestrator)
  ├── llm_input (LLM)                    ← NEW
  ├── llm_usage (LLM)                    ← NEW
  ├── llm_output (LLM)                   ← NEW
  ├── final_result (Orchestrator)
  └── mcp_cleanup_* (MCPServer)          ← NEW

SSH Tunnel → standard logging → console/file (GHSA-agnostic)
```

**Impact**: Updated 4 files (2 infra adapters, 1 container, 1 CLI)

## Active TODOs

**When completing these, remove from this list and document in "Recent Changes" above.**

1. **TODO: Re-enable clear command** (see Phase 18 above)
   - Define semantics
   - Fix resource conflicts
   - Re-enable tests

2. **TODO: Extract default limit (10) to config**
   - Currently hardcoded in `ListUseCase.execute()`
   - Should come from `AppConfig` (new field: `list_default_limit`)
