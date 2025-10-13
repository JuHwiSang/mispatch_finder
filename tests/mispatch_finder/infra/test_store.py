from mispatch_finder.infra.adapters.result_store import ResultStore


def test_result_store_save_and_load(tmp_path):
    results_dir = tmp_path / "results"
    results_dir.mkdir()
    
    adapter = ResultStore(results_dir=results_dir)
    
    payload = {
        "ghsa": "GHSA-TEST-1234-5678",
        "provider": "openai",
        "verdict": "good",
    }
    
    adapter.save(ghsa="GHSA-TEST-1234-5678", payload=payload)
    
    loaded = adapter.load(ghsa="GHSA-TEST-1234-5678")
    assert loaded == payload


def test_result_store_load_nonexistent(tmp_path):
    results_dir = tmp_path / "results"
    results_dir.mkdir()
    
    adapter = ResultStore(results_dir=results_dir)
    loaded = adapter.load(ghsa="GHSA-NONEXIST")
    assert loaded is None


def test_result_store_list_all(tmp_path):
    results_dir = tmp_path / "results"
    results_dir.mkdir()
    
    adapter = ResultStore(results_dir=results_dir)
    adapter.save("GHSA-1111-2222-3333", {"ghsa": "GHSA-1111-2222-3333", "verdict": "good"})
    adapter.save("GHSA-4444-5555-6666", {"ghsa": "GHSA-4444-5555-6666", "verdict": "low"})
    
    items = adapter.list_all()
    assert len(items) == 2
    assert all("ghsa" in item for item in items)

