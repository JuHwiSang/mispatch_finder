from __future__ import annotations

import json
import logging
import sys
import subprocess
from pathlib import Path
import os
import re

import typer

from .main import run_analysis, list_ghsa_ids, clear_all_caches, show_log
from .config import get_model_api_key, get_logs_dir
from ..shared.json_logging import build_json_console_handler, build_json_file_handler
from ..shared.log_summary import summarize_logs

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = typer.Typer(add_completion=False, no_args_is_help=True)


@app.command()
def run(
    ghsa: str = typer.Argument(..., help="GHSA identifier, e.g., GHSA-xxxx-xxxx-xxxx"),
    provider: str = typer.Option("openai", '--provider', case_sensitive=False, help="LLM provider"),
    model: str = typer.Option("gpt-5", '--model', help="Model name"),
    log_level: str = typer.Option("INFO", '--log-level', help="Log level", case_sensitive=False),
    force_reclone: bool = typer.Option(False, '--force-reclone', help="Force re-clone repo cache"),
):
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
    logging.getLogger(__name__).info("run_started", extra={"payload": {
        "type": "run_started",
        "ghsa": ghsa,
        "provider": provider,
        "model": model,
    }})

    # Resolve required secrets from env
    api_key = get_model_api_key()
    if not api_key:
        typer.echo("API key required via MODEL_API_KEY (or OPENAI_API_KEY/ANTHROPIC_API_KEY)", err=True)
        raise typer.Exit(code=2)

    from .config import get_github_token
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


@app.command()
def show():
    """List available GHSA identifiers."""
    items = list_ghsa_ids()
    typer.echo(json.dumps({"items": items}, ensure_ascii=False, indent=2))



@app.command()
def clear():
    """Clear local caches and CVE collector state."""
    typer.echo("Clearing caches...")
    clear_all_caches()
    typer.echo("Done.")


@app.command()
def log(
    ghsa: str = typer.Argument(None, help="Optional GHSA. If omitted, lists summaries of all runs."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed MCP call counts per tool."),
):
    """Print logs for a GHSA, or list summaries of all runs."""
    lines = show_log(ghsa, verbose)
    for line in lines:
        typer.echo(line)


@app.command()
def all(
    provider: str | None = typer.Option(None, "--provider", case_sensitive=False, help="LLM provider (optional)"),
    model: str | None = typer.Option(None, "--model", help="Model name (optional)"),
    limit: int | None = typer.Option(None, "--limit", "-n", help="Max number of IDs to run"),
):
    """Run analysis for GHSA IDs lacking a completed run."""
    items = list_ghsa_ids()

    logs_dir = get_logs_dir()
    summaries = summarize_logs(logs_dir, verbose=False)

    # Choose IDs to run
    to_run: list[str] = []
    for ghsa in items:
        s = summaries.get(ghsa)
        if s is not None and s.done:
            continue
        to_run.append(ghsa)
        if limit is not None and len(to_run) >= limit:
            break

    if not to_run:
        typer.echo("No pending GHSA IDs to run.")
        return

    # Run each analysis in a fresh subprocess to ensure clean state per run
    # (Original in-process call retained for reference)
    # for idx, ghsa in enumerate(to_run, start=1):
    #     typer.echo(f"[{idx}/{len(to_run)}] Running {ghsa} (provider={provider}, model={model})...")
    #     run(
    #         ghsa=ghsa,
    #         provider=provider,
    #         model=model,
    #         log_level="INFO",
    #         force_reclone=False,
    #     )

    src_dir = Path(__file__).resolve().parents[2]
    for idx, ghsa in enumerate(to_run, start=1):
        # Status line with optional provider/model context
        parts = [f"[{idx}/{len(to_run)}] Running {ghsa}"]
        if provider:
            parts.append(f"provider={provider}")
        if model:
            parts.append(f"model={model}")
        typer.echo(" " .join(parts) + " via subprocess...")

        # Build subprocess command; only pass flags that were provided
        cmd = [
            sys.executable,
            "-m",
            "mispatch_finder.app.cli",
            "run",
            ghsa,
        ]
        if provider:
            cmd.extend(["--provider", provider])
        if model:
            cmd.extend(["--model", model])
        result = subprocess.run(cmd, cwd=str(src_dir))
        if result.returncode != 0:
            typer.echo(f"Subprocess failed for {ghsa} with exit code {result.returncode}", err=True)
            raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
