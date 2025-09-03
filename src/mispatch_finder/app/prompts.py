from __future__ import annotations

from typing import Dict


def build_prompt(ghsa: str, meta: Dict[str, str], has_pre: bool, has_post: bool, *, diff_text: str = "") -> str:
    repo_url = meta.get("repo_url", "")
    commit = meta.get("commit", "")
    pre_note = "available" if has_pre else "unavailable (no parent commit)"
    post_note = "available" if has_post else "unavailable"

    body = (
        f"You are a security reviewer assessing patch correctness for GHSA {ghsa}.\n"
        f"Repository: {repo_url}\n"
        f"Patched commit: {commit}\n"
        f"Pre-state tools: {pre_note}; Post-state tools: {post_note}.\n\n"
        "Tools are exposed via MCP under prefixes: pre/repo, pre/debug, post/repo, post/debug.\n"
        "Use repo tools to read files/dirs and search; use debug tools only when Node project exists.\n\n"
        "Task:\n"
        "1) Decide if the patch is correct or leaves residual risk.\n"
        "2) Provide rationale and file/line references gathered via tools.\n"
        "3) If risky, propose a simple PoC idea.\n\n"
        "Respond in JSON only with fields: {\n"
        "  \"verdict\": \"good\" | \"risky\",\n"
        "  \"severity\": \"low\" | \"medium\" | \"high\",\n"
        "  \"rationale\": string,\n"
        "  \"evidence\": [{\"file\": string, \"line\"?: number, \"snippet\"?: string, \"tool\": string}],\n"
        "  \"poc_idea\"?: string\n"
        "}\n"
    )
    if diff_text:
        body += "\n\n--- DIFF (unified) ---\n" + diff_text
    return body


