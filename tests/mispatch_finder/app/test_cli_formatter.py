"""Tests for CLI formatter utilities."""

from mispatch_finder.core.domain.models import AnalysisResult, Repository, Vulnerability
from mispatch_finder.app.cli_formatter import format_analyze_result, format_vulnerability_list


def test_format_analyze_result_basic():
    """Test basic analysis result formatting."""
    result = AnalysisResult(
        ghsa="GHSA-1234-5678-9012",
        provider="openai",
        model="gpt-4",
        verdict="bad",  # current_risk
        severity="high",  # patch_risk
        rationale="The patch was not applied correctly.",
        evidence=[{"file": "src/main.py"}, {"file": "src/utils.py"}],
        poc_idea="Test PoC idea",
        raw_text='{"current_risk": "bad", "patch_risk": "high"}',
    )

    output = format_analyze_result(result)

    assert "ANALYSIS RESULT" in output
    assert "GHSA-1234-5678-9012" in output
    assert "openai" in output
    assert "gpt-4" in output
    assert "BAD" in output  # Verdict uppercased
    assert "HIGH" in output  # Severity uppercased
    assert "The patch was not applied correctly." in output
    assert "src/main.py" in output
    assert "Test PoC idea" in output


def test_format_analyze_result_minimal():
    """Test formatting with minimal fields."""
    result = AnalysisResult(
        ghsa="GHSA-1234-5678-9012",
        provider="",
        model="",
        verdict="good",
        severity=None,
        rationale="Patch appears correct.",
        evidence=None,
        poc_idea=None,
        raw_text='{"current_risk": "good"}',
    )

    output = format_analyze_result(result)

    assert "GHSA-1234-5678-9012" in output
    assert "GOOD" in output
    assert "Patch appears correct." in output


def test_format_vulnerability_list_simple():
    """Test simple GHSA ID list formatting."""
    ghsa_ids = [
        "GHSA-1111-2222-3333",
        "GHSA-4444-5555-6666",
        "GHSA-7777-8888-9999",
    ]

    output = format_vulnerability_list(ghsa_ids=ghsa_ids)

    assert "Found 3 vulnerabilities:" in output
    assert "GHSA-1111-2222-3333" in output
    assert "GHSA-4444-5555-6666" in output
    assert "GHSA-7777-8888-9999" in output


def test_format_vulnerability_list_detailed():
    """Test detailed vulnerability list with table formatting."""
    vulns = [
        Vulnerability(
            ghsa_id="GHSA-1111-2222-3333",
            cve_id="CVE-2024-0001",
            severity="HIGH",
            summary="Test vulnerability 1",
            repository=Repository(
                owner="org1",
                name="repo1",
                ecosystem="npm",
                star_count=500,
                size_kb=1024,
            ),
            commit_hash="abc123",
        ),
        Vulnerability(
            ghsa_id="GHSA-4444-5555-6666",
            cve_id="CVE-2024-0002",
            severity="CRITICAL",
            summary="Test vulnerability 2",
            repository=Repository(
                owner="org2",
                name="repo2",
                ecosystem="pypi",
                star_count=1500,
                size_kb=2048,
            ),
            commit_hash="def456",
        ),
    ]

    output = format_vulnerability_list(vulnerabilities=vulns)

    assert "Found 2 vulnerabilities:" in output
    assert "GHSA ID" in output  # Table header
    assert "CVE ID" in output
    assert "Severity" in output
    assert "Repository" in output
    assert "Stars" in output
    assert "GHSA-1111-2222-3333" in output
    assert "CVE-2024-0001" in output
    assert "HIGH" in output
    assert "org1/repo1" in output
    assert "500" in output
    assert "1,024" in output
    assert "GHSA-4444-5555-6666" in output
    assert "CRITICAL" in output


def test_format_vulnerability_list_empty():
    """Test formatting with no vulnerabilities."""
    output = format_vulnerability_list(ghsa_ids=[])
    assert "Found 0 vulnerabilities:" in output

    output = format_vulnerability_list(vulnerabilities=[])
    assert "Found 0 vulnerabilities:" in output


def test_format_vulnerability_list_long_repo_name():
    """Test that long repository names are truncated."""
    vulns = [
        Vulnerability(
            ghsa_id="GHSA-1111-2222-3333",
            cve_id="CVE-2024-0001",
            severity="HIGH",
            summary="Test",
            repository=Repository(
                owner="very-long-organization-name",
                name="very-long-repository-name-that-exceeds-limit",
                ecosystem="npm",
                star_count=100,
                size_kb=500,
            ),
            commit_hash="abc123",
        ),
    ]

    output = format_vulnerability_list(vulnerabilities=vulns)

    # Should contain truncation indicator
    assert "..." in output
