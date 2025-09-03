from mispatch_finder.infra.store import save_result, load_result, list_results


def test_save_and_load_roundtrip(tmp_path):
    data = {"verdict": "good", "severity": "low"}
    save_result(tmp_path, "GHSA-AAA", data)
    got = load_result(tmp_path, "GHSA-AAA")
    assert got == data


def test_list_results(tmp_path):
    save_result(tmp_path, "GHSA-1", {"verdict": "good"})
    save_result(tmp_path, "GHSA-2", {"status": "ok"})
    items = list_results(tmp_path)
    ghsa_set = {i["ghsa"] for i in items}
    assert {"GHSA-1", "GHSA-2"}.issubset(ghsa_set)

