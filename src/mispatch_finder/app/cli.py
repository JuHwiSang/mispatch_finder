from __future__ import annotations

import json
import logging
import sys
import subprocess
from pathlib import Path
import os
import re

import typer

from .main import run_analysis, list_ghsa_ids, list_ghsa_with_metadata, clear_all_caches, logs as logs_main
from .config import get_model_api_key, get_logs_dir, get_github_token
from ..infra.logging import build_json_console_handler, build_json_file_handler
from ..shared.log_summary import summarize_logs
from cve_collector import detail

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
    # structured logging: file + console
    level = logging._nameToLevel.get(log_level.upper(), logging.INFO)
    root = logging.getLogger()
    root.setLevel(level)
    # remove existing handlers to avoid duplication in reruns
    for h in list(root.handlers):
        root.removeHandler(h)
    logs_dir = get_logs_dir()
    log_file = logs_dir / f"{ghsa}.jsonl"
    if log_file.exists():
        log_file.unlink()
    file_handler = build_json_file_handler(log_file, level=level)
    console_handler = build_json_console_handler(level=level)
    root.addHandler(file_handler)
    root.addHandler(console_handler)
    logging.getLogger(__name__).info("log_file", extra={"payload": {"type": "log_file", "path": str(log_file)}})
    logging.getLogger(__name__).info("analysis_started", extra={"payload": {
        "type": "analysis_started",
        "ghsa": ghsa,
        "provider": provider,
        "model": model,
    }})

    # Resolve required secrets from env
    api_key = get_model_api_key()
    if not api_key:
        typer.echo("API key required via MODEL_API_KEY (or OPENAI_API_KEY/ANTHROPIC_API_KEY)", err=True)
        raise typer.Exit(code=2)

    github_token = get_github_token()
    if not github_token:
        typer.echo("GitHub token required via GITHUB_TOKEN", err=True)
        raise typer.Exit(code=2)

    result = run_analysis(
        ghsa=ghsa,
        provider=provider,
        model=model,
        api_key=api_key,
        github_token=github_token,
        force_reclone=force_reclone,
    )
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))


@app.command(name="list")
def list_command():
    """List available GHSA identifiers from vulnerability database."""
    items = list_ghsa_ids()
    typer.echo(json.dumps({"items": items}, ensure_ascii=False, indent=2))



@app.command()
def clear():
    """Clear local caches and CVE collector state."""
    typer.echo("Clearing caches...")
    clear_all_caches()
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
):
    """Run batch analysis for all pending GHSA identifiers."""
    items = list_ghsa_ids()

    logs_dir = get_logs_dir()
    summaries = summarize_logs(logs_dir, verbose=False)

    # Filter out already completed IDs
    candidates = []
    for ghsa in items:
        s = summaries.get(ghsa)
        if s is None or not s.done:
            candidates.append(ghsa)

    if not candidates:
        typer.echo("No pending GHSA IDs to run.")
        return

    typer.echo(f"Found {len(candidates)} pending GHSA IDs. Starting validation and batch analysis...")
    if limit:
        typer.echo(f"Target: {limit} successful runs")

    src_dir = Path(__file__).resolve().parents[2]

    processed = 0
    skipped = 0

    for candidate_idx, ghsa in enumerate(candidates, start=1):
        # Check if we've reached the limit
        if limit and processed >= limit:
            break

        # Lazy validation: check metadata only when needed
        typer.echo(f"[{candidate_idx}/{len(candidates)}] Validating {ghsa}...", nl=False)
        vuln = detail(ghsa)

        if vuln is None:
            typer.echo(f" ⊘ Skip (metadata not found)")
            skipped += 1
            continue

        if not vuln.repositories or len(vuln.repositories) == 0:
            typer.echo(f" ⊘ Skip (no repository)")
            skipped += 1
            continue

        if not vuln.commits or len(vuln.commits) == 0:
            typer.echo(f" ⊘ Skip (no commits)")
            skipped += 1
            continue

        # Valid metadata - run analysis
        typer.echo(f" ✓ Valid, running...")

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
            "analyze",  # Changed from "run" to "analyze"
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
