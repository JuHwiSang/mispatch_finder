from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class RunSummary:
    ghsa_id: str
    current_risk: str = ""
    patch_risk: str = ""
    reason: str = ""
    poc: str = ""
    model: str = ""
    run_date: str = ""
    mcp_total_calls: int = 0
    mcp_tool_counts: dict[str, int] = field(default_factory=dict)
    total_tokens: int = 0
    done: bool = False


@dataclass
class LogDetails:
    ghsa_id: str
    repo_url: str = ""
    commit: str = ""
    model: str = ""
    patch_risk: str = ""
    current_risk: str = ""
    reason: str = ""
    poc: str | None = None


def parse_log_details(fp: Path) -> LogDetails:
    """Parse a single JSONL log file and return concise details with fallbacks.

    Fallback rules:
    - repo_url/commit: from `ghsa_meta` payload when available; otherwise empty
    - risks: prefer `current_risk` then `patch_risk` from `final_result.result.raw_text` JSON
      - legacy: map `severity` to `patch_risk` when present
    - reason/poc: prefer `reason`/`poc`; legacy: `rationale`/`poc_idea`
    - model: from `run_started.payload.model` or `final_result.result.model`
    """
    details = LogDetails(ghsa_id=fp.stem)

    for line in fp.read_text(encoding="utf-8").splitlines():
        try:
            obj = json.loads(line)
        except Exception:
            continue

        msg = obj.get("message")
        payload = obj.get("payload") or {}

        # model (early from run_started or llm_input)
        if msg == "run_started":
            m = payload.get("model")
            if isinstance(m, str):
                details.model = details.model or m
        
        if msg == "llm_input":
            m = payload.get("model")
            if isinstance(m, str):
                details.model = details.model or m

        # ghsa meta (repo url / commit)
        if msg == "ghsa_meta":
            meta = payload.get("meta") or {}
            repo_url = meta.get("repo_url")
            commit = meta.get("commit")
            if isinstance(repo_url, str):
                details.repo_url = repo_url
            if isinstance(commit, str):
                details.commit = commit
            ghsa = payload.get("ghsa")
            if isinstance(ghsa, str):
                details.ghsa_id = ghsa

        # final result (risks and reasoning)
        if msg == "final_result":
            res = payload.get("result") or {}
            m = res.get("model")
            if isinstance(m, str):
                details.model = details.model or m
            raw_text = res.get("raw_text")
            if isinstance(raw_text, str) and raw_text.strip():
                j = None
                try:
                    j = json.loads(raw_text)
                except Exception:
                    j = None
                if isinstance(j, dict):
                    cur = j.get("current_risk")
                    pat = j.get("patch_risk")
                    if isinstance(cur, str) and not details.current_risk:
                        details.current_risk = cur
                    if isinstance(pat, str) and not details.patch_risk:
                        details.patch_risk = pat
                    reason = j.get("reason")
                    if isinstance(reason, str) and not details.reason:
                        details.reason = reason
                    poc = j.get("poc")
                    if isinstance(poc, str) and not details.poc:
                        details.poc = poc

                    # legacy fallbacks
                    if not details.patch_risk:
                        sev = j.get("severity")
                        if isinstance(sev, str):
                            details.patch_risk = sev
                    if not details.reason:
                        r = j.get("rationale")
                        if isinstance(r, str):
                            details.reason = r
                    if not details.poc:
                        pi = j.get("poc_idea")
                        if isinstance(pi, str):
                            details.poc = pi
    return details


def parse_log_file(fp: Path, verbose: bool = False) -> RunSummary:
    ghsa_id = fp.stem
    current_risk = ""
    patch_risk = ""
    reason = ""
    poc = ""
    model = ""
    run_date = ""
    mcp_total_calls = 0
    mcp_tool_counts: dict[str, int] = {}
    total_tokens = 0
    done = False

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
                    message = payload.get("message", {})
                    tool_name = message.get("name")
                    if tool_name:
                        mcp_tool_counts[tool_name] = mcp_tool_counts.get(tool_name, 0) + 1

        elif msg == "llm_usage":
            payload = obj.get("payload", {})
            tokens = payload.get("total_tokens")
            if isinstance(tokens, int):
                total_tokens += tokens

        payload = obj.get("payload") or {}
        typ = payload.get("type") if isinstance(payload, dict) else None

        if typ == "run_started" and not run_date:
            # No timestamp in formatter; we will use file mtime as proxy later
            run_date = ""
            if not model:
                model = payload.get("model") or model
        
        if typ == "llm_input":
            if not model:
                model = payload.get("model") or model

        if typ == "final_result":
            done = True
            res = payload.get("result") or {}
            raw_text = res.get("raw_text")
            if raw_text:
                try:
                    j = json.loads(raw_text)
                    if isinstance(j, dict):
                        cur = j.get("current_risk")
                        pat = j.get("patch_risk")
                        rsn = j.get("reason")
                        pc = j.get("poc")
                        if isinstance(cur, str):
                            current_risk = cur
                        if isinstance(pat, str):
                            patch_risk = pat
                        if isinstance(rsn, str):
                            reason = rsn
                        if isinstance(pc, str):
                            poc = pc
                        # legacy fallbacks
                        if not patch_risk:
                            sev = j.get("severity")
                            if isinstance(sev, str):
                                patch_risk = sev
                        if not reason:
                            r = j.get("rationale")
                            if isinstance(r, str):
                                reason = r
                        if not poc:
                            pi = j.get("poc_idea")
                            if isinstance(pi, str):
                                poc = pi
                except (json.JSONDecodeError, TypeError):
                    pass
            m = res.get("model")
            if m:
                model = str(m)
    if not run_date:
        import datetime as _dt
        ts = fp.stat().st_mtime
        run_date = _dt.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")

    return RunSummary(
        ghsa_id=ghsa_id,
        current_risk=current_risk,
        patch_risk=patch_risk,
        reason=reason,
        poc=poc,
        model=model,
        run_date=run_date,
        mcp_total_calls=mcp_total_calls,
        mcp_tool_counts=mcp_tool_counts if verbose else {},
        total_tokens=total_tokens,
        done=done,
    )


def summarize_logs(logs_dir: Path, verbose: bool = False) -> dict[str, RunSummary]:
    try:
        files = sorted([p for p in logs_dir.glob("*.jsonl") if p.is_file()])
    except FileNotFoundError:
        files = []

    # Parse, then sort by run_date descending (empty dates last)
    items: list[RunSummary] = []
    for fp in files:
        items.append(parse_log_file(fp, verbose=verbose))

    items.sort(key=lambda s: s.run_date or "", reverse=True)

    summaries: dict[str, RunSummary] = {}
    for s in items:
        summaries[s.ghsa_id] = s
    return summaries


def format_summary_table(summaries: dict[str, RunSummary], verbose: bool = False) -> list[str]:
    if not summaries:
        return ["No logs found."]

    rows: list[tuple[str, str, str, str, str, str, str, str]] = []
    for ghsa_id, s in summaries.items():
        mcp_details = ""
        if verbose and s.mcp_tool_counts:
            details = ", ".join(f"{k}: {v}" for k, v in sorted(s.mcp_tool_counts.items()))
            mcp_details = f"({details})"
        rows.append((
            ghsa_id,
            s.current_risk or "",
            s.patch_risk or "",
            s.model or "",
            s.run_date or "",
            str(s.mcp_total_calls),
            str(s.total_tokens),
            mcp_details,
        ))

    ghsa_w = max(len(r[0]) for r in rows)
    curr_w = max(7, max(len(r[1]) for r in rows))
    patch_w = max(5, max(len(r[2]) for r in rows))
    model_w = max(5, max(len(r[3]) for r in rows))
    mcp_w = max(9, max(len(r[5]) for r in rows))
    tokens_w = max(6, max(len(r[6]) for r in rows))

    header_parts = [
        'GHSA'.rjust(ghsa_w),
        'Current'.rjust(curr_w),
        'Patch'.rjust(patch_w),
        'Model'.rjust(model_w),
        'MCP Calls'.rjust(mcp_w),
        'Tokens'.rjust(tokens_w),
        'RunDate',
    ]
    if verbose:
        header_parts.append('MCP Details')

    lines: list[str] = ["  ".join(header_parts)]
    for ghsa_id, current_risk, patch_risk, model, run_date, mcp_calls, tokens, mcp_details in rows:
        parts = [
            ghsa_id.rjust(ghsa_w),
            (current_risk or '').rjust(curr_w),
            (patch_risk or '').rjust(patch_w),
            (model or '').rjust(model_w),
            mcp_calls.rjust(mcp_w),
            tokens.rjust(tokens_w),
            run_date,
        ]
        if verbose and mcp_details:
            parts.append(mcp_details)
        lines.append("  ".join(parts))
    return lines


def format_single_summary(details: LogDetails) -> list[str]:
    """Render a concise multi-line summary for a single run."""
    lines: list[str] = []
    lines.append(f"GHSA:   {details.ghsa_id}")
    if details.repo_url:
        lines.append(f"Repo:   {details.repo_url}")
    if details.commit:
        lines.append(f"Commit: {details.commit}")
    if details.model:
        lines.append(f"Model:  {details.model}")
    if details.patch_risk:
        lines.append(f"Patch Risk:   {details.patch_risk}")
    if details.current_risk:
        lines.append(f"Current Risk: {details.current_risk}")
    if details.reason:
        lines.append("Reason:")
        lines.append(details.reason)
    if details.poc:
        lines.append("PoC:")
        lines.append(details.poc)
    if not lines:
        lines.append("No summary available.")
    return lines


