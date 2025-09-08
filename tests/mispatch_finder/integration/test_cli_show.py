import json
import os
import re
import pytest
from typer.testing import CliRunner

from mispatch_finder.app.cli import app


@pytest.mark.integration
def test_cli_show_lists_real_items():
    # This test runs the real CLI show command, which requires GITHUB_TOKEN.
    if not os.environ.get("GITHUB_TOKEN"):
        pytest.skip("GITHUB_TOKEN not set; skipping live CLI show test")

    runner = CliRunner()
    res = runner.invoke(app, ["show"])
    assert res.exit_code == 0
    payload = json.loads(res.stdout)
    assert isinstance(payload, dict)
    assert "items" in payload
    assert isinstance(payload["items"], list)
    # Ensure there is at least one GHSA-like identifier
    assert any(isinstance(x, str) and re.match(r"^GHSA-[A-Za-z0-9_-]+-[A-Za-z0-9_-]+-[A-Za-z0-9_-]+$", x) for x in payload["items"]) 

