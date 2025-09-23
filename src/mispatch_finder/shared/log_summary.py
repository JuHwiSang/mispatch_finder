from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List


@dataclass
class RunSummary:
    ghsa_id: str
    verdict: str = ""
    model: str = ""
    run_date: str = ""
    mcp_total_calls: int = 0
    mcp_tool_counts: Dict[str, int] = field(default_factory=dict)
    total_tokens: int = 0


def parse_log_file(fp: Path, verbose: bool = False) -> RunSummary:
    ghsa_id = fp.stem
    verdict = ""
    model = ""
    run_date = ""
    mcp_total_calls = 0
    mcp_tool_counts: Dict[str, int] = {}
    total_tokens = 0

    try:
        for line in fp.read_text(encoding="utf-8").splitlines():
            try:
                obj = json.loads(line)
            except Exception:
                continue

            msg = obj.get("message")
            if msg == "mcp_request":
                payload = obj.get("payload", {})
                # exclude inventory listing calls
                if payload.get("method") == "tools/list":
                    pass
                else:
                    mcp_total_calls += 1
                    if verbose:
                        try:
                            message = payload.get("message", {})
                            tool_name = message.get("name")
                            if tool_name:
                                mcp_tool_counts[tool_name] = mcp_tool_counts.get(tool_name, 0) + 1
                        except Exception:
                            pass

            elif msg == "llm_usage":
                try:
                    payload = obj.get("payload", {})
                    tokens = payload.get("total_tokens")
                    if isinstance(tokens, int):
                        total_tokens += tokens
                except Exception:
                    pass

            payload = obj.get("payload") or {}
            typ = payload.get("type") if isinstance(payload, dict) else None

            if typ == "run_started" and not run_date:
                # No timestamp in formatter; we will use file mtime as proxy later
                run_date = ""
                if not model:
                    model = payload.get("model") or model

            if typ == "final_result":
                res = payload.get("result") or {}
                raw_text = res.get("raw_text")
                if raw_text:
                    try:
                        j = json.loads(raw_text)
                        if isinstance(j, dict):
                            verdict = str(j.get("verdict") or "")
                    except (json.JSONDecodeError, TypeError):
                        pass
                m = res.get("model")
                if m:
                    model = str(m)
    except Exception:
        pass

    if not run_date:
        try:
            import datetime as _dt
            ts = fp.stat().st_mtime
            run_date = _dt.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            run_date = ""

    return RunSummary(
        ghsa_id=ghsa_id,
        verdict=verdict,
        model=model,
        run_date=run_date,
        mcp_total_calls=mcp_total_calls,
        mcp_tool_counts=mcp_tool_counts if verbose else {},
        total_tokens=total_tokens,
    )


def summarize_logs(logs_dir: Path, verbose: bool = False) -> Dict[str, RunSummary]:
    try:
        files = sorted([p for p in logs_dir.glob("*.jsonl") if p.is_file()])
    except FileNotFoundError:
        files = []

    # Parse, then sort by run_date descending (empty dates last)
    items: List[RunSummary] = []
    for fp in files:
        items.append(parse_log_file(fp, verbose=verbose))

    items.sort(key=lambda s: s.run_date or "", reverse=True)

    summaries: Dict[str, RunSummary] = {}
    for s in items:
        summaries[s.ghsa_id] = s
    return summaries


def format_summary_table(summaries: Dict[str, RunSummary], verbose: bool = False) -> List[str]:
    if not summaries:
        return ["No logs found."]

    rows: List[tuple[str, str, str, str, str, str, str]] = []
    for ghsa_id, s in summaries.items():
        mcp_details = ""
        if verbose and s.mcp_tool_counts:
            details = ", ".join(f"{k}: {v}" for k, v in sorted(s.mcp_tool_counts.items()))
            mcp_details = f"({details})"
        rows.append((
            ghsa_id,
            s.verdict,
            s.model,
            s.run_date,
            str(s.mcp_total_calls),
            str(s.total_tokens),
            mcp_details,
        ))

    ghsa_w = max(len(r[0]) for r in rows)
    verdict_w = max(7, max(len(r[1]) for r in rows))
    model_w = max(5, max(len(r[2]) for r in rows))
    mcp_w = max(9, max(len(r[4]) for r in rows))
    tokens_w = max(6, max(len(r[5]) for r in rows))

    header_parts = [
        'GHSA'.rjust(ghsa_w),
        'Verdict'.rjust(verdict_w),
        'Model'.rjust(model_w),
        'MCP Calls'.rjust(mcp_w),
        'Tokens'.rjust(tokens_w),
        'RunDate',
    ]
    if verbose:
        header_parts.append('MCP Details')

    lines: List[str] = ["  ".join(header_parts)]
    for ghsa_id, verdict, model, run_date, mcp_calls, tokens, mcp_details in rows:
        parts = [
            ghsa_id.rjust(ghsa_w),
            verdict.rjust(verdict_w),
            model.rjust(model_w),
            mcp_calls.rjust(mcp_w),
            tokens.rjust(tokens_w),
            run_date,
        ]
        if verbose and mcp_details:
            parts.append(mcp_details)
        lines.append("  ".join(parts))
    return lines


