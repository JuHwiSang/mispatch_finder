from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional, List


def save_result(results_dir: Path, ghsa: str, payload: Dict[str, object]) -> None:
    fp = results_dir / f"{ghsa}.json"
    fp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_result(results_dir: Path, ghsa: str) -> Optional[Dict[str, object]]:
    fp = results_dir / f"{ghsa}.json"
    if not fp.exists():
        return None
    return json.loads(fp.read_text(encoding="utf-8"))


def list_results(results_dir: Path) -> List[Dict[str, object]]:
    items: List[Dict[str, object]] = []
    if not results_dir.exists():
        return items
    for fp in sorted(results_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        items.append({
            "ghsa": fp.stem,
            "mtime": fp.stat().st_mtime,
            "summary": data.get("verdict") or data.get("status") or "",
        })
    return items


