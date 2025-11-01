"""Tests for CLI formatter utilities."""

from mispatch_finder.core.domain.models import Repository, Vulnerability
from mispatch_finder.app.cli_formatter import format_analyze_result, format_vulnerability_list


def test_format_analyze_result_basic():
    """Test basic analysis result formatting."""
    result = {
        "ghsa_id": "GHSA-1234-5678-9012",
        "repository": {
            "owner": "test-org",
            "name": "test-repo",
        },
        "commit_hash": "abc123def456",
        "assessment": {
            "is_mispatch": True,
            "confidence": "high",
            "reasoning": "The patch was not applied correctly.",
            "affected_files": ["src/main.py", "src/utils.py"],
        },
        "token_usage": {
            "input_tokens": 1000,
            "output_tokens": 500,
            "total_tokens": 1500,
        },
    }

    output = format_analyze_result(result)

    assert "ANALYSIS RESULT" in output
    assert "GHSA-1234-5678-9012" in output
    assert "test-org/test-repo" in output
    assert "abc123def456" in output
    assert "MISPATCH DETECTED" in output
    assert "high" in output
    assert "The patch was not applied correctly." in output
    assert "src/main.py" in output
    assert "src/utils.py" in output
    assert "1,000" in output  # Input tokens formatted
    assert "500" in output  # Output tokens
    assert "1,500" in output  # Total tokens


def test_format_analyze_result_no_mispatch():
    """Test formatting when no mispatch is detected."""
    result = {
        "ghsa_id": "GHSA-1234-5678-9012",
        "repository": {"owner": "test-org", "name": "test-repo"},
        "commit_hash": "abc123",
        "assessment": {
            "is_mispatch": False,
            "confidence": "medium",
            "reasoning": "Patch appears correct.",
        },
    }

    output = format_analyze_result(result)

    assert "NO MISPATCH" in output
    assert "medium" in output


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
