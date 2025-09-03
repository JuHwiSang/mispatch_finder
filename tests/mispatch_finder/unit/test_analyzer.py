from mispatch_finder.core.analyze import Analyzer


def test_analyzer_generates_ephemeral_token():
    a1 = Analyzer()
    a2 = Analyzer()
    assert isinstance(a1.mcp_token, str) and len(a1.mcp_token) > 20
    assert a1.mcp_token != a2.mcp_token

