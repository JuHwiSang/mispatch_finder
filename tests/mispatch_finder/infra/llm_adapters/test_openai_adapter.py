import types

import pytest

from mispatch_finder.infra.llm_adapters import Toolset
from mispatch_finder.infra.llm_adapters.openai_adapter import OpenAIHostedMCPAdapter
from mispatch_finder.infra.llm_adapters.types import TokenUsage


class DummyResponse:
    def __init__(self, text: str) -> None:
        self.output_text = text
        self.usage = TokenUsage(input_tokens=1, output_tokens=2, total_tokens=3)


class DummyResponsesClient:
    def __init__(self, expected_tools):
        self._expected_tools = expected_tools

    def create(self, *, model, input, tools, tool_choice, extra_headers=None, store=True):  # noqa: A002 (input)
        # Validate tools shape roughly
        assert tools == self._expected_tools
        assert isinstance(model, str)
        assert isinstance(input, str)
        assert tool_choice == "auto"
        assert store == True
        return DummyResponse("ok-openai")


class DummyOpenAI:
    def __init__(self, *, api_key: str):
        assert api_key == "sk-openai-test"
        self.responses = DummyResponsesClient(expected_tools=None)


@pytest.fixture(autouse=True)
def mock_openai(monkeypatch):
    # Replace OpenAI class used in adapter with dummy
    import mispatch_finder.infra.llm_adapters.openai_adapter as mod

    def _factory(*, api_key: str):
        return DummyOpenAI(api_key=api_key)

    monkeypatch.setattr(mod, "OpenAI", lambda api_key: _factory(api_key=api_key))
    yield


def test_openai_adapter_builds_tools_and_calls_create(monkeypatch):
    # Arrange expected tool payload
    expected_tools = [
        {
            "type": "mcp",
            "server_label": "my-mcp",
            "server_url": "https://example.com/sse",
            "headers": {"Authorization": "Bearer mcp"},
            "allowed_tools": ["echo"],
            "require_approval": "never",
        }
    ]

    dummy_client = DummyOpenAI(api_key="sk-openai-test")
    dummy_client.responses = DummyResponsesClient(expected_tools=expected_tools)

    import mispatch_finder.infra.llm_adapters.openai_adapter as mod
    monkeypatch.setattr(mod, "OpenAI", lambda api_key: dummy_client)

    adapter = OpenAIHostedMCPAdapter(model="o3", api_key="sk-openai-test")
    response = adapter.run(
        prompt="ping",
        toolsets=[
            Toolset(
                label="my-mcp",
                server_url="https://example.com/sse",
                bearer_token="mcp",
                allowed_tools=["echo"],
                require_approval="never",
            )
        ],
    )
    assert response.text == "ok-openai"
