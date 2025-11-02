import pytest
from pathlib import Path

from mispatch_finder.infra.analysis_store import AnalysisStore


# Tests for log reading operations

def test_analysis_store_read_log_verbose(tmp_path):
    analysis_dir = tmp_path / "analysis"
    analysis_dir.mkdir()

    log_file = analysis_dir / "GHSA-TEST.jsonl"
    log_file.write_text(
        '{"message":"run_started","ghsa":"GHSA-TEST"}\n'
        '{"message":"final_result","payload":{"type":"final_result"}}\n',
        encoding="utf-8"
    )

    store = AnalysisStore(analysis_dir=analysis_dir)
    lines = store.read_log("GHSA-TEST", verbose=True)

    assert len(lines) == 2
    assert "run_started" in lines[0]
    assert "final_result" in lines[1]


def test_analysis_store_read_log_non_verbose(tmp_path):
    analysis_dir = tmp_path / "analysis"
    analysis_dir.mkdir()

    log_file = analysis_dir / "GHSA-TEST.jsonl"
    log_file.write_text(
        '{"message":"run_started","ghsa":"GHSA-TEST"}\n'
        '{"message":"final_result","payload":{"type":"final_result","result":{"ghsa":"GHSA-TEST"}}}\n',
        encoding="utf-8"
    )

    store = AnalysisStore(analysis_dir=analysis_dir)
    lines = store.read_log("GHSA-TEST", verbose=False)

    assert isinstance(lines, list)
    assert len(lines) > 0


def test_analysis_store_read_log_not_found(tmp_path):
    analysis_dir = tmp_path / "analysis"
    analysis_dir.mkdir()

    store = AnalysisStore(analysis_dir=analysis_dir)

    with pytest.raises(FileNotFoundError):
        store.read_log("GHSA-NONEXIST", verbose=False)


def test_analysis_store_summarize_all_empty(tmp_path):
    analysis_dir = tmp_path / "analysis"
    analysis_dir.mkdir()

    store = AnalysisStore(analysis_dir=analysis_dir)
    lines = store.summarize_all(verbose=False)

    # Should return empty or header-only table
    assert isinstance(lines, list)


def test_analysis_store_summarize_all_with_logs(tmp_path):
    analysis_dir = tmp_path / "analysis"
    analysis_dir.mkdir()

    # Create multiple log files
    for i, ghsa in enumerate(["GHSA-1111-2222-3333", "GHSA-4444-5555-6666"]):
        log_file = analysis_dir / f"{ghsa}.jsonl"
        log_file.write_text(
            f'{{"message":"run_started","ghsa":"{ghsa}"}}\n'
            f'{{"message":"final_result","payload":{{"type":"final_result","result":{{"ghsa":"{ghsa}"}}}}}}\n',
            encoding="utf-8"
        )

    store = AnalysisStore(analysis_dir=analysis_dir)
    lines = store.summarize_all(verbose=False)

    assert isinstance(lines, list)
    assert len(lines) > 0


def test_analysis_store_get_analyzed_ids_empty(tmp_path):
    analysis_dir = tmp_path / "analysis"
    analysis_dir.mkdir()

    store = AnalysisStore(analysis_dir=analysis_dir)
    analyzed = store.get_analyzed_ids()

    assert analyzed == set()


def test_analysis_store_get_analyzed_ids_with_completed(tmp_path):
    analysis_dir = tmp_path / "analysis"
    analysis_dir.mkdir()

    # Create a completed analysis log
    log_file = analysis_dir / "GHSA-DONE.jsonl"
    log_file.write_text(
        '{"message":"run_started","ghsa":"GHSA-DONE"}\n'
        '{"message":"final_result","payload":{"type":"final_result"}}\n',
        encoding="utf-8"
    )

    store = AnalysisStore(analysis_dir=analysis_dir)
    analyzed = store.get_analyzed_ids()

    # Should detect completed analysis based on log_summary logic
    assert isinstance(analyzed, set)
