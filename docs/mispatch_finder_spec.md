## Mispatch Finder - Requirements and Architecture

### Vision
Detect whether historical GHSA patches were correct or potentially left residual vulnerabilities, by orchestrating LLM reasoning and repository-level MCP tools.

### Goals
- CLI and Python API to analyze a given GHSA ID
- Reproducible, cacheable repo preparation (previous/current workdirs)
- Secure, ephemeral MCP exposure via localhost.run with one-shot Authorization (FastMCP + StaticTokenVerifier)
- Provider-agnostic LLM invocation (OpenAI/Anthropic) via `itdev_llm_adapter`
- Clean DDD architecture with dependency inversion

### Out-of-Scope (now)
- Non-GHSA identifiers (CVE) as primary key
- Full PoC execution; we only propose PoC ideas

---

## High-Level Flow
1) Fetch GHSA metadata using `cve_collector.detail(id)` API:
   - Returns enriched `Vulnerability` model with repository metadata, commits, severity, etc.
   - Automatically pulls data from OSV and enriches with GitHub repository info (stars, size)
2) Prepare two cached working directories (copy-based):
   - current: repository's present state (current HEAD)
   - previous: checkout parent of the patched commit (if none, mark previous as unavailable)
3) Start child MCP servers, aggregator, and tunnel in one integrated step
4) Call LLM with prompt, metadata, and MCP context
5) Persist and return result

---

## DDD Architecture (Current)

### Folder Structure
```
src/mispatch_finder/
  app/                          # Application Layer
    cli.py                      # Typer CLI commands (run, show, clear, log, all)
    main.py                     # Application facade functions
    config.py                   # Configuration from env/platformdirs
    container.py                # Dependency injection container

  core/                         # Core Domain Layer
    domain/
      models.py                 # Domain models (AnalysisRequest, AnalysisResult, RepoContext)
      prompt.py                 # Prompt building logic
    usecases/
      analyze.py                # AnalyzeUseCase
      list.py                   # ListUseCase
      clear_cache.py            # ClearCacheUseCase
      logs.py                   # LogsUseCase
    ports.py                    # Port protocols (interfaces)

  infra/                        # Infrastructure Layer
    adapters/                   # All logic consolidated here
      vulnerability_repository.py  # VulnerabilityRepositoryPort impl
      repository.py                # RepositoryPort impl (git operations)
      mcp_server.py                # MCPServerPort impl (child+aggregator+tunnel integrated)
      llm.py                       # LLMPort impl (itdev_llm_adapter wrapper)
      result_store.py              # ResultStorePort impl (JSON persistence)
      log_store.py                 # LogStorePort impl (log parsing/formatting)
      cache.py                     # CachePort impl (directory cleanup)
    mcp/                        # MCP support modules
      tunnel.py                    # localhost.run SSH tunnel
      wiretap_logging.py           # MCP request/response logging middleware
      security.py                  # Auth helpers (legacy, minimal use)

  shared/                       # Shared utilities
    json_logging.py             # Structured JSON logging
    log_summary.py              # Log parsing and formatting
    rmtree_force.py             # Robust directory removal
    to_jsonable.py              # Object serialization
    list_tools.py               # MCP tool listing
```

### Dependency Flow
```
app (CLI/main)
  ↓ uses
core/usecases
  ↓ depends on
core/ports (protocols)
  ↑ implemented by
infra/adapters
  ↓ uses
infra/* (low-level implementations)
```

### Key Principles
- **Dependency Inversion**: Core depends only on ports (protocols), never on infra directly
- **Use Case per Command**: Each CLI command maps to a dedicated use case class
- **Constructor Injection**: Adapters receive config in `__init__`, not per-method call
- **No Duck Typing**: Explicit types, no `getattr`/`hasattr`/`Any`/`cast`
- **Minimal Try/Except**: Let exceptions bubble unless there's a clear recovery strategy
- **DI Container**: `dependency-injector` wires all dependencies
- **No Wrapper Layers**: Adapters implement logic directly, no intermediate infra files

---

## Ports (Protocols)

### VulnerabilityRepositoryPort
Wraps `cve_collector` library (v0.5.0+), converting external models to domain models.

**Domain Model Conversion:**
The adapter translates between external `cve_collector` models and internal domain models, keeping core independent from external libraries (DDD principle).

**Domain Models:**
```python
@dataclass(frozen=True)
class Repository:
    owner: str
    name: str
    ecosystem: Optional[str] = None
    star_count: Optional[int] = None
    size_kb: Optional[int] = None

    @property
    def slug(self) -> str  # "owner/name"
    @property
    def url(self) -> str   # "https://github.com/owner/name"

@dataclass(frozen=True)
class Vulnerability:
    ghsa_id: str
    repository: Repository
    commit_hash: str
    cve_id: Optional[str] = None
    summary: Optional[str] = None
    severity: Optional[str] = None  # "CRITICAL", "HIGH", etc.
```

**Methods:**
- `fetch_metadata(ghsa: str) -> Vulnerability`
  - Uses `cve_collector.detail(id)` to fetch enriched vulnerability data
  - Converts external model to domain `Vulnerability` with nested `Repository`
  - Extracts: repository (owner/name), commit hash, CVE ID, severity, summary
  - Converts repo size from bytes to KB
  - Selects most complete commit hash from candidates

- `list_ids(limit: int, ecosystem: str = "npm") -> list[str]`
  - Uses `cve_collector.list_vulnerabilities(ecosystem, limit, detailed=False)`
  - Returns only GHSA IDs (no metadata) for efficient listing
  - Validates GHSA format: `GHSA-xxxx-xxxx-xxxx`

- `list_with_metadata(limit: int, ecosystem: str = "npm") -> list[Vulnerability]`
  - Uses `cve_collector.list_vulnerabilities(ecosystem, limit, detailed=True)`
  - More efficient than calling `fetch_metadata()` individually
  - Returns domain `Vulnerability` objects in batched operation

- `clear_cache(prefix: str | None = None) -> None`
  - Uses `cve_collector.clear_cache(prefix)`
  - `prefix=None`: clear all caches
  - `prefix="osv"`: clear only OSV vulnerability data
  - `prefix="gh_repo"`: clear only GitHub repository metadata

**cve_collector Integration:**
- Data sources: OSV (GHSA data) + GitHub API (repository enrichment)
- Caching: Disk-based with TTL, prefix-based key structure (`osv:`, `gh_repo:`)
- Authentication: Requires `GITHUB_TOKEN` environment variable
- Supported ecosystems: npm, pypi, Maven, Go, etc.

### RepositoryPort
- `prepare_workdirs(...) -> (current, previous)`
- `get_diff(workdir, commit) -> str`

### MCPServerPort
- `start_servers(...) -> MCPServerContext` (integrated: child servers + aggregator + tunnel)

### LLMPort
- `call(prompt, mcp_url, mcp_token) -> str`

### ResultStorePort, LogStorePort, CachePort
- Standard CRUD and management operations

---

## Tokens and Secrets Strategy
### Inputs
- GitHub token: from env `GITHUB_TOKEN` (used by `cve_collector`)
- Unified LLM API key: from env `MODEL_API_KEY` (fallbacks: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`)

### Ephemeral MCP Authorization Token
- Generated per analysis via `TokenGeneratorPort`
- `secrets.token_urlsafe(32)` - never persisted
- Lifecycle: created → attached to MCP middleware → passed to LLM → destroyed on cleanup

---

## Configuration

### Environment Variables
- `GITHUB_TOKEN`: Required for `cve_collector` API access
- `MODEL_API_KEY`: Unified LLM API key (fallbacks: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`)
- `MISPATCH_HOME`: Application home directory (default: platformdirs cache)
- `MISPATCH_DIFF_MAX_CHARS`: Diff size cap (default: 200_000)
  - Middle-truncation when exceeded
- `MISPATCH_ECOSYSTEM`: Target vulnerability ecosystem (default: npm)
  - Options: npm, pypi, Maven, Go, etc.

### Directory Structure
- Cache base: `platformdirs.user_cache_dir("mispatch_finder")` or `$MISPATCH_HOME`
  - `cache/`: git repos, worktrees
  - `results/`: analysis JSON outputs
  - `logs/`: structured JSONL logs

---

## CLI Commands

### `mispatch_finder run GHSA-xxxx-xxxx-xxxx`
**Use Case**: `RunAnalysisUseCase`

Options:
- `--provider [openai|anthropic]` (default: openai)
- `--model TEXT` (required)
- `--log-level [INFO|DEBUG]`
- `--force-reclone`

Behavior:
1. Resolve secrets from env (`MODEL_API_KEY`, `GITHUB_TOKEN`)
2. Execute use case: fetch metadata → prepare repos → start MCP+tunnel → call LLM → save result
3. Print JSON result

### `mispatch_finder show`
**Use Case**: `ListGHSAUseCase`

Lists available GHSA identifiers from `cve_collector`.

Behavior:
- Uses configured ecosystem (`MISPATCH_ECOSYSTEM` env var, default: npm)
- Limit: 500 (configurable in container)
- Returns GHSA IDs only (no metadata)

### `mispatch_finder clear`
**Use Case**: `ClearCacheUseCase`

Clears application cache and `cve_collector` cache.

Behavior:
- Clears all local caches (git repos, results, logs)
- Clears all `cve_collector` caches (OSV data + GitHub metadata)
- Future: Add `--prefix` option to selectively clear OSV or GitHub caches

### `mispatch_finder logs [GHSA-xxxx-xxxx-xxxx]`
**Use Case**: `LogsUseCase`

Options:
- `--verbose`/`-v`

Behavior:
- With GHSA: print single log (raw JSONL if verbose, summary otherwise)
- Without GHSA: print table of all logs

### `mispatch_finder all`
Options:
- `--provider`, `--model`, `--limit`

Behavior:
- List GHSA IDs
- Filter out completed runs (check logs)
- Run analysis for pending IDs via subprocess

---

## Prompt Contract
Model input:
- GHSA metadata
- MCP tool availability (previous/current)
- Unified diff (truncated if needed)
- Tasks: rate patch adequacy, rate current risk, provide PoC

Output JSON:
```json
{
  "patch_risk": "good" | "low" | "medium" | "high",
  "current_risk": "good" | "low" | "medium" | "high",
  "reason": "...",
  "poc": "..."
}
```

---

## Testing Strategy (Current)

### Structure
```
tests/
  mispatch_finder/
    core/              # Unit tests for use cases, domain, ports
    infra/             # Integration tests for adapters
    app/               # E2E tests for CLI and main facade
    shared/            # Tests for shared utilities
  itdev_llm_adapter/   # Tests for LLM adapter package
```

### Test Count: **90+ tests** across all layers

### Mapping
- **core (17 tests)**: Fast unit tests with fake port implementations
  - Domain models (`RepoContext`, `AnalysisRequest`, `AnalysisResult`)
  - Prompt building with all edge cases
  - Use case execution (`Analyze`, `List`, `ClearCache`, `Logs`)
  
- **infra (28 tests)**: Integration tests with real dependencies
  - VulnerabilityRepository: URL normalization, commit selection, GHSA fetching
  - Repository: Git workdir preparation, diff generation
  - ResultStore, LogStore: JSON persistence and parsing
  - Cache: Directory cleanup with readonly files
  - LLM: JSON extraction, toolset handling
  
- **app (24 tests)**: E2E tests with mocked external services
  - CLI commands: `analyze`, `list`, `clear`, `logs` with all options
  - Facade functions: `run_analysis`, `list_ghsa_ids`, `clear_all_caches`, `logs`
  - Error handling: missing tokens, invalid args
  - Full workflow integration
  
- **shared (21 tests)**: Utility function tests
  - JSON serialization (`to_jsonable`) for all Python types
  - Force directory removal (`rmtree_force`) with edge cases
  - Structured JSON logging with payloads
  - Log summary parsing

### Key Test Files
- `tests/mispatch_finder/core/test_usecases.py`: Use case execution with fake ports
- `tests/mispatch_finder/core/test_usecases_logs.py`: Logs use case scenarios
- `tests/mispatch_finder/core/test_domain_models.py`: All domain model creation and defaults
- `tests/mispatch_finder/core/test_domain_prompt.py`: Prompt building with all states
- `tests/mispatch_finder/infra/test_vulnerability_repository.py`: CVE collector integration
- `tests/mispatch_finder/infra/test_git_repo.py`: Git operations
- `tests/mispatch_finder/infra/test_store.py`: Result persistence
- `tests/mispatch_finder/infra/test_llm.py`: LLM adapter with JSON extraction
- `tests/mispatch_finder/infra/test_cache.py`: Cache clearing
- `tests/mispatch_finder/infra/test_log_store.py`: Log reading and summarization
- `tests/mispatch_finder/app/test_main_e2e.py`: Full run_analysis flow
- `tests/mispatch_finder/app/test_main_facade.py`: Facade function integration
- `tests/mispatch_finder/app/test_cli.py`: Basic CLI execution
- `tests/mispatch_finder/app/test_cli_commands.py`: All CLI commands and options
- `tests/mispatch_finder/app/test_config.py`: Configuration loading
- `tests/mispatch_finder/shared/test_to_jsonable.py`: JSON serialization
- `tests/mispatch_finder/shared/test_rmtree_force.py`: Robust directory removal
- `tests/mispatch_finder/shared/test_json_logging.py`: Structured logging

### Running Tests
```bash
# By layer
pytest tests/mispatch_finder/core      # Unit tests (fast)
pytest tests/mispatch_finder/infra     # Integration tests (may require tokens)
pytest tests/mispatch_finder/app       # E2E tests (most important)
pytest tests/mispatch_finder/shared    # Utility tests

# By marker
pytest -m unit           # All unit tests
pytest -m integration    # All integration tests  
pytest -m e2e           # All E2E tests

# All tests
pytest tests/mispatch_finder
```

### Test Principles
- **Isolation**: Extensive use of `monkeypatch` and `tmp_path` fixtures
- **No External Calls**: Real APIs mocked in E2E, allowed in integration with skip conditions
- **Clear Intent**: Each test focuses on one specific behavior
- **Realistic Scenarios**: E2E tests mirror actual usage patterns
- **Comprehensive Coverage**: All public APIs, error paths, and edge cases tested

---

## Container & DI

### Container Configuration
- **Singletons**: `VulnerabilityRepository`, `Repository`, `ResultStore`, `LogStore`, `Cache`
- **Factories**: Use cases, `MCPServer`, `LLM`
- **Configuration**: `providers.Configuration()` for centralized settings

### Configuration Keys
Internal config keys (in `container.config`):
- `llm_provider_name`: LLM provider (e.g., "openai", "anthropic")
- `llm_model_name`: Model identifier (e.g., "gpt-4", "claude-3-5-sonnet-20241022")
- `llm_api_key`: API key for LLM service
- `github_token`: GitHub token for vulnerability data
- `cache_dir`: Base directory for caches
- `results_dir`: Directory for analysis results
- `logs_dir`: Directory for structured logs
- `mcp_port`: Port for MCP aggregator (default: 18080)
- `prompt_diff_max_chars`: Max chars for diff in prompt (default: 200000)
- `list_limit`: Max GHSA IDs to list (default: 500)

### Parameter Mapping
CLI-friendly parameter names are mapped to config keys in `app/main.py`:
- `provider` → `llm_provider_name`
- `model` → `llm_model_name`
- `api_key` → `llm_api_key`

This allows clean CLI usage while avoiding conflicts with `dependency-injector`'s reserved attributes.

### Use Case Wiring Example
```python
# LLM adapter receives config from container
llm = providers.Factory(
    LLM,
    provider=config.llm_provider_name,
    model=config.llm_model_name,
    api_key=config.llm_api_key,
)

# Use cases receive dependencies via DI
run_analysis = providers.Factory(
    RunAnalysisUseCase,
    vuln_repo=vuln_repo,          # Singleton
    repo=repo,                     # Singleton
    mcp=mcp_server,                # Factory
    llm=llm,                       # Factory
    store=result_store,            # Singleton
    token_gen=token_gen,           # Singleton
    prompt_diff_max_chars=config.prompt_diff_max_chars.as_int(),
)
```

---

## Engineering Conventions & Logging

### Code Conventions
- **Imports**: Top of module, no local imports
- **Types**: Avoid `Any`, avoid `type: ignore`. Explicit dataclasses and protocols
- **No Duck Typing**: No `getattr`/`hasattr`/`cast` - use explicit attributes
- **Error Handling**: Fail fast, minimal try/except. Let exceptions bubble unless clear recovery rationale
- **Naming**: Descriptive variables, functions as verbs, snake_case
- **DDD Structure**: Strict separation of app/core/infra/shared

### Logging Policy
- Standard library `logging` with structured JSON output
- CLI configures file (`<cache>/logs/<GHSA>.jsonl`) + console handlers
- Payload-wrapped entries: `{"level": "...", "logger": "...", "message": "...", "payload": {...}}`
- MCP wiretap middleware logs all requests/responses

### Run-time Logging Payloads
- `ghsa_meta`: GHSA metadata fetched
- `repos_prepared`: Workdir paths
- `diff_built`: Diff length and truncation status
- `mcp_ready`: Server URLs and mount status
- `llm_input`: Prompt details
- `llm_output`: Raw response
- `llm_usage`: Token counts
- `final_result`: Complete analysis result

---

## Changes (History)

### Latest Refactoring (DDD Architecture + Consolidation + Comprehensive Testing)

#### Recent Changes
- **Configuration Naming (2025-01-11)**: Renamed config keys to avoid `dependency-injector` reserved attributes
  - `provider` → `llm_provider_name`
  - `model` → `llm_model_name`
  - `api_key` → `llm_api_key`
  - Added parameter mapping in `with_container` decorator for CLI compatibility
- **Type Safety Enhancement**: Added `ParamSpec` and `Concatenate` to `with_container` decorator
  - Preserves exact type signatures through decorator
  - Enables IDE autocomplete and type checking for facade functions
- **Logging Consolidation**: Moved LLM provider/model logging from UseCase to LLM adapter
  - `LLMPort` no longer exposes implementation details
  - All LLM metadata logged internally by adapter
  - Log summary parses `llm_input`/`llm_output` messages for provider/model

#### Architecture
- **Ports Introduction**: Defined protocol interfaces for all external dependencies
  - `VulnerabilityRepositoryPort`, `RepositoryPort`, `MCPServerPort`, `LLMPort`
  - `ResultStorePort`, `LogStorePort`, `CachePort`, `TokenGeneratorPort`
- **Use Cases**: Created dedicated use case classes for each CLI command
  - `AnalyzeUseCase`: Full analysis workflow
  - `ListUseCase`: GHSA listing
  - `ClearCacheUseCase`: Cache management
  - `LogsUseCase`: Log display
- **Adapters**: Implemented ports with all logic consolidated (no wrapper layers)
  - `VulnerabilityRepository`: CVE collector integration, URL normalization, commit selection
  - `Repository`: Git operations (clone, checkout, diff) - direct implementation
  - `MCPServer`: Child servers + aggregator + tunnel - fully integrated
  - `LLM`: itdev_llm_adapter + JSON extraction - complete implementation
  - `ResultStore`: JSON save/load/list - direct file operations
  - `LogStore`: Log parsing and formatting - direct implementation
  - `Cache`: Directory cleanup - direct rmtree
- **Container**: DI container with `dependency-injector`, factory and singleton patterns

#### Testing (90+ tests)
- **Test Restructure**: Migrated from `unit/integration` to DDD-aligned `app/core/infra/shared`
- **Core Tests (17)**: Unit tests for all domain models, prompt building, and use cases
  - Domain models: `RepoContext`, `AnalysisRequest`, `AnalysisResult`
  - Prompt builder: All availability states, diff handling, JSON schema
  - Use cases: Full execution flows with fake ports
- **Infra Tests (28)**: Integration tests for all adapters
  - VulnerabilityRepository: 10 tests (URL formats, commit selection, real API with skip)
  - Repository, Store, Cache, LogStore, LLM: Comprehensive adapter testing
- **App Tests (24)**: E2E tests for CLI and facade
  - All CLI commands (`run`, `show`, `clear`, `log`) with options
  - Error scenarios (missing tokens, invalid args)
  - Full workflow with mocked external dependencies
- **Shared Tests (21)**: Utility function coverage
  - JSON serialization for all Python types
  - Robust directory removal (readonly, symlinks)
  - Structured logging validation

#### Cleanup
- **Deleted Legacy Files**: 
  - Old wrapper adapters: `infra/adapters/cve_adapter.py`, `git_adapter.py`, etc.
  - Legacy core: `core/analyze.py`, `app/prompts.py`, `core/toolset.py`
  - Legacy infra: `infra/git_repo.py`, `infra/llm.py`, `infra/store.py`
  - Legacy MCP: `infra/mcp/mounts.py`, `infra/mcp/aggregator.py`
  - Legacy tests: `tests/mispatch_finder/unit/*`, `tests/mispatch_finder/integration/*`
- **Public API**: Updated `__init__.py` to export facade functions
  - `run_analysis`, `list_ghsa_ids`, `clear_all_caches`, `logs`

### Recent Changes (2025-01-12)

#### Test Mock Refactoring
- **Root Cause Fix**: E2E tests were failing due to mismatched mocks - `MockVulnerabilityRepository` returned fake commit SHAs, but real `Repository` adapter tried to find them in git repos
- **Solution**: Added `MockRepository` to `tests/mispatch_finder/app/conftest.py` to mock git operations
- **Container Override Strategy**: Monkeypatch `Container` class (not `with_container` decorator) to preserve parameter mapping logic
- **Centralized Mocks**: Created reusable mock classes and fixtures in `conftest.py`:
  - `MockVulnerabilityRepository`: Fake GHSA metadata
  - `MockRepository`: Fake git operations  
  - `MockLLM`: Canned JSON responses
  - `MockMCPServer`: Mock MCP context
  - `DummyTunnel`: No-op tunnel

#### Test Coverage Improvements
- **Unskipped Tests**: Fixed previously skipped integration tests
  - `test_vulnerability_repository_fetch_metadata_real`: Now uses known-good GHSA ID `GHSA-93vw-8fm5-p2jf`
  - `test_cli_logs_with_ghsa_shows_details`: Uses `mock_container_for_logs` fixture
  - `test_cli_logs_verbose_flag`: Tests verbose output with fixture
- **Result**: 93 passed, 4 skipped (down from 6 skipped)

### Earlier Changes
- CLI migrated to Typer
- MCP security with `StaticTokenVerifier`
- Prompt includes unified diff with size cap
- OpenAI Responses API integration
- `cve_collector` new module API integration
- Removed blanket try/except blocks

---

## Open Questions / Iteration Items
- Fallback when localhost.run is unavailable
- Results schema versioning
- Additional vulnerability sources beyond npm ecosystem
