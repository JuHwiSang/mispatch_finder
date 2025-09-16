## Mispatch Finder - Requirements and Architecture

### Vision
Detect whether historical GHSA patches were correct or potentially left residual vulnerabilities, by orchestrating LLM reasoning and repository-level MCP tools.

### Goals
- CLI and Python API to analyze a given GHSA ID
- Reproducible, cacheable repo preparation (pre/post commit workdirs)
- Secure, ephemeral MCP exposure via localhost.run with one-shot Authorization (FastMCP + StaticTokenVerifier)
- Provider-agnostic LLM invocation (OpenAI/Anthropic) via `itdev_llm_adapter`

### Out-of-Scope (now)
- Non-GHSA identifiers (CVE) as primary key
- Full PoC execution; we only propose PoC ideas

---

## High-Level Flow
1) Fetch GHSA metadata using `cve_collector` (repo URL, patch commit).
2) Prepare two cached working directories (copy-based):
   - post: checkout target patch commit
   - pre: checkout parent of patch commit (if none, mark pre as unavailable)
3) Start child MCP servers conditionally and mount under prefixes:
   - post_repo: repo_read_mcp; post_debug: jsts_debugger (if Node project)
   - pre_repo: repo_read_mcp (if parent exists); pre_debug: jsts_debugger (if Node project)
4) Aggregate under a main FastMCP with Authorization (StaticTokenVerifier) and wiretap logging.
5) Expose main server via localhost.run (SSH reverse tunnel) and capture public URL.
6) Build a single `Toolset` to the aggregator `/mcp` with bearer token and call the LLM with prompt+metadata.
7) Persist and present the result.

---

## Senior Folder Structure (current)
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
    toolset.py             # Tool availability map (slash-style keys)
  infra/                   # External boundaries (adapters, side effects)
    cve.py                 # cve_collector wrapper
    git_repo.py            # git clone/fetch/checkout, caching
    mcp/
      mounts.py            # create repo_read_mcp / jsts_debugger servers
      aggregator.py        # compose main FastMCP + security middleware + wiretap
      wiretap_logging.py   # logging middleware for MCP request/response events
      security.py          # Lightweight auth middleware helper (legacy/minimal)
      tunnel.py            # localhost.run ssh lifecycle
    llm.py                 # itdev_llm_adapter usage helpers
    store.py               # JSON result cache read/write
  shared/
    fastapi_raw_log.py     # MCP wiretap middleware (raw request/response log)
    list_tools.py          # Utility to list mounted tools
    rmtree_force.py        # Robust directory removal
    to_jsonable.py         # Safe converter for logging payloads
    log_summary.py         # Dataclass-based log summarizer and table formatter
```

Rationale:
- app: inputs/outputs; no business rules
- core: composition of domain behavior, provider-agnostic
- infra: side-effecting code (network, disk, processes)

---

## Tokens and Secrets Strategy
### Inputs
- GitHub token: from env `GITHUB_TOKEN` (used by `cve_collector`)
- Unified LLM API key: from env `MODEL_API_KEY` (fallbacks: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`)

### Ephemeral MCP Authorization Token (one-shot)
- Generated per analysis session (per-instance, not global process):
  - Create cryptographically secure random string (`secrets.token_urlsafe(32)`)
  - Never accept injection from external callers
  - Stored only in memory in the analyzer object; not persisted
- Injection points:
  - Main FastMCP security middleware checks header `Authorization: Bearer <token>`
  - OpenAI adapter: Toolset contributes `headers.Authorization` or `bearer_token` → Responses API `tools` include headers
  - Anthropic adapter: each `mcp_servers` entry includes `authorization_token`
- Lifecycle:
  - Created at analysis start
  - Attached to MCP server on create (middleware)
  - Passed to LLM Toolset
  - Destroyed when analysis completes (server shutdown), reference dropped

---

## Configuration
- Diff size cap for prompts: `MISPATCH_DIFF_MAX_CHARS` (default: 200_000)
  - If the unified diff exceeds the cap, it is middle-truncated (head + tail joined with `...`).
 - Cache base: user cache directory via `platformdirs`. Results saved under `<cache>/results/`.

---

## CLI Commands
### `mispatch_finder run GHSA-xxxx-xxxx-xxxx`
Options:
- `--provider [openai|anthropic]` (default: openai)
- `--model TEXT` (required)
- `--log-level [INFO|DEBUG]`
- `--force-reclone` (optional)

Behavior:
1. Fetch GHSA meta → clone/checkout → start MCP → tunnel → call LLM
2. Print JSON result; persist to cache

Credentials are read from environment variables:
- LLM API key: `MODEL_API_KEY` (fallbacks: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`)
- GitHub token: `GITHUB_TOKEN`

### `mispatch_finder show`
- List available GHSA identifiers via `CVECollector` (requires `GITHUB_TOKEN`).

### `mispatch_finder clear`
- Clear local caches/results and CVE collector local state.

### `mispatch_finder log [GHSA-xxxx-xxxx-xxxx]`
Options:
- `--verbose`/`-v`

Behavior:
- When GHSA is provided: prints structured JSON lines from `<cache>/logs/<GHSA>.jsonl` (errors if missing).
- When GHSA is omitted: prints a right-aligned summary table for all `logs/*.jsonl` with columns:
  - GHSA, Verdict, Model, MCP Calls, Tokens, RunDate
  - MCP Calls: counts `mcp_request` events but excludes entries where `payload.method == "tools/list"`.
  - Tokens: sums `llm_usage.payload.total_tokens` across the run.
  - RunDate: approximated from the log file's modified time.
- With `--verbose`: appends MCP tool call details as `(NAME: NUM, NAME: NUM, ...)`.

### `mispatch_finder all`
Options:
- `--provider [openai|anthropic]` (default: openai)
- `--model TEXT` (required)
- `--limit`/`-n` INTEGER (optional)

Behavior:
- Uses the same source as `show` to obtain GHSA identifiers.
- Summarizes existing logs and skips IDs whose verdict is already `good` or `risky`.
- Runs analysis (`run`) for remaining IDs, respecting `--limit`.

---

## Prompt Contract (current)
Model input includes:
- GHSA metadata summary
- Availability note of MCP tools (pre/post), using a simple map:
  - core/toolset: `{"pre/repo": bool, "pre/debug": bool, "post/repo": bool, "post/debug": bool}`
  - aggregator mounts actually use underscore prefixes: `/pre_repo`, `/pre_debug`, `/post_repo`, `/post_debug`
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
- `evidence`: list[{ file, line?, snippet? }]
- `poc_idea?`: str

---

## Testing Plan
- Unit: token generation (core), git commands (infra), toolset assembly, tunnel URL parsing
- Integration (stubbed tunnel): cve_collector → repo prep → MCP mounts → LLM adapter call
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
- Git repo: commit diff text, copy-based pre/post checkout
- Mounts/Toolset: Node project detection and tool availability map
- Analyzer: ephemeral MCP token generation per instance
- LLM wrapper: returns JSON via mocked adapter

### Integration tests (highlights)
- `run_analysis` end-to-end using a local temporary git repo
  - Stubs `fetch_ghsa_metadata` to point at the local repo
  - Stubs tunnel to avoid `localhost.run` network
  - Aggregator/MCP servers run locally (ensure port 18080 is free)
- CLI `show` command using `CliRunner`
  - Verifies identifier listing via `CVECollector`

### Running
- Unit only: `pytest -q -m unit`
- Integration only: `pytest -q -m integration`
- All tests: `pytest -q`

### Mocking policy
- Mandatory mock: `itdev_llm_adapter` adapter factory to prevent real OpenAI/Anthropic calls
- Optional stubs in integration: tunnel (network), leave aggregator real by default



---

## Implementation Notes (current)
- Aggregator runs `transport="streamable-http"` on port 18080; URL is `http://127.0.0.1:18080`.
- Tunnel parses public URL matching `https://*.lhr.life` from `ssh` stdout.
- LLM call uses a single `Toolset` labeled `mispatch_tools` targeting `<public-url>/mcp` with bearer token.
- Wiretap logging middleware logs full MCP request/response payloads. Non-JSON types are converted via `shared/to_jsonable.py`.

---

## Engineering Conventions & Logging

### Code conventions
- Imports: placed at the top of the module. No local imports inside functions.
- Types: avoid `Any`, avoid `type: ignore`. Use explicit dataclasses and precise types.
- No dynamic duck-typing helpers for core logic (no `getattr`/`hasattr` fallbacks). Prefer explicit attributes and narrow APIs.
- Error handling: fail fast; no broad catch unless necessary. Never swallow exceptions silently.
- Naming: descriptive variables; functions as verbs; consistent snake_case.

### LLM Adapter Interface
- Standardized return type for hosted MCP adapters:
  - `LLMResponse { text: str, usage?: TokenUsage }`
  - `TokenUsage { input_tokens?: int, output_tokens?: int, total_tokens?: int }`
- OpenAI adapter fills `usage` from SDK `response.usage`.
- Anthropic adapter fills `usage` from `message.usage` and computes `total_tokens` when missing.
- Internal wrapper `infra/llm.call_llm` returns plain text for the app layer and logs token usage payload when present.

### Logging policy
- Standard library `logging` only. Library attaches a `NullHandler` by default to avoid unsolicited output.
- CLI configures structured JSON logging:
  - File: `<cache>/logs/<GHSA>.jsonl`
  - Console: JSON to stdout when invoked via CLI
  - Formatter: `shared/JSONFormatter` prints `{ level, logger, message, payload? }` only
- Aggregator middleware:
  - `infra/mcp/wiretap_logging.py` emits payload-wrapped entries:
    - Request: `payload={"type":"request", "method": ctx.method, "message": to_jsonable(ctx.message)}`
    - Response: `payload={"type":"response", "method": ctx.method, "result": to_jsonable(result)}`
  - Combine with FastMCP `LoggingMiddleware(include_payloads=True)` if you need extra low-level traces.
  - CLI also emits: `payload={"type":"log_file", "path": "<cache>/logs/<GHSA>.jsonl"}` at startup.

### Run-time logging payloads (Analyzer)
- All app logs put their data under `payload` for consistency:
  - `{"type":"ghsa_meta", ghsa, meta}`
  - `{"type":"repos_prepared", workdirs}`
  - `{"type":"diff_built", full_len, included_len, truncated}`
  - `{"type":"aggregator_started", local_url, mounted}`
  - `{"type":"tunnel_started", public_url}`
  - `{"type":"llm_input", provider, model, prompt_len, prompt}`
  - `{"type":"llm_output", raw_text_len, raw_text}`
  - `{"type":"llm_usage", provider, model, input_tokens, output_tokens, total_tokens}`
  - `{"type":"final_result", result}`

### File/Folder conventions
- Log files are named by GHSA id only: `<ghsa>.jsonl` under `<cache>/logs/`.
- MCP middleware lives under `infra/mcp/` and is wired in `aggregator.py`.

