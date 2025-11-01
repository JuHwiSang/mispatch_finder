"""CLI output formatting utilities for human-readable display."""

from __future__ import annotations

from ..core.domain.models import Vulnerability


def format_analyze_result(result: dict) -> str:
    """Format analysis result for human-readable CLI output.

    Args:
        result: Analysis result dictionary

    Returns:
        Formatted string for display
    """
    lines = []
    lines.append("=" * 80)
    lines.append("ANALYSIS RESULT")
    lines.append("=" * 80)

    # GHSA ID
    if "ghsa_id" in result:
        lines.append(f"\nGHSA ID: {result['ghsa_id']}")

    # Repository info
    if "repository" in result:
        repo = result["repository"]
        lines.append(f"Repository: {repo.get('owner')}/{repo.get('name')}")

    # Commit hash
    if "commit_hash" in result:
        lines.append(f"Commit: {result['commit_hash']}")

    # Assessment
    if "assessment" in result:
        lines.append("\n" + "-" * 80)
        lines.append("ASSESSMENT")
        lines.append("-" * 80)
        assessment = result["assessment"]

        if "is_mispatch" in assessment:
            status = "MISPATCH DETECTED" if assessment["is_mispatch"] else "NO MISPATCH"
            lines.append(f"\nStatus: {status}")

        if "confidence" in assessment:
            lines.append(f"Confidence: {assessment['confidence']}")

        if "reasoning" in assessment:
            lines.append(f"\nReasoning:\n{assessment['reasoning']}")

        if "affected_files" in assessment and assessment["affected_files"]:
            lines.append(f"\nAffected Files:")
            for f in assessment["affected_files"]:
                lines.append(f"  - {f}")

    # Token usage
    if "token_usage" in result:
        lines.append("\n" + "-" * 80)
        lines.append("TOKEN USAGE")
        lines.append("-" * 80)
        usage = result["token_usage"]
        lines.append(f"Input: {usage.get('input_tokens', 0):,}")
        lines.append(f"Output: {usage.get('output_tokens', 0):,}")
        lines.append(f"Total: {usage.get('total_tokens', 0):,}")

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
