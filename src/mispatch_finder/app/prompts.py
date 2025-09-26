from __future__ import annotations

from typing import Dict


def build_prompt(ghsa: str, meta: Dict[str, str], has_previous: bool, has_current: bool, *, diff_text: str = "") -> str:
    repo_url = meta.get("repo_url", "")
    commit = meta.get("commit", "")
    previous_note = "available" if has_previous else "unavailable (no parent commit)"
    current_note = "available" if has_current else "unavailable"

    body = (
        f"You are a security reviewer assessing patch correctness for GHSA {ghsa}.\n"
        f"Repository: {repo_url}\n"
        f"Patched commit: {commit}\n"
        f"Previous-state tools: {previous_note}; Current-state tools: {current_note}.\n\n"
        "Available tools are read-only repository tools for both states.\n"
        "Use 'previous' to inspect code prior to the patched commit (its parent). Use 'current' strictly for the repository's present HEAD (today's codebase).\n\n"
        "Task:\n"
        "1) Rate whether the patch was adequate (from the 'previous' state perspective).\n"
        "2) Rate whether the current repository still has a risk.\n"
        "3) Provide a succinct PoC (prefer code; steps acceptable).\n\n"
        "Respond in JSON only with fields: {\n"
        "  \"patch_risk\": \"good\" | \"low\" | \"medium\" | \"high\",\n"
        "  \"current_risk\": \"good\" | \"low\" | \"medium\" | \"high\",\n"
        "  \"reason\": string,\n"
        "  \"poc\"?: string\n"
        "}\n"
    )
    if diff_text:
        body += "\n\n--- DIFF (unified) ---\n" + diff_text
    return body


