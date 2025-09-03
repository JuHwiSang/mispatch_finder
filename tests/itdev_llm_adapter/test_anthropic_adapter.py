import pytest
import types

from itdev_llm_adapter import Toolset
from itdev_llm_adapter.adapters.anthropic_adapter import AnthropicHostedMCPAdapter


class DummyMessage:
    def __init__(self, content):
        self.content = content


class DummyContentBlock:
    def __init__(self, text: str):
        self.type = "text"
        self.text = text


class DummyBetaMessagesClient:
    def create(self, *, model, max_tokens, messages, mcp_servers, betas):
        # smoke-validate payload
        assert isinstance(model, str)
        assert isinstance(max_tokens, int)
        assert isinstance(messages, list)
        assert isinstance(mcp_servers, list)
        assert betas == ["mcp-client-2025-04-04"]
        return DummyMessage([DummyContentBlock("ok-anthropic")])


class DummyBeta:
    def __init__(self):
        self.messages = DummyBetaMessagesClient()


class DummyAnthropic:
    def __init__(self, *, api_key: str):
        assert api_key == "sk-anthropic-test"
        self.beta = DummyBeta()


@pytest.fixture(autouse=True)
def mock_anthropic(monkeypatch):
    import itdev_llm_adapter.adapters.anthropic_adapter as mod

    monkeypatch.setattr(mod, "anthropic", types.SimpleNamespace(Anthropic=lambda api_key: DummyAnthropic(api_key=api_key)))
    yield


def test_anthropic_adapter_builds_mcp_servers_and_calls_create(monkeypatch):
    adapter = AnthropicHostedMCPAdapter(model="claude-sonnet", api_key="sk-anthropic-test")
    text = adapter.run(
        prompt="ping",
        toolsets=[
            Toolset(
                label="my-mcp",
                server_url="https://example.com/sse",
                bearer_token="mcp",
                allowed_tools=["echo"],
            )
        ],
        max_output_tokens=256,
    )
    assert text == "ok-anthropic"


