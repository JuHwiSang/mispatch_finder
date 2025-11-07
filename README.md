# Mispatch Finder

> **Note: This project is currently under active development. Features and APIs may change.**

A security analysis tool that detects potential mispatch vulnerabilities in software patches by analyzing GitHub Security Advisories (GHSA).

## Overview

Mispatch Finder analyzes GHSA data to identify cases where security patches may have been incorrectly applied or missed entirely. It uses LLM-powered analysis with Model Context Protocol (MCP) servers to examine code diffs and assess patch quality.

## Prerequisites

- Python 3.13+
- SSH (for MCP tunneling)
- ripgrep (for repository analysis)
- GitHub Personal Access Token
- LLM API Key (OpenAI or Anthropic)

## Installation

### Using uv (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd mispatch_finder

# Install with uv
uv pip install -e .

# Or install with test dependencies
uv pip install -e ".[tests]"
```

### Using pip

```bash
pip install -e .
# Or with test dependencies
pip install -e ".[tests]"
```

### Using pipx (Standalone Installation)

```bash
pipx install git+<repository-url>
```

## Configuration

### Environment Variables

Create a `.env` file in the project root or set environment variables:

```bash
# Required
MISPATCH_FINDER_GITHUB__TOKEN=ghp_your_token_here
MISPATCH_FINDER_LLM__API_KEY=your_api_key_here

# Optional (with defaults shown)
MISPATCH_FINDER_LLM__PROVIDER_NAME=openai
MISPATCH_FINDER_LLM__MODEL_NAME=gpt-4o
MISPATCH_FINDER_VULNERABILITY__ECOSYSTEM=npm
MISPATCH_FINDER_VULNERABILITY__FILTER_EXPR="stars is not None and stars>=100 and size_bytes is not None and size_bytes<=10_000_000"
MISPATCH_FINDER_ANALYSIS__DIFF_MAX_CHARS=200000
MISPATCH_FINDER_ANALYSIS__MCP_PORT=18080
MISPATCH_FINDER_LOGGING__LEVEL=INFO
MISPATCH_FINDER_LOGGING__CONSOLE_OUTPUT=False
```

See [.env.example](.env.example) for a template.

### Configuration Details

- **GitHub Token**: Required for accessing GitHub Security Advisories and repository data
- **LLM API Key**: Required for analysis (supports OpenAI and Anthropic)
- **Provider**: Choose `openai` or `anthropic`
- **Model**: Model name (e.g., `gpt-4o`, `claude-sonnet-4`)
- **Ecosystem**: Default ecosystem filter (`npm`, `pypi`, `go`, etc.)
- **Filter Expression**: Python expression to filter vulnerabilities (e.g., `"stars >= 100"`)
- **Diff Max Chars**: Maximum characters in diff sent to LLM (default: 200,000)

## Usage

### Basic Commands

#### Analyze a Vulnerability

```bash
mispatch-finder analyze GHSA-xxxx-xxxx-xxxx
```

Options:
- `--provider`: LLM provider (`openai` or `anthropic`)
- `--model`: Model name (e.g., `gpt-4o`, `claude-sonnet-4`)
- `--force-reclone`: Force re-clone repositories

#### List Vulnerabilities

```bash
# List unanalyzed vulnerabilities (default)
mispatch-finder list

# Include already analyzed vulnerabilities
mispatch-finder list --include-analyzed

# Show detailed metadata
mispatch-finder list --detail

# Limit results
mispatch-finder list --limit 10

# Custom filter
mispatch-finder list --filter "severity == 'CRITICAL'"

# Disable default filter (show all)
mispatch-finder list --no-filter

# JSON output (for scripting)
mispatch-finder list --json
```

#### Batch Analysis

```bash
# Analyze up to 10 unanalyzed vulnerabilities
mispatch-finder batch --limit 10

# With custom filter
mispatch-finder batch --filter "severity == 'CRITICAL'" --limit 5

# Analyze all unanalyzed vulnerabilities
mispatch-finder batch --no-filter --limit 100
```

#### View Analysis Logs

```bash
# Summary of all analysis runs
mispatch-finder logs

# Detailed logs for specific vulnerability
mispatch-finder logs GHSA-xxxx-xxxx-xxxx --verbose
```

#### Display Analysis Prompt

```bash
# Show prompt that would be sent to LLM
mispatch-finder prompt GHSA-xxxx-xxxx-xxxx

# Save to file
mispatch-finder prompt GHSA-xxxx-xxxx-xxxx > prompt.txt

# Force re-clone repositories
mispatch-finder prompt GHSA-xxxx-xxxx-xxxx --force-reclone
```

#### MCP Server Mode

Start a standalone MCP server for interactive analysis:

```bash
# stdio mode (default) - for local MCP clients
mispatch-finder mcp GHSA-xxxx-xxxx-xxxx

# HTTP server mode - for remote access
mispatch-finder mcp GHSA-xxxx-xxxx-xxxx --mode streamable-http --port 18080

# HTTP with SSH tunnel and authentication
mispatch-finder mcp GHSA-xxxx-xxxx-xxxx --mode streamable-http --port 18080 --tunnel --auth
```

Options:
- `--mode`: Transport mode (`stdio` or `streamable-http`)
- `--port`: Port number (required for streamable-http)
- `--tunnel`: Enable SSH tunnel via localhost.run
- `--auth`: Enable authentication (generates random token)
- `--force-reclone`: Force re-clone repositories

#### Clear Caches

```bash
mispatch-finder clear
```

## Architecture

The project follows **Domain-Driven Design (DDD)** with clean architecture principles:

```
src/mispatch_finder/
├── app/                    # Application Layer (CLI, DI Container, Config)
├── core/                   # Core Domain Layer (Business Logic)
│   ├── domain/            # Domain Models & Entities
│   ├── services/          # Domain Services
│   ├── usecases/          # Use Cases
│   └── ports.py           # Port Interfaces
├── infra/                 # Infrastructure Layer (Adapters)
│   ├── llm_adapters/      # LLM Provider Adapters
│   ├── logging/           # Structured Logging
│   └── mcp/              # Model Context Protocol
└── shared/                # Shared Utilities
```

See [CLAUDE.md](CLAUDE.md) for detailed architecture documentation.

## Development

### Running Tests

```bash
# All tests
pytest tests/

# Core unit tests only
pytest tests/mispatch_finder/core/

# Integration tests
pytest tests/mispatch_finder/infra/

# E2E tests
pytest tests/mispatch_finder/app/
```

### Code Style

- Python 3.13+ syntax
- Modern type hints (`list[T]`, `str | None`)
- SOLID principles
- Dependency inversion via Ports and Adapters

## How It Works

1. **Fetch Vulnerability Data**: Retrieves GHSA metadata from GitHub and OSV databases
2. **Clone Repositories**: Clones both current (patched) and previous (vulnerable) versions
3. **Generate Diff**: Creates a diff between the two versions
4. **LLM Analysis**: Sends diff and metadata to LLM with MCP server access to repository files
5. **Risk Assessment**: LLM evaluates patch quality and identifies potential mispatches
6. **Store Results**: Saves analysis results and logs for later review

## Output

Analysis results are stored in:
- **Logs**: `~/.cache/mispatch-finder/logs/{ghsa_id}.jsonl` (structured JSONL format)
- **Repositories**: `~/.cache/mispatch-finder/repos/{owner}/{name}/`

## Troubleshooting

### Common Issues

1. **GitHub Rate Limiting**: Ensure your GitHub token has sufficient permissions
2. **LLM API Errors**: Check API key and model availability
3. **MCP Server Errors**: Ensure port is not already in use
4. **SSH Tunnel Failures**: Check SSH client installation and network connectivity

### Debug Mode

Enable verbose logging:

```bash
export MISPATCH_FINDER_LOGGING__LEVEL=DEBUG
export MISPATCH_FINDER_LOGGING__CONSOLE_OUTPUT=True
```

## Contributing

See [CLAUDE.md](CLAUDE.md) for development guidelines and architecture details.

## License

[Add license information]

## Related Projects

- [cve_collector](https://github.com/JuHwiSang/cve_collector) - Vulnerability data collection
- [repo_read_mcp](https://github.com/JuHwiSang/repo_read_mcp) - MCP server for repository reading
