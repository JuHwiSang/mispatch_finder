"""CLI output formatting utilities for human-readable display."""

from __future__ import annotations

from ..core.domain.models import AnalysisResult, Vulnerability


def format_analyze_result(result: AnalysisResult) -> str:
    """Format analysis result for human-readable CLI output.

    Args:
        result: Analysis result

    Returns:
        Formatted string for display
    """
    lines = []
    lines.append("=" * 80)
    lines.append("ANALYSIS RESULT")
    lines.append("=" * 80)

    # GHSA ID
    lines.append(f"\nGHSA ID: {result.ghsa}")

    # Provider and Model
    if result.provider or result.model:
        parts = []
        if result.provider:
            parts.append(f"Provider: {result.provider}")
        if result.model:
            parts.append(f"Model: {result.model}")
        lines.append(" | ".join(parts))

    # Assessment
    lines.append("\n" + "-" * 80)
    lines.append("ASSESSMENT")
    lines.append("-" * 80)

    # Verdict (current_risk)
    if result.verdict:
        lines.append(f"\nCurrent Risk: {result.verdict.upper()}")

    # Severity (patch_risk)
    if result.severity:
        lines.append(f"Patch Risk: {result.severity.upper()}")

    # Rationale (reason)
    if result.rationale:
        lines.append(f"\nRationale:\n{result.rationale}")

    # Evidence
    if result.evidence:
        lines.append(f"\nEvidence:")
        for i, ev in enumerate(result.evidence, 1):
            if isinstance(ev, dict):
                lines.append(f"  {i}. {ev}")
            else:
                lines.append(f"  {i}. {ev}")

    # PoC
    if result.poc_idea:
        lines.append(f"\nProof of Concept:\n{result.poc_idea}")

    lines.append("\n" + "=" * 80)

    return "\n".join(lines)


def format_vulnerability_list(
    ghsa_ids: list[str] | None = None,
    vulnerabilities: list[Vulnerability] | None = None,
) -> str:
    """Format vulnerability list for human-readable CLI output.

    Args:
        ghsa_ids: Simple list of GHSA IDs (when detailed=False)
        vulnerabilities: Detailed vulnerability objects (when detailed=True)

    Returns:
        Formatted string for display
    """
    lines = []

    if ghsa_ids is not None:
        # Simple list mode
        lines.append(f"Found {len(ghsa_ids)} vulnerabilities:")
        lines.append("")
        for ghsa_id in ghsa_ids:
            lines.append(f"  {ghsa_id}")
        return "\n".join(lines)

    if vulnerabilities is not None:
        # Detailed table mode
        lines.append(f"Found {len(vulnerabilities)} vulnerabilities:")
        lines.append("")
        lines.append("-" * 120)
        lines.append(
            f"{'GHSA ID':<20} {'CVE ID':<18} {'Severity':<10} {'Repository':<35} {'Stars':>8} {'Size (KB)':>10}"
        )
        lines.append("-" * 120)

        for v in vulnerabilities:
            ghsa = v.ghsa_id
            cve = v.cve_id or "N/A"
            severity = v.severity or "N/A"
            repo = f"{v.repository.owner}/{v.repository.name}"
            stars = f"{v.repository.star_count:,}" if v.repository.star_count is not None else "N/A"
            size = f"{v.repository.size_kb:,}" if v.repository.size_kb is not None else "N/A"

            # Truncate long repo names
            if len(repo) > 35:
                repo = repo[:32] + "..."

            lines.append(f"{ghsa:<20} {cve:<18} {severity:<10} {repo:<35} {stars:>8} {size:>10}")

        lines.append("-" * 120)
        return "\n".join(lines)

    return "No vulnerabilities found."
