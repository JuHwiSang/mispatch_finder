from mispatch_finder.infra.llm import call_llm


def test_call_llm_returns_json_with_mock():
    text = call_llm(
        provider="openai",
        model="gpt-test",
        api_key="sk-xxx",
        mcp_url="http://127.0.0.1:18080",
        mcp_token="tkn",
        prompt="hello",
    )
    assert text.startswith("{") and text.endswith("}")

