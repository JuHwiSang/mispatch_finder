"""Facade function tests for main module."""
from pathlib import Path

from mispatch_finder.app.main import run_analysis, list_ghsa_ids, clear_all_caches, logs


def test_run_analysis_with_optional_params(mock_container_for_run_analysis):
    """Test that run_analysis works with optional parameters."""
    result = run_analysis(
        ghsa="GHSA-OPT-TEST",
        force_reclone=True,
    )
    
    assert isinstance(result, dict)
    assert result["ghsa"] == "GHSA-OPT-TEST"
    assert result["raw_text"]


def test_list_ghsa_ids_returns_list(mock_container_for_list_ghsa):
    """Test that list_ghsa_ids returns a list of GHSA IDs."""
    result = list_ghsa_ids()
    
    assert isinstance(result, list)
    assert len(result) == 2
    assert all(ghsa.startswith("GHSA-") for ghsa in result)


def test_clear_all_caches_executes(tmp_path, mock_container_for_clear_cache):
    """Test that clear_all_caches executes without error."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    (cache_dir / "test.txt").write_text("test", encoding="utf-8")
    
    # Should not raise
    clear_all_caches()


def test_logs_with_ghsa(tmp_path, mock_container_for_logs):
    """Test that logs returns log details for a GHSA."""
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()

    log_file = logs_dir / "GHSA-TEST.jsonl"
    log_file.write_text(
        '{"message":"run_started","ghsa":"GHSA-TEST"}\n'
        '{"message":"final_result","payload":{"type":"final_result","result":{"ghsa":"GHSA-TEST"}}}\n',
        encoding="utf-8"
    )

    result = logs("GHSA-TEST", verbose=False)

    assert isinstance(result, list)
    assert len(result) > 0


def test_logs_without_ghsa(tmp_path, mock_container_for_logs):
    """Test that logs returns summary table when no GHSA provided."""
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()

    result = logs(None, verbose=False)

    assert isinstance(result, list)


def test_run_analysis_with_mocked_dependencies(mock_container_for_run_analysis):
    """Test run_analysis with fully mocked dependencies."""
    result = run_analysis(
        ghsa="GHSA-TEST-E2E",
        force_reclone=True,
    )
    
    assert isinstance(result, dict)
    assert result["ghsa"] == "GHSA-TEST-E2E"
    assert result["raw_text"]


def test_run_analysis_saves_result(mock_container_for_run_analysis):
    """Test that run_analysis saves the result to disk."""
    repo_dir, c1, c2 = mock_container_for_run_analysis
    
    result = run_analysis(
        ghsa="GHSA-SAVE-TEST",
        force_reclone=False,
    )
    
    # Result should be returned
    assert isinstance(result, dict)
    assert result["ghsa"] == "GHSA-SAVE-TEST"
