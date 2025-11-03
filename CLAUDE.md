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

## Core Development Principles

### 1. Quality Standards (Clean Code, Latest Tech, Latest Versions)
- **For src/ (Production Code)**:
  - **Clean Code**: SOLID principles, DRY, clear naming, proper abstraction
  - **Latest Tech**: Python 3.13+ features, modern type hints (`list[T]`, `str | None`)
  - **Latest Versions**: Use latest stable dependencies, no deprecated APIs
  - **When exceptions needed**: Always ask user for approval first

- **For tests/ (Test Code)**:
  - **Pragmatic approach**: Quality standards apply more loosely
  - **Goal**: Test correctness > test elegance
  - **Trade-offs acceptable**: Duplicate code, simple fakes over complex mocks

### 2. Continuous Improvement
- **User feedback → CLAUDE.md updates**: Incorporate user's coding style, methodologies, rules
- **Document decisions**: When user approves exceptions, document rationale
- **Evolving guidelines**: This document should grow with project needs

### 3. Dependency Inversion
- **Core never depends on infra** - only on Ports (protocols)
- Infra implements Ports and is injected via DI container
- Example: `AnalysisOrchestrator` uses `LoggerPort`, not `AnalysisLogger`

### 4. Service Layer Pattern
- Business logic resides in `core/services/`:
  - `DiffService`: Diff generation and truncation
  - `JsonExtractor`: JSON extraction from LLM responses
  - `AnalysisOrchestrator`: Complete analysis workflow coordination
- UseCases are thin orchestration layers

### 5. Ports & Adapters
All external dependencies are abstracted through Ports:
- `VulnerabilityDataPort` → `VulnerabilityDataAdapter` (cve_collector adapter)
- `RepositoryPort` → `GitRepository` (git operations)
- `MCPServerPort` → `MCPServer` (MCP server management)
- `LLMPort` → `LLM` (LLM API adapter)
- `LoggerPort` → `AnalysisLogger` (structured logging)
- `AnalysisStorePort` → `AnalysisStore` (read JSONL logs)

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

6. **`mcp <GHSA-ID>`** - Start standalone MCP server
   ```bash
   mispatch-finder mcp GHSA-xxxx-xxxx-xxxx                      # Local server on default port
   mispatch-finder mcp GHSA-xxxx-xxxx-xxxx --mode tunnel --auth # Tunnel with authentication
   mispatch-finder mcp GHSA-xxxx-xxxx-xxxx --port 8080          # Custom port
   ```
   - UseCase: `MCPUseCase` ([core/usecases/mcp.py](src/mispatch_finder/core/usecases/mcp.py))
   - CLI Command: `mcp()` ([app/cli.py:356](src/mispatch_finder/app/cli.py#L356))
   - **Behavior**: Fetches vulnerability metadata from GHSA ID, prepares repository workdirs (current & previous), and starts MCP server
   - **Options**:
     - `ghsa`: GitHub Security Advisory ID (required argument)
     - `--port, -p`: Port number for MCP server (default: 18080)
     - `--mode, -m`: Server mode - `local` (local only) or `tunnel` (with SSH tunnel, default: local)
     - `--auth, -a`: Enable authentication (generates random token)
     - `--force-reclone`: Force re-clone of repositories (default: False)
   - **Testing note**: CLI tests are minimal due to infinite loop (server keeps running). Core functionality tested at UseCase level.

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

## Current Architecture Status

### Configuration (Pydantic BaseSettings)
- **AppConfig hierarchy**: `DirectoryConfig`, `VulnerabilityConfig`, `LLMConfig`, `GitHubConfig`, `AnalysisConfig`, `LoggingConfig`, `RuntimeConfig`
- **Environment prefix**: `MISPATCH_FINDER_` (nested: `MISPATCH_FINDER_LLM__API_KEY`)
- **Runtime mutation**: `config.runtime.ghsa` set by CLI before container creation
- **DI integration**: `container.config.from_pydantic(config)`

### Logging System
- **AnalysisLogger**: GHSA-specific JSONL files + optional console output
- **Standard library**: `python-json-logger` for JSON formatting
- **Resource pattern**: `providers.Resource` for proper file handle cleanup
- **Structure**: Flat `extra={key: value}` (no payload wrapper)
- **Injected into**: `AnalysisOrchestrator`, `LLM`, `MCPServer` (via `LoggerPort`)

### Type System (Python 3.13+)
- **Modern syntax**: `list[T]`, `dict[K, V]`, `str | None`, `A | B`
- **Legacy only**: `typing.Literal`, `typing.Protocol`, `typing.TYPE_CHECKING`
- **Pragmatic approach**: `# type: ignore[assignment]` where type system has limitations
- **No mid-function imports**: All imports at file top

### CLI Structure
- **No facades**: CLI commands create Container + execute UseCase inline
- **Commands**: `analyze`, `list`, `logs`, `batch` (subprocess orchestration)
- **Clear disabled**: Resource conflict with cve_collector (TODO)

### UseCase Pattern
- **Constructor**: DI dependencies only
- **execute()**: Runtime parameters
- **Example**: `ListUseCase.__init__(vuln_data)`, `execute(limit, ecosystem, detailed, filter_expr)`

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

## Recent Changes (2025-11)

### Iterator-Based Listing + Human-Readable CLI (11-01)
- **Efficiency**: `list_vulnerabilities_iter()` for lazy iteration (no batch loading)
- **User experience**: `--json` flag for scriptability, human-readable default
- **CLI options**: `--detail` (was `--detailed`), `--include-analyzed` (was `--all`)

### Test Organization + Environment Variables (11-01)
- **Test structure**: `tests/app/cli/test_{command}.py` (one file per command)
- **Environment**: All tests use `MISPATCH_FINDER_GITHUB__TOKEN` (not old `GITHUB_TOKEN`)

### Logging Infrastructure Complete Redesign (11-02 ~ 11-03)
- **Unified store**: `AnalysisStore` (read-only JSONL logs)
- **GHSA-specific files**: `logs/{ghsa}.jsonl` (required parameter)
- **Dual output**: File (always) + console (CLI only)
- **Resource pattern**: `providers.Resource` with `shutdown_resources()` for proper cleanup
- **Flat structure**: `logger.info("event", key=val)` (no payload wrapper)
- **Backward compat**: Old logs (`payload: {...}`) still parse correctly
- **Logger injection**: `LLM`, `MCPServer` use injected `LoggerPort`

### Type Safety + Error Handling (11-02 ~ 11-03)
- **Pydantic models**: `AnalysisOrchestrator` returns `AnalysisResult` (not dict)
- **Field mapping**: LLM JSON (`current_risk`, `patch_risk`) → `AnalysisResult` (`verdict`, `severity`)
- **Custom exception**: `GHSANotFoundError` for 404s → clean up empty log files
- **Pragmatic types**: `# type: ignore[assignment]` where type system can't infer (Union return types)

### MCP Command + Optional Tunneling (11-03)
- **New command**: `mcp` command for standalone MCP server
- **Optional tunneling**: `use_tunnel` parameter in `MCPServerPort.start_servers()`
  - `use_tunnel=True`: Creates SSH tunnel via localhost.run (default for `analyze`)
  - `use_tunnel=False`: Local-only server (for `mcp --mode internal`)
- **Authentication**: Random token generation with `secrets.token_urlsafe(32)`
- **CLI options**: `--port`, `--mode` (internal/external), `--auth`, `--current`, `--previous`
- **Type safety**: `MCPServerContext.public_url` is now `str | None`
- **Testing**: UseCase tests cover core functionality; CLI tests minimal (infinite loop issue)
- **Infrastructure updates**:
  - `MCPServer` handles optional tunnel creation
  - `AnalysisOrchestrator` explicitly passes `use_tunnel=True` and validates `public_url`
  - Signal handlers in CLI for clean shutdown

### UseCase Test Reorganization (11-03)
- **Structure**: `tests/core/usecases/` now mirrors `app/cli/` structure
  - Created `tests/core/usecases/` directory with per-usecase test files
  - `conftest.py` with shared Fake classes (FakeVulnRepo, FakeRepo, FakeMCP, etc.)
  - Individual test files: `test_analyze.py`, `test_list.py`, `test_clear_cache.py`, `test_mcp.py`, `test_logs.py`
- **Removed**: Old monolithic files (`test_usecases.py`, `test_usecases_logs.py`)
- **Benefits**: Better organization, easier to find tests, consistent with CLI test structure

### MCP Command Redesign (11-03)
- **Interface change**: `mcp` now requires GHSA ID as argument (like `analyze`)
  - Old: `mcp --current /path --previous /path` (incorrect design)
  - New: `mcp GHSA-xxxx-xxxx-xxxx` (automatically prepares workdirs)
- **Mode naming**: Changed from `internal`/`external` to `local`/`tunnel`
  - `--mode local`: Local-only access (default)
  - `--mode tunnel`: SSH tunnel via localhost.run
- **MCPUseCase updates**:
  - Added dependencies: `VulnerabilityDataPort`, `RepositoryPort`, `TokenGeneratorPort`
  - Removed direct `secrets` usage, now uses `TokenGeneratorPort` (proper DI)
  - Prepares workdirs from GHSA ID automatically
  - Uses `vuln.repository.url` instead of manually constructing URL
- **Test updates**: All 11 tests updated with new dependencies, token generation tests fixed
- **Documentation**: CLAUDE.md and CLI help updated to reflect new interface

### MCP Port Configuration Refactoring (11-04)
- **Design improvement**: Port parameter moved from `__init__` to `start_servers()`
  - **Before**: `MCPServer.__init__(port=18080, logger=...)` - port decided at construction time
  - **After**: `MCPServer.__init__(logger=...)` + `start_servers(port=..., ...)` - port decided at runtime
- **Rationale**: Port is a runtime parameter that should be specified when starting the server, not during object construction
- **Configuration**: Added `AnalysisConfig.mcp_port` (default: 18080, env: `MISPATCH_FINDER_ANALYSIS__MCP_PORT`)
- **Protocol update**: `MCPServerPort.start_servers()` now requires `port: int` parameter
- **Service layer**: `AnalysisOrchestrator` receives `mcp_port` via DI and passes it to `start_servers()`
- **UseCase layer**: `MCPUseCase.execute()` already had `port` parameter, now passes it to `start_servers()`
- **Container**:
  - Removed `port=18080` from `mcp_server` provider
  - Added `mcp_port=config.analysis.mcp_port` to `analysis_orchestrator` provider
  - Fixed `mcp_uc` provider with missing dependencies (`vuln_data`, `repo`, `token_gen`)
- **Test updates**: All Fake/Mock implementations updated with `port` parameter in `start_servers()`
  - `tests/core/usecases/conftest.py` - FakeMCP
  - `tests/app/conftest.py` - MockMCPServer
  - `tests/core/test_services.py` - FakeMCP (2 orchestrator tests)
  - `tests/core/usecases/test_analyze.py` - orchestrator construction

### Disabled Features
- **clear command**: Resource conflict with cve_collector (TODO: define semantics)

## Active TODOs

**When completing these, remove from this list and document in "Recent Changes" above.**

1. **TODO: Re-enable clear command** (see Phase 18 above)
   - Define semantics
   - Fix resource conflicts
   - Re-enable tests

2. **TODO: Extract default limit (10) to config**
   - Currently hardcoded in `ListUseCase.execute()`
   - Should come from `AppConfig` (new field: `list_default_limit`)
