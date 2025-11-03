import json
from pathlib import Path
from mispatch_finder.infra.logging.log_summary import parse_log_details, parse_log_file, format_single_summary


def test_parse_log_details_empty(tmp_path):
    log_file = tmp_path / "test.jsonl"
    log_file.write_text("", encoding="utf-8")

    details = parse_log_details(log_file)
    assert details.ghsa_id == "test"


def test_format_single_summary(tmp_path):
    log_file = tmp_path / "GHSA-TEST.jsonl"
    log_file.write_text('{"message":"final_result","payload":{"type":"final_result","result":{"ghsa":"GHSA-TEST"}}}\n', encoding="utf-8")

    details = parse_log_details(log_file)
    lines = format_single_summary(details)

    assert isinstance(lines, list)
    assert len(lines) > 0


def test_parse_log_details_old_format(tmp_path):
    """Test parsing old format with payload wrapper."""
    log_file = tmp_path / "GHSA-OLD.jsonl"

    # Old format: extra={'payload': {...}}
    old_logs = [
        {
            "message": "ghsa_meta",
            "level": "INFO",
            "logger": "mispatch_finder",
            "payload": {
                "type": "ghsa_meta",
                "ghsa": "GHSA-OLD-1234",
                "vulnerability": {
                    "repo_url": "https://github.com/test/repo",
                    "commit": "abc123",
                    "cve_id": "CVE-2024-0001",
                    "severity": "HIGH"
                }
            }
        },
        {
            "message": "llm_input",
            "level": "INFO",
            "logger": "mispatch_finder",
            "payload": {
                "type": "llm_input",
                "model": "gpt-4",
                "provider": "openai"
            }
        },
        {
            "message": "final_result",
            "level": "INFO",
            "logger": "mispatch_finder",
            "payload": {
                "type": "final_result",
                "result": {
                    "ghsa": "GHSA-OLD-1234",
                    "model": "gpt-4",
                    "verdict": "high",
                    "severity": "medium",
                    "rationale": "Old format test",
                    "poc_idea": "PoC for old format"
                }
            }
        }
    ]

    log_file.write_text("\n".join(json.dumps(log) for log in old_logs) + "\n", encoding="utf-8")

    details = parse_log_details(log_file)

    assert details.ghsa_id == "GHSA-OLD-1234"
    assert details.repo_url == "https://github.com/test/repo"
    assert details.commit == "abc123"
    assert details.model == "gpt-4"
    assert details.current_risk == "high"
    assert details.patch_risk == "medium"
    assert details.reason == "Old format test"
    assert details.poc == "PoC for old format"


def test_parse_log_details_new_format(tmp_path):
    """Test parsing new format with direct fields."""
    log_file = tmp_path / "GHSA-NEW.jsonl"

    # New format: extra={...} (no payload wrapper)
    new_logs = [
        {
            "message": "ghsa_meta",
            "level": "INFO",
            "logger": "mispatch_finder",
            "type": "ghsa_meta",
            "ghsa": "GHSA-NEW-5678",
            "vulnerability": {
                "repo_url": "https://github.com/new/repo",
                "commit": "def456",
                "cve_id": "CVE-2024-0002",
                "severity": "CRITICAL"
            }
        },
        {
            "message": "llm_input",
            "level": "INFO",
            "logger": "mispatch_finder",
            "type": "llm_input",
            "model": "gpt-4o",
            "provider": "openai"
        },
        {
            "message": "final_result",
            "level": "INFO",
            "logger": "mispatch_finder",
            "type": "final_result",
            "result": {
                "ghsa": "GHSA-NEW-5678",
                "model": "gpt-4o",
                "verdict": "medium",
                "severity": "low",
                "rationale": "New format test",
                "poc_idea": "PoC for new format"
            }
        }
    ]

    log_file.write_text("\n".join(json.dumps(log) for log in new_logs) + "\n", encoding="utf-8")

    details = parse_log_details(log_file)

    assert details.ghsa_id == "GHSA-NEW-5678"
    assert details.repo_url == "https://github.com/new/repo"
    assert details.commit == "def456"
    assert details.model == "gpt-4o"
    assert details.current_risk == "medium"
    assert details.patch_risk == "low"
    assert details.reason == "New format test"
    assert details.poc == "PoC for new format"


def test_parse_log_file_old_format(tmp_path):
    """Test parse_log_file with old format."""
    log_file = tmp_path / "GHSA-OLD-FILE.jsonl"

    old_logs = [
        {
            "message": "llm_usage",
            "level": "INFO",
            "logger": "mispatch_finder",
            "payload": {
                "type": "llm_usage",
                "total_tokens": 1500
            }
        },
        {
            "message": "final_result",
            "level": "INFO",
            "logger": "mispatch_finder",
            "payload": {
                "type": "final_result",
                "result": {
                    "verdict": "high",
                    "severity": "good",
                    "rationale": "Test reason"
                }
            }
        }
    ]

    log_file.write_text("\n".join(json.dumps(log) for log in old_logs) + "\n", encoding="utf-8")

    summary = parse_log_file(log_file, verbose=False)

    assert summary.ghsa_id == "GHSA-OLD-FILE"
    assert summary.total_tokens == 1500
    assert summary.current_risk == "high"
    assert summary.patch_risk == "good"
    assert summary.reason == "Test reason"
    assert summary.done is True


def test_parse_log_file_new_format(tmp_path):
    """Test parse_log_file with new format."""
    log_file = tmp_path / "GHSA-NEW-FILE.jsonl"

    new_logs = [
        {
            "message": "llm_usage",
            "level": "INFO",
            "logger": "mispatch_finder",
            "type": "llm_usage",
            "total_tokens": 2000
        },
        {
            "message": "final_result",
            "level": "INFO",
            "logger": "mispatch_finder",
            "type": "final_result",
            "result": {
                "verdict": "low",
                "severity": "high",
                "rationale": "New test reason"
            }
        }
    ]

    log_file.write_text("\n".join(json.dumps(log) for log in new_logs) + "\n", encoding="utf-8")

    summary = parse_log_file(log_file, verbose=False)

    assert summary.ghsa_id == "GHSA-NEW-FILE"
    assert summary.total_tokens == 2000
    assert summary.current_risk == "low"
    assert summary.patch_risk == "high"
    assert summary.reason == "New test reason"
    assert summary.done is True

