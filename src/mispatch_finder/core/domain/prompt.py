from __future__ import annotations


def build_prompt(
    *,
    ghsa: str,
    repo_url: str,
    commit: str,
    has_previous: bool,
    has_current: bool,
    diff_text: str,
) -> str:
    """Build analysis prompt with GHSA context and diff."""
    previous_note = "available" if has_previous else "unavailable (no parent commit)"
    current_note = "available" if has_current else "unavailable"

    body = (
        f"You are a security reviewer assessing patch correctness for GHSA {ghsa}.\n"
        f"Repository: {repo_url}\n"
        f"Patched commit: {commit}\n"
        f"Previous-state tools: {previous_note}; Current-state tools: {current_note}.\n\n"
        "# Repository States\n"
        "- 'previous': Code state BEFORE the patch (parent commit of the patched commit)\n"
        "- 'current': Latest version of the repository (HEAD), NOT necessarily the patched commit\n\n"
        "Available tools are read-only repository tools for both states.\n\n"
        "# Assessment Task\n"
        "1) **Patch Risk Assessment**: Evaluate whether the patch adequately addressed the vulnerability.\n"
        "   - Compare 'previous' (vulnerable code) with the patch diff\n"
        "   - Rate: \"good\" (adequate fix) | \"low\" | \"medium\" | \"high\" (inadequate/incomplete fix)\n\n"
        "2) **Current Risk Assessment**: Determine if the vulnerability risk persists in the latest version.\n"
        "   - If patch was adequate (patch_risk = \"good\"), current_risk should be \"good\"\n"
        "   - If patch was inadequate, check 'current' state to see if the vulnerability still exists\n"
        "   - Rate: \"good\" (no risk) | \"low\" | \"medium\" | \"high\" (risk persists)\n\n"
        "3) **Proof of Concept**: Required ONLY if current_risk is not \"good\".\n"
        "   - Provide exploit code or detailed steps demonstrating the vulnerability in the 'current' state\n"
        "   - Omit this field if current_risk is \"good\"\n\n"
        "Respond in JSON only with fields: {\n"
        "  \"patch_risk\": \"good\" | \"low\" | \"medium\" | \"high\",\n"
        "  \"current_risk\": \"good\" | \"low\" | \"medium\" | \"high\",\n"
        "  \"reason\": string,\n"
        "  \"poc\"?: string  // Required only if current_risk != \"good\"\n"
        "}\n"
    )
    if diff_text:
        body += "\n\n--- DIFF (unified) ---\n" + diff_text
    return body

