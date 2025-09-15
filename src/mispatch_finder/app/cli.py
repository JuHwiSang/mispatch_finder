from __future__ import annotations

import json
import logging
import sys

import typer
from cve_collector import CVECollector

from .main import run_analysis
from .config import get_github_token, get_model_api_key, get_cache_dir
from ..shared.json_logging import build_json_console_handler, build_json_file_handler
from ..shared.rmtree_force import rmtree_force

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
    model: str = typer.Option(..., '--model', help="Model name"),
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
    logs_dir = get_cache_dir() / "logs"
    file_handler = build_json_file_handler(logs_dir / f"{ghsa}.jsonl", level=level)
    console_handler = build_json_console_handler(level=level)
    root.addHandler(file_handler)
    root.addHandler(console_handler)

    # Resolve required secrets
    if not model:
        typer.echo("--model is required", err=True)
        raise typer.Exit(code=2)

    resolved_api_key = get_model_api_key()
    if not resolved_api_key:
        typer.echo("API key is required via environment variable", err=True)
        raise typer.Exit(code=2)

    resolved_github = get_github_token()
    if not resolved_github:
        typer.echo("GitHub token is required via environment variable (GITHUB_TOKEN)", err=True)
        raise typer.Exit(code=2)

    result = run_analysis(
        ghsa=ghsa,
        provider=provider,
        model=model,
        api_key=resolved_api_key,
        github_token=resolved_github,
        force_reclone=force_reclone,
    )
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))


@app.command()
def show():
    """List available GHSA identifiers from CVECollector."""
    token = get_github_token()
    if not token:
        typer.echo("GitHub token is required (env GITHUB_TOKEN)", err=True)
        raise typer.Exit(code=2)
    collector = CVECollector(github_token=token)
    items = collector.collect_identifiers()
    typer.echo(json.dumps({"items": items}, ensure_ascii=False, indent=2))



@app.command()
def clear():
    """Clear local caches/results and CVE collector state."""
    # Remove application cache directory (includes results, repos, worktrees)
    typer.echo("Clearing local caches/results and CVE collector state...")
    
    cache_dir = get_cache_dir()
    removed = []
    errors: list[str] = []
    try:
        rmtree_force(cache_dir)
        removed.append(str(cache_dir))
    except Exception as e:
        errors.append(f"cache_dir: {e}")

    # Clear CVE collector's local state
    try:
        CVECollector.clear_local_state()
    except Exception as e:
        errors.append(f"cve_collector: {e}")

    typer.echo("Cleared local caches/results and CVE collector state.")


@app.command()
def log(ghsa: str = typer.Argument(..., help="GHSA identifier, e.g., GHSA-xxxx-xxxx-xxxx")):
    """Print structured log lines for a GHSA run (from <cache>/logs/<GHSA>.jsonl)."""
    logs_dir = get_cache_dir() / "logs"
    log_fp = logs_dir / f"{ghsa}.jsonl"
    if not log_fp.exists():
        typer.echo(f"Log file not found: {log_fp}", err=True)
        raise typer.Exit(code=2)
    try:
        for line in log_fp.read_text(encoding="utf-8").splitlines():
            typer.echo(line)
    except Exception as e:
        typer.echo(f"Failed to read log file: {e}", err=True)
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()


