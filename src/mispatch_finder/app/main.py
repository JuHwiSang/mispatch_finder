from __future__ import annotations

from typing import Dict

from .config import get_cache_dir, get_results_dir
from .models import AnalysisRequest
from ..core.analyze import Analyzer
from ..infra.store import save_result, load_result
from ..infra.store import list_results


def run_analysis(
    *,
    ghsa: str,
    provider: str,
    model: str,
    api_key: str,
    github_token: str,
    force_reclone: bool = False,
) -> Dict[str, object]:
    """High-level orchestration entrypoint (stub).

    This will:
      - fetch GHSA meta
      - prepare repos (pre/post)
      - start MCP + tunnel
      - call LLM via itdev_llm_adapter
      - persist and return a result dict
    """
    # Minimal orchestration wiring (stubbed external effects)
    results_dir = get_results_dir()
    req = AnalysisRequest(
        ghsa=ghsa,
        provider=provider,
        model=model,
        api_key=api_key,
        github_token=github_token,
        force_reclone=force_reclone,
    )
    analyzer = Analyzer()
    payload = analyzer.analyze(req)
    save_result(results_dir, ghsa, payload)
    return payload


def show_results(*, ghsa: str | None) -> Dict[str, object]:
    results_dir = get_results_dir()
    if ghsa:
        data = load_result(results_dir, ghsa)
        return data or {"ghsa": ghsa, "status": "not-found"}
    # List recent summaries
    return {"items": list_results(results_dir)}


