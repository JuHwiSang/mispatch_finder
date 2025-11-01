from pathlib import Path
from mispatch_finder.infra.logging.log_summary import parse_log_details, format_single_summary


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

