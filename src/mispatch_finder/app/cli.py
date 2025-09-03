from __future__ import annotations

import json
import logging
import sys

import typer

from .main import run_analysis, show_results
from .config import get_github_token, get_openai_key, get_anthropic_key


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
def show(
    ghsa: str | None = typer.Option(None, '--ghsa', help="GHSA to show"),
):
    payload = show_results(ghsa=ghsa)
    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    app()


