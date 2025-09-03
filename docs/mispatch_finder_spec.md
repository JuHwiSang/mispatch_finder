## Mispatch Finder - Requirements and Architecture

### Vision
Detect whether historical GHSA patches were correct or potentially left residual vulnerabilities, by orchestrating LLM reasoning and repository-level MCP tools.

### Goals
- CLI and Python API to analyze a given GHSA ID
- Reproducible, cacheable repo preparation (pre/post commit workdirs)
- Secure, ephemeral MCP exposure via localhost.run with one-shot Authorization
- Provider-agnostic LLM invocation (OpenAI/Anthropic) via `itdev_llm_adapter`

### Out-of-Scope (now)
- Non-GHSA identifiers (CVE) as primary key
- Full PoC execution; we only propose PoC ideas

---

## High-Level Flow
1) Fetch GHSA metadata using `cve_collector` (repo URL, patch commit).
2) Prepare two cached working directories:
   - post: checkout target patch commit
   - pre: checkout parent of patch commit (if none, mark pre as unavailable)
3) Stand up 4 child MCP servers (prefix-mount):
   - pre_repo (repo_read_mcp), pre_debug (jsts_debugger)
   - post_repo (repo_read_mcp), post_debug (jsts_debugger)
4) Aggregate under a main fastMCP with Authorization middleware.
5) Expose main server via localhost.run (SSH reverse tunnel) and capture public URL.
6) Build `Toolset` with Authorization header and call LLM with prompt+metadata.
7) Persist and present the result.

---

## Senior Folder Structure (proposal)
```
src/mispatch_finder/
  app/                     # Presentation + orchestration
    cli.py                 # Typer/argparse CLI only (I/O & args)
    main.py                # Public Python API; orchestrates end-to-end run
    config.py              # Platformdirs, tokens from env, defaults
    models.py              # DTOs: AnalysisRequest/Result, RepoContext, etc.
    prompts.py             # Prompt builders/templates
  core/                    # Business logic
    analyze.py             # Main analyze() combining GHSA meta + MCP + LLM
    toolset.py             # Toolset assembly based on tunnel URL + prefixes
  infra/                   # External boundaries (adapters, side effects)
    cve.py                 # cve_collector wrapper
    git_repo.py            # git clone/fetch/checkout, caching
    mcp/
      mounts.py            # create repo_read_mcp / jsts_debugger servers
      aggregator.py        # compose main fastMCP + security middleware
      security.py          # Authorization middleware
      tunnel.py            # localhost.run ssh lifecycle
    llm.py                 # itdev_llm_adapter usage helpers
    store.py               # JSON result cache read/write
```

Rationale:
- app: inputs/outputs; no business rules
- core: composition of domain behavior, provider-agnostic
- infra: side-effecting code (network, disk, processes)

---

## Tokens and Secrets Strategy
### Inputs
- GitHub token: from env or config file (used by cve_collector)
- LLM provider API key: from env/CLI option (OpenAI/Anthropic)

### Ephemeral MCP Authorization Token (one-shot)
- Generated per analysis session (per-instance, not global process):
  - Create cryptographically secure random string (`secrets.token_urlsafe(32)`)
  - Never accept injection from external callers
  - Stored only in memory in the analyzer object; not persisted
- Injection points:
  - Main fastMCP security middleware checks header `Authorization: Bearer <token>`
  - `itdev_llm_adapter.Toolset.headers["Authorization"] = Bearer <token>`
- Lifecycle:
  - Created at analysis start
  - Attached to MCP server on create (middleware)
  - Passed to LLM Toolset headers
  - Destroyed when analysis completes (server shutdown), reference dropped

---

## Configuration
- Diff size cap for prompts: `MISPATCH_DIFF_MAX_CHARS` (default: 200_000)
  - If the unified diff exceeds the cap, it is middle-truncated (head + tail joined with `...`).

---

## CLI Commands
### `mispatch_finder run GHSA-xxxx-xxxx-xxxx`
Options:
- `--provider [openai|anthropic]` (default: openai)
- `--model TEXT` (required)
- `--api-key TEXT` (required; or from env)
- `--github-token TEXT` (required; or from env)
- `--log-level [INFO|DEBUG]`
- `--force-reclone` (optional)

Behavior:
1. Fetch GHSA meta → clone/checkout → start MCP → tunnel → call LLM
2. Print JSON result and human summary; persist to cache

### `mispatch_finder show [--ghsa GHSA-...]`
- Print last results; show MCP/tunnel status if running

---

## Prompt Contract (sketch)
Model input includes:
- GHSA metadata summary
- Availability table of MCP tool prefixes (pre_repo, pre_debug, post_repo, post_debug)
- Unified diff of the patched commit (may be truncated by size cap)
- Tasks:
  - Assess patch correctness
  - Identify residual risks and impacted surfaces
  - Provide reasoning and references (files/lines via tools)
  - Suggest simple PoC ideas if risk detected
Output JSON fields:
- `verdict`: "good" | "risky"
- `severity`: "low" | "medium" | "high"
- `rationale`: str
- `evidence`: list[{ file, line?, snippet?, tool }]
- `poc_idea?`: str

---

## Testing Plan
- Unit: token generation (core), git commands (infra), toolset assembly, tunnel URL parsing
- Integration (mocked): cve_collector → repo prep → MCP mounts → LLM adapter call
- CLI smoke: argument parsing and dispatch

---

## Changes (since initial draft)
- CLI migrated to Typer; console entry is `mispatch_finder.app.cli:app`.
- Credentials required at CLI: `--provider`, `--model`, `--api-key` (or env), `--github-token` (or env).
- Internal API updated: `AnalysisRequest.api_key` and `.github_token` are required (non-Optional); `run_analysis` requires them explicitly.
- CLI `main()` wrapper removed; Typer app is invoked directly.
- MCP security: main FastMCP uses `StaticTokenVerifier`, requiring `Authorization: Bearer <token>`.
- MCP mounts: use dataclass `ServerMap` with optional `pre_repo`/`pre_debug`; prefixes use underscores (e.g., `/post_repo`).
- Prompt: include unified diff of the patched commit; respects `MISPATCH_DIFF_MAX_CHARS` with middle truncation.
- Repo prep: worktrees for pre/post; parent commit auto-derived when missing.
- `show` command: when no GHSA provided, lists cached result summaries.
- OpenAI adapter: Responses API tools use dict-based `ToolParam` with `{"type":"mcp", ...}` and `tool_choice="auto"`.
- Test suite implemented: pytest with unit/integration markers; only `itdev_llm_adapter` is mocked; tunnel is stubbed in integration; CLI tests use `CliRunner`.

## Open Questions / Iteration Items
- jsts_debugger enablement gate (detect JS/TS project reliably?)
- Fallback when localhost.run is unavailable
- Results schema versioning


---

## Testing (implemented)
### Layout
- `tests/mispatch_finder/unit`: fast, isolated tests
- `tests/mispatch_finder/integration`: end-to-end orchestration with minimal stubs

### Pytest configuration
- `pytest.ini`:
  - `pythonpath = src` for src-layout imports
  - markers: `unit`, `integration`

### Shared fixtures
- `tests/conftest.py`:
  - Adds `src/` to `sys.path`
  - Mocks `itdev_llm_adapter.factory.get_adapter` with a dummy adapter returning deterministic JSON
  - Everything else (git, MCP server creation, repo scan) is real unless explicitly stubbed by a test

### Unit tests (highlights)
- Config: cache/results dirs, `MISPATCH_DIFF_MAX_CHARS` parsing
- CVE helpers: `_normalize_repo_url`, `_choose_commit`
- Prompts: includes GHSA/repo/commit/diff
- Store: save/load/list summaries
- Git repo: commit diff text, worktrees creation against a local temporary repo
- Mounts/Toolset: Node project detection and tool availability map
- Analyzer: ephemeral MCP token generation per instance
- LLM wrapper: returns JSON via mocked adapter

### Integration tests (highlights)
- `run_analysis` end-to-end using a local temporary git repo
  - Stubs `fetch_ghsa_metadata` to point at the local repo
  - Stubs tunnel (`start_tunnel`/`stop_tunnel`) to avoid `localhost.run` network
  - Aggregator/MCP servers run locally (ensure port 18080 is free)
- CLI `show` command using `CliRunner`
  - Redirects results directory to a temp directory and verifies list/single outputs

### Running
- Unit only: `pytest -q -m unit`
- Integration only: `pytest -q -m integration`
- All tests: `pytest -q`

### Mocking policy
- Mandatory mock: `itdev_llm_adapter` adapter factory to prevent real OpenAI/Anthropic calls
- Optional stubs in integration: tunnel (network), leave aggregator real by default


