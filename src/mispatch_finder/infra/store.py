from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional


def save_result(results_dir: Path, ghsa: str, payload: dict[str, Any]) -> None:
    fp = results_dir / f"{ghsa}.json"
    fp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_result(results_dir: Path, ghsa: str) -> Optional[dict[str, Any]]:
    fp = results_dir / f"{ghsa}.json"
    if not fp.exists():
        return None
    return json.loads(fp.read_text(encoding="utf-8"))


def list_results(results_dir: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if not results_dir.exists():
        return items
    for fp in sorted(results_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        # Prefer current_risk.verdict, then patch_risk.verdict, else legacy verdict/status
        summary: str = ""
        cur = data.get("current_risk") if isinstance(data, dict) else None
        if isinstance(cur, dict):
            summary = str(cur.get("verdict") or "")
        if not summary:
            pat = data.get("patch_risk") if isinstance(data, dict) else None
            if isinstance(pat, dict):
                summary = str(pat.get("verdict") or "")
        if not summary and isinstance(data, dict):
            summary = str(data.get("verdict") or data.get("status") or "")

        items.append({
            "ghsa": fp.stem,
            "mtime": fp.stat().st_mtime,
            "summary": summary,
        })
    return items


