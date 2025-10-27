from __future__ import annotations

import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import cast

import typer

from .config import get_github_token, get_logs_dir, get_model_api_key
from .main import analyze as analyze_main, clear, list_vulnerabilities, logs as logs_main
from ..core.domain.models import Vulnerability
from ..shared.log_summary import summarize_logs

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
):
    """Analyze a single GHSA vulnerability for potential mispatches."""
    # Configure basic logging for internal debugging
    level = logging._nameToLevel.get(log_level.upper(), logging.INFO)
    logging.basicConfig(level=level, format='%(levelname)s: %(message)s', force=True)

    # User-facing status messages via typer.echo
    logs_dir = get_logs_dir()
    log_file = logs_dir / f"{ghsa}.jsonl"
    if log_file.exists():
        log_file.unlink()

    typer.echo(f"Starting analysis: {ghsa}")
    typer.echo(f"Provider: {provider}, Model: {model}")
    typer.echo(f"Log file: {log_file}")

    # Resolve required secrets from env
    api_key = get_model_api_key()
    if not api_key:
        typer.echo("Error: API key required via MODEL_API_KEY (or OPENAI_API_KEY/ANTHROPIC_API_KEY)", err=True)
        raise typer.Exit(code=2)

    github_token = get_github_token()
    if not github_token:
        typer.echo("Error: GitHub token required via GITHUB_TOKEN", err=True)
        raise typer.Exit(code=2)

    result = analyze_main(
        ghsa=ghsa,
        provider=provider,
        model=model,
        api_key=api_key,
        github_token=github_token,
        force_reclone=force_reclone,
    )
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))


@app.command(name="list")
def list_command(
    detailed: bool = typer.Option(False, "--detailed", "-d", help="Show detailed vulnerability information"),
    filter_expr: str | None = typer.Option(None, "--filter", "-f", help="Filter expression (use empty string '' to disable default filter)"),
    no_filter: bool = typer.Option(False, "--no-filter", help="Disable default filter (show all vulnerabilities)"),
):
    """List available vulnerabilities from the database.

    By default, shows only GHSA IDs with default filter applied (stars>=100, size<=10MB).
    Use --detailed to include full metadata.
    Use --filter to override the default filter (e.g., 'stars > 1000 and severity == "CRITICAL"').
    Use --no-filter to disable filtering entirely and show all vulnerabilities.
    """
    # Handle filter logic: explicit filter > no_filter flag > default
    if no_filter:
        final_filter = ""
    elif filter_expr is not None:
        final_filter = filter_expr
    else:
        final_filter = None  # Use config default

    result = list_vulnerabilities(detailed=detailed, filter_expr=final_filter)

    if not detailed:
        # Simple list of IDs
        typer.echo(json.dumps({"items": result}, ensure_ascii=False, indent=2))
    else:
        # Detailed vulnerability information
        vulns = cast(list[Vulnerability], result)

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



@app.command(name="clear")
def clear_command():
    """Clear local caches and CVE collector state."""
    typer.echo("Clearing caches...")
    clear()
    typer.echo("Done.")


@app.command()
def logs(
    ghsa: str = typer.Argument(None, help="Optional GHSA. If omitted, lists summaries of all runs."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed MCP call counts per tool."),
):
    """Show analysis logs - either for a specific GHSA or summary of all runs."""
    lines = logs_main(ghsa, verbose)
    for line in lines:
        typer.echo(line)


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
    # Handle filter logic
    if no_filter:
        final_filter = ""
    elif filter_expr is not None:
        final_filter = filter_expr
    else:
        final_filter = None  # Use config default

    # Fetch all vulnerabilities with detailed metadata (efficient single call)
    typer.echo("Fetching vulnerability list with metadata...")
    result = list_vulnerabilities(detailed=True, filter_expr=final_filter)
    vulns = cast(list[Vulnerability], result)

    logs_dir = get_logs_dir()
    summaries = summarize_logs(logs_dir, verbose=False)

    # Filter out already completed IDs
    candidates = []
    for vuln in vulns:
        ghsa = vuln.ghsa_id
        s = summaries.get(ghsa)
        if s is None or not s.done:
            candidates.append(vuln)

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


if __name__ == "__main__":
    app()
