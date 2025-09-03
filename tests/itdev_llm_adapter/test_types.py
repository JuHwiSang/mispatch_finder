from itdev_llm_adapter import Toolset


def test_toolset_defaults():
    ts = Toolset(label="my-mcp", server_url="https://example.com/sse")
    assert ts.bearer_token is None
    assert ts.headers == {}
    assert ts.allowed_tools is None
    assert ts.require_approval == "never"


def test_toolset_custom_fields():
    ts = Toolset(
        label="m",
        server_url="https://mcp/sse",
        bearer_token="T",
        headers={"X-Trace": "1"},
        allowed_tools=["echo"],
        require_approval={"echo": True},
    )
    assert ts.bearer_token == "T"
    assert ts.headers["X-Trace"] == "1"
    assert ts.allowed_tools == ["echo"]
    assert ts.require_approval == {"echo": True}


