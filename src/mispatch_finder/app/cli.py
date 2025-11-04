from __future__ import annotations

import json
import logging
import signal
import subprocess
import sys
import time
from pathlib import Path

import typer

from .config import AppConfig
from .container import Container
from .cli_formatter import format_analyze_result, format_vulnerability_list
from ..core.domain.exceptions import GHSANotFoundError
from ..core.domain.models import Vulnerability
from ..core.usecases.mcp import MCPUseCase
from ..infra.llm import LLM
from ..infra.mcp_server import MCPServer

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = typer.Typer(add_completion=False, no_args_is_help=True)


@app.command()
def analyze(
    ghsa: str = typer.Argument(..., help="GHSA identifier, e.g., GHSA-xxxx-xxxx-xxxx"),
    provider: str = typer.Option("openai", '--provider', case_sensitive=False, help="LLM provider"),
    model: str = typer.Option("gpt-5", '--model', help="Model name"),
    log_level: str = typer.Option("INFO", '--log-level', help="Log level", case_sensitive=False),
    force_reclone: bool = typer.Option(False, '--force-reclone', help="Force re-clone repo cache"),
    json_output: bool = typer.Option(False, '--json', help="Output result as JSON"),
):
    """Analyze a single GHSA vulnerability for potential mispatches."""
    # Configure basic logging for internal debugging
    level = logging._nameToLevel.get(log_level.upper(), logging.INFO)
    logging.basicConfig(level=level, format='%(levelname)s: %(message)s', force=True)

    # Load config from environment variables
    config = AppConfig()

    # Set runtime GHSA for logger configuration
    config.runtime.ghsa = ghsa
    config.logging.console_output = True  # Enable console output in CLI

    # User-facing status messages
    log_file = config.directories.logs_dir / f"{ghsa}.jsonl"
    if log_file.exists():
        log_file.unlink()

    typer.echo(f"Starting analysis: {ghsa}")
    typer.echo(f"Provider: {provider}, Model: {model}")
    typer.echo(f"Log file: {log_file}")

    # Validate required secrets
    if not config.llm.api_key:
        typer.echo("Error: API key required via MISPATCH_FINDER_LLM__API_KEY", err=True)
        raise typer.Exit(code=2)

    if not config.github.token:
        typer.echo("Error: GitHub token required via MISPATCH_FINDER_GITHUB__TOKEN", err=True)
        raise typer.Exit(code=2)

    # Create container and execute
    container = Container()
    container.config.from_pydantic(config)
    container.init_resources()

    # Override LLM config with CLI params
    if provider or model:
        llm = LLM(
            provider=provider,
            model=model,
            api_key=config.llm.api_key,
            logger=container.logger(),
        )
        orchestrator = container.analysis_orchestrator()
        orchestrator._llm = llm

    # Execute use case
    uc = container.analyze_uc()
    try:
        result = uc.execute(ghsa=ghsa, force_reclone=force_reclone)

        # Output in requested format
        if json_output:
            # Convert AnalysisResult to dict for JSON serialization
            result_dict = {
                "ghsa": result.ghsa,
                "provider": result.provider,
                "model": result.model,
                "verdict": result.verdict,
                "severity": result.severity,
                "rationale": result.rationale,
                "evidence": result.evidence,
                "poc_idea": result.poc_idea,
                "raw_text": result.raw_text,
            }
            typer.echo(json.dumps(result_dict, ensure_ascii=False, indent=2))
        else:
            typer.echo(format_analyze_result(result))

    except GHSANotFoundError as e:
        # GHSA doesn't exist - clean up log file to avoid clutter
        container.shutdown_resources()
        if log_file.exists():
            log_file.unlink()
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)

    finally:
        # Always shutdown resources to close file handles
        container.shutdown_resources()


@app.command(name="list")
def list_command(
    detail: bool = typer.Option(False, "--detail", "-d", help="Show detailed vulnerability information"),
    filter_expr: str | None = typer.Option(None, "--filter", "-f", help="Filter expression (use empty string '' to disable default filter)"),
    no_filter: bool = typer.Option(False, "--no-filter", help="Disable default filter (show all vulnerabilities)"),
    include_analyzed: bool = typer.Option(False, "--include-analyzed", "-i", help="Include already analyzed vulnerabilities"),
    limit: int | None = typer.Option(None, "--limit", "-n", help="Limit number of results"),
    json_output: bool = typer.Option(False, "--json", help="Output result as JSON"),
):
    """List available vulnerabilities from the database.

    By default, shows only unanalyzed GHSA IDs with default filter applied (stars>=100, size<=10MB).
    Use --include-analyzed to include already analyzed vulnerabilities.
    Use --detail to include full metadata.
    Use --filter to override the default filter (e.g., 'stars > 1000 and severity == "CRITICAL"').
    Use --no-filter to disable filtering entirely and show all vulnerabilities.
    Use --limit to restrict the number of results.
    """
    # Create container
    config = AppConfig()
    container = Container()
    container.config.from_pydantic(config)
    container.init_resources()

    # Handle filter: None = use default, "" = no filter, otherwise = custom
    if no_filter:
        actual_filter = None
    elif filter_expr is not None:
        actual_filter = None if filter_expr == "" else filter_expr
    else:
        actual_filter = container.config.vulnerability.filter_expr()

    # Execute use case (business logic is now in UseCase)
    uc = container.list_uc()
    items = uc.execute(
        limit=limit,
        ecosystem=container.config.vulnerability.ecosystem(),
        detailed=detail,
        filter_expr=actual_filter,
        include_analyzed=include_analyzed,
    )

    # Output results
    if not detail:
        # Execute with detailed=False -> returns list[str]
        ghsa_ids: list[str] = uc.execute(
            limit=10,
            ecosystem=container.config.vulnerability.ecosystem(),
            detailed=False,
            filter_expr=actual_filter,
        )  # type: ignore[assignment]

        # Output in requested format
        if json_output:
            typer.echo(json.dumps({"items": ghsa_ids}, ensure_ascii=False, indent=2))
        else:
            typer.echo(format_vulnerability_list(ghsa_ids=ghsa_ids))
    else:
        # items is list[Vulnerability]
        vulns: list[Vulnerability] = items  # type: ignore[assignment]

        # Output in requested format
        if json_output:
            # Convert to JSON-serializable format
            items = []
            for v in vulns:
                items.append({
                    "ghsa_id": v.ghsa_id,
                    "cve_id": v.cve_id,
                    "severity": v.severity,
                    "summary": v.summary,
                    "repository": {
                        "owner": v.repository.owner,
                        "name": v.repository.name,
                        "ecosystem": v.repository.ecosystem,
                        "stars": v.repository.star_count,
                        "size_kb": v.repository.size_kb,
                    },
                    "commit_hash": v.commit_hash,
                })
            typer.echo(json.dumps({"count": len(items), "vulnerabilities": items}, ensure_ascii=False, indent=2))
        else:
            typer.echo(format_vulnerability_list(vulnerabilities=vulns))



# TODO: Re-enable after properly defining clear semantics and fixing resource conflicts
# Currently disabled due to:
# 1. Resource conflict: cve_collector client holds cache_dir lock
# 2. Unclear semantics: need to define what to clear (vuln_data cache, repo cache, results, logs?)
# @app.command(name="clear")
# def clear_command():
#     """Clear local caches and CVE collector state."""
#     typer.echo("Clearing caches...")
#
#     # Create container and execute
#     config = AppConfig()
#     container = Container()
#     container.config.from_pydantic(config)
#     container.init_resources()
#
#     uc = container.clear_cache_uc()
#     uc.execute()
#
#     typer.echo("Done.")


@app.command()
def logs(
    ghsa: str = typer.Argument(None, help="Optional GHSA. If omitted, lists summaries of all runs."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed MCP call counts per tool."),
):
    """Show analysis logs - either for a specific GHSA or summary of all runs."""
    # Create container and execute
    config = AppConfig()
    container = Container()
    container.config.from_pydantic(config)
    container.init_resources()

    uc = container.logs_uc()
    lines = uc.execute(ghsa, verbose)

    for line in lines:
        typer.echo(line)


@app.command()
def prompt(
    ghsa: str = typer.Argument(..., help="GHSA identifier, e.g., GHSA-xxxx-xxxx-xxxx"),
    force_reclone: bool = typer.Option(False, '--force-reclone', help="Force re-clone repo cache"),
):
    """Display the raw analysis prompt for a given GHSA."""
    # Create container and execute
    config = AppConfig()
    container = Container()
    container.config.from_pydantic(config)
    container.init_resources()

    try:
        uc = container.prompt_uc()
        prompt_text = uc.execute(ghsa=ghsa, force_reclone=force_reclone)
        typer.echo(prompt_text)
    except GHSANotFoundError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)
    finally:
        container.shutdown_resources()


@app.command()
def batch(
    provider: str | None = typer.Option(None, "--provider", case_sensitive=False, help="LLM provider (optional)"),
    model: str | None = typer.Option(None, "--model", help="Model name (optional)"),
    limit: int | None = typer.Option(None, "--limit", "-n", help="Max number of successful analyses to run"),
    filter_expr: str | None = typer.Option(None, "--filter", "-f", help="Filter expression (overrides default)"),
    no_filter: bool = typer.Option(False, "--no-filter", help="Disable default filter"),
):
    """Run batch analysis for pending vulnerabilities.

    By default, applies filter (stars>=100, size<=10MB) to focus on relevant repos.
    Use --filter to specify custom criteria or --no-filter to process all vulnerabilities.

    Examples:
      mispatch-finder batch --limit 10                           # Process 10 filtered vulnerabilities
      mispatch-finder batch --filter "severity == 'CRITICAL'"   # Only critical severity
      mispatch-finder batch --no-filter --limit 100              # Process all, up to 100
    """
    # Fetch all vulnerabilities with detailed metadata (efficient single call)
    typer.echo("Fetching vulnerability list with metadata...")

    # Create container
    config = AppConfig()
    container = Container()
    container.config.from_pydantic(config)
    container.init_resources()

    # Handle filter
    if no_filter:
        actual_filter = None
    elif filter_expr is not None:
        actual_filter = None if filter_expr == "" else filter_expr
    else:
        actual_filter = container.config.vulnerability.filter_expr()

    # Fetch pending vulnerabilities (business logic is now in UseCase)
    uc = container.list_uc()
    candidates: list[Vulnerability] = uc.execute(
        limit=limit,
        ecosystem=container.config.vulnerability.ecosystem(),
        detailed=True,
        filter_expr=actual_filter,
        include_analyzed=False,  # Only fetch pending (not yet analyzed)
    )  # type: ignore[assignment]

    if not candidates:
        typer.echo("No pending GHSA IDs to run.")
        return

    typer.echo(f"Found {len(candidates)} pending vulnerabilities. Starting batch analysis...")
    if limit:
        typer.echo(f"Target: {limit} successful runs")

    src_dir = Path(__file__).resolve().parents[2]

    processed = 0
    skipped = 0

    for candidate_idx, vuln in enumerate(candidates, start=1):
        # Check if we've reached the limit
        if limit and processed >= limit:
            break

        ghsa = vuln.ghsa_id
        typer.echo(f"[{candidate_idx}/{len(candidates)}] {ghsa} - {vuln.repository.owner}/{vuln.repository.name}")

        # Status line with optional provider/model context
        parts = [f"  Running {ghsa}"]
        if provider:
            parts.append(f"provider={provider}")
        if model:
            parts.append(f"model={model}")
        typer.echo(" ".join(parts))

        # Build subprocess command
        cmd = [
            sys.executable,
            "-m",
            "mispatch_finder.app.cli",
            "analyze",
            ghsa,
        ]
        if provider:
            cmd.extend(["--provider", provider])
        if model:
            cmd.extend(["--model", model])

        # Suppress stdout, keep stderr for errors
        result = subprocess.run(
            cmd,
            cwd=str(src_dir),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True
        )

        if result.returncode != 0:
            typer.echo(f"  ✗ Failed with exit code {result.returncode}", err=True)
            if result.stderr:
                typer.echo(result.stderr, err=True)
            raise typer.Exit(code=1)
        else:
            typer.echo(f"  ✓ Completed")
            processed += 1

    typer.echo(f"\nBatch analysis complete: {processed} processed, {skipped} skipped.")


@app.command()
def mcp(
    ghsa: str = typer.Argument(..., help="GitHub Security Advisory ID (e.g., GHSA-xxxx-xxxx-xxxx)"),
    mode: str = typer.Option("stdio", "--mode", "-m", help="Transport mode: 'stdio' or 'streamable-http'"),
    port: int | None = typer.Option(None, "--port", "-p", help="Port number (required for streamable-http)"),
    tunnel: bool = typer.Option(False, "--tunnel", "-t", help="Enable SSH tunnel (only for streamable-http)"),
    auth: bool = typer.Option(False, "--auth", "-a", help="Enable authentication (generates random token)"),
    force_reclone: bool = typer.Option(False, "--force-reclone", help="Force re-clone of repositories"),
):
    """Start a standalone MCP server for a specific vulnerability.

    Prepares repository workdirs from the GHSA ID and starts an MCP server.

    TRANSPORT MODES:
      stdio           - Direct communication via stdin/stdout (default)
      streamable-http - HTTP server (requires --port)

    STREAMABLE-HTTP OPTIONS:
      --port       - Port number (required)
      --tunnel     - Expose via SSH tunnel
      --auth       - Enable token authentication

    Examples:
      mispatch-finder mcp GHSA-xxxx-xxxx-xxxx                           # stdio mode (default)
      mispatch-finder mcp GHSA-xxxx-xxxx-xxxx --mode streamable-http --port 18080
      mispatch-finder mcp GHSA-xxxx-xxxx-xxxx --mode streamable-http --port 18080 --tunnel --auth
    """
    # Validate mode
    if mode not in ("stdio", "streamable-http"):
        typer.echo(f"Error: Invalid mode '{mode}'. Must be 'stdio' or 'streamable-http'.", err=True)
        raise typer.Exit(code=1)

    # For streamable-http, port is required
    if mode == "streamable-http" and port is None:
        typer.echo("Error: --port is required for streamable-http mode.", err=True)
        raise typer.Exit(code=1)

    # For stdio, ignore port/tunnel options
    if mode == "stdio":
        if port is not None:
            typer.echo("Warning: --port is ignored in stdio mode.", err=True)
        if tunnel:
            typer.echo("Warning: --tunnel is ignored in stdio mode.", err=True)

    # Create container
    config = AppConfig()
    container = Container()
    container.config.from_pydantic(config)
    container.init_resources()

    # Create MCP server
    mcp_server = MCPServer(logger=container.logger())

    # Execute use case
    uc = MCPUseCase(
        mcp_server=mcp_server,
        vuln_data=container.vuln_data(),
        repo=container.repo(),
        token_gen=container.token_gen(),
    )

    # Display startup info (only for streamable-http)
    if mode == "streamable-http":
        typer.echo(f"Preparing repositories for {ghsa}...")
        typer.echo(f"Starting MCP server on port {port}...")
        typer.echo(f"Tunnel: {'enabled' if tunnel else 'disabled'}")
        typer.echo(f"Authentication: {'enabled' if auth else 'disabled'}")

    try:
        result = uc.execute(
            ghsa=ghsa,
            transport=mode,
            port=port,
            use_tunnel=tunnel,
            use_auth=auth,
            force_reclone=force_reclone,
        )

        # For streamable-http, display server info
        if mode == "streamable-http":
            typer.echo("\n" + "=" * 60)
            typer.echo("MCP Server Started Successfully")
            typer.echo("=" * 60)
            typer.echo(f"Transport: {result['transport']}")
            typer.echo(f"Local URL:  {result['local_url']}")

            if result["public_url"]:
                typer.echo(f"Public URL: {result['public_url']}")

            if result["auth_token"]:
                typer.echo(f"\nAuthentication Token:")
                typer.echo(f"  {result['auth_token']}")

            typer.echo("\nPress Ctrl+C to stop the server...")
            typer.echo("=" * 60)

            # Keep the server running
            def signal_handler(sig, frame):  # noqa: ARG001
                typer.echo("\n\nShutting down MCP server...")
                container.shutdown_resources()
                raise typer.Exit(code=0)

            signal.signal(signal.SIGINT, signal_handler)

        # Keep alive
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        typer.echo("\n\nShutting down MCP server...")
        container.shutdown_resources()
        raise typer.Exit(code=0)
    except Exception as e:
        typer.echo(f"Error starting MCP server: {e}", err=True)
        container.shutdown_resources()
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
