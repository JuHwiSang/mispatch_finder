from pathlib import Path

from mispatch_finder.core.toolset import describe_available_tools
from mispatch_finder.infra.mcp.mounts import _has_node_project


def test_has_node_project(tmp_path):
    assert _has_node_project(tmp_path) is False
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    assert _has_node_project(tmp_path) is True


def test_describe_available_tools_matrix():
    m = describe_available_tools(True, False)
    assert m == {"pre/repo": True, "pre/debug": True, "post/repo": False, "post/debug": False}
    m2 = describe_available_tools(False, True)
    assert m2 == {"pre/repo": False, "pre/debug": False, "post/repo": True, "post/debug": True}

