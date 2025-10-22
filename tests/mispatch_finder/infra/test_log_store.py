import pytest
from pathlib import Path

from mispatch_finder.infra.log_store import LogStore


def test_log_store_read_log_verbose(tmp_path):
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    
    log_file = logs_dir / "GHSA-TEST.jsonl"
    log_file.write_text(
        '{"message":"run_started","ghsa":"GHSA-TEST"}\n'
        '{"message":"final_result","payload":{"type":"final_result"}}\n',
        encoding="utf-8"
    )
    
    store = LogStore(logs_dir=logs_dir)
    lines = store.read_log("GHSA-TEST", verbose=True)
    
    assert len(lines) == 2
    assert "run_started" in lines[0]
    assert "final_result" in lines[1]


def test_log_store_read_log_non_verbose(tmp_path):
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    
    log_file = logs_dir / "GHSA-TEST.jsonl"
    log_file.write_text(
        '{"message":"run_started","ghsa":"GHSA-TEST"}\n'
        '{"message":"final_result","payload":{"type":"final_result","result":{"ghsa":"GHSA-TEST"}}}\n',
        encoding="utf-8"
    )
    
    store = LogStore(logs_dir=logs_dir)
    lines = store.read_log("GHSA-TEST", verbose=False)
    
    assert isinstance(lines, list)
    assert len(lines) > 0


def test_log_store_read_log_not_found(tmp_path):
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    
    store = LogStore(logs_dir=logs_dir)
    
    with pytest.raises(FileNotFoundError):
        store.read_log("GHSA-NONEXIST", verbose=False)


def test_log_store_summarize_all_empty(tmp_path):
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    
    store = LogStore(logs_dir=logs_dir)
    lines = store.summarize_all(verbose=False)
    
    # Should return empty or header-only table
    assert isinstance(lines, list)


def test_log_store_summarize_all_with_logs(tmp_path):
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    
    # Create multiple log files
    for i, ghsa in enumerate(["GHSA-1111-2222-3333", "GHSA-4444-5555-6666"]):
        log_file = logs_dir / f"{ghsa}.jsonl"
        log_file.write_text(
            f'{{"message":"run_started","ghsa":"{ghsa}"}}\n'
            f'{{"message":"final_result","payload":{{"type":"final_result","result":{{"ghsa":"{ghsa}"}}}}}}\n',
            encoding="utf-8"
        )
    
    store = LogStore(logs_dir=logs_dir)
    lines = store.summarize_all(verbose=False)
    
    assert isinstance(lines, list)
    assert len(lines) > 0

