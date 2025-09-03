import json
from pathlib import Path
from typer.testing import CliRunner

from mispatch_finder.app.cli import app
from mispatch_finder.app import main as app_main
from mispatch_finder.infra.store import save_result


def test_cli_show_lists_items(tmp_path, monkeypatch):
    # Redirect results dir to tmp at the import site used by CLI (app.main)
    monkeypatch.setattr(app_main, "get_results_dir", lambda: tmp_path)
    save_result(tmp_path, "GHSA-1", {"verdict": "good"})
    save_result(tmp_path, "GHSA-2", {"status": "ok"})

    runner = CliRunner()
    res = runner.invoke(app, ["show"])
    assert res.exit_code == 0
    payload = json.loads(res.stdout)
    assert "items" in payload
    assert any(item.get("ghsa") == "GHSA-1" for item in payload["items"])  # may not be sorted on all FS
    assert any(item.get("ghsa") == "GHSA-2" for item in payload["items"])  # ensure both are present


def test_cli_show_one_item(tmp_path, monkeypatch):
    monkeypatch.setattr(app_main, "get_results_dir", lambda: tmp_path)
    save_result(tmp_path, "GHSA-X", {"ghsa": "GHSA-X", "verdict": "good"})

    runner = CliRunner()
    res = runner.invoke(app, ["show", "--ghsa", "GHSA-X"])
    assert res.exit_code == 0
    payload = json.loads(res.stdout)
    assert payload.get("ghsa") == "GHSA-X"
    # Single-item show returns the stored object; ensure we persisted our verdict
    assert payload.get("verdict") == "good"

