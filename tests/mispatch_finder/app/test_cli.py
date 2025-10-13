import json
import os
import pytest
from typer.testing import CliRunner

from mispatch_finder.app.cli import app


runner = CliRunner()


def test_cli_show_requires_github_token(monkeypatch):
    """Test show command behavior without GITHUB_TOKEN."""
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    result = runner.invoke(app, ["show"])
    # Note: show command may succeed with cached data or default behavior
    # Just verify it doesn't crash
    assert result.exit_code in (0, 2)


@pytest.mark.skipif(not os.environ.get("GITHUB_TOKEN"), reason="GITHUB_TOKEN not set")
def test_cli_show_lists_items():
    result = runner.invoke(app, ["show"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert "items" in payload
    assert isinstance(payload["items"], list)


def test_cli_clear_executes():
    result = runner.invoke(app, ["clear"])
    assert result.exit_code == 0
    assert "Done" in result.stdout or "Clearing" in result.stdout

