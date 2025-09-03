from __future__ import annotations

import json
import logging
import sys

import typer
from cve_collector import CVECollector

from .main import run_analysis
from .config import get_github_token, get_openai_key, get_anthropic_key, get_cache_dir
from ..shared.rmtree_force import rmtree_force


app = typer.Typer(add_completion=False, no_args_is_help=True)


@app.command()
def run(
    ghsa: str = typer.Argument(..., help="GHSA identifier, e.g., GHSA-xxxx-xxxx-xxxx"),
    provider: str = typer.Option("openai", '--provider', case_sensitive=False, help="LLM provider"),
    model: str = typer.Option(..., '--model', help="Model name"),
    api_key: str | None = typer.Option(None, '--api-key', help="Provider API key (fallback env)"),
    github_token: str | None = typer.Option(None, '--github-token', help="GitHub token (fallback env)"),
    log_level: str = typer.Option("INFO", '--log-level', help="Log level", case_sensitive=False),
    force_reclone: bool = typer.Option(False, '--force-reclone', help="Force re-clone repo cache"),
):
    logging.basicConfig(level=getattr(logging, log_level.upper(), logging.INFO))

    # Resolve required secrets
    if not model:
        typer.echo("--model is required", err=True)
        raise typer.Exit(code=2)

    resolved_api_key = api_key or (get_openai_key() if provider == "openai" else get_anthropic_key())
    if not resolved_api_key:
        typer.echo("API key is required (flag or environment variable)", err=True)
        raise typer.Exit(code=2)

    resolved_github = github_token or get_github_token()
    if not resolved_github:
        typer.echo("GitHub token is required (flag or environment variable)", err=True)
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


if __name__ == "__main__":
    app()


