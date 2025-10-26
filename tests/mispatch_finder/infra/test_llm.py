import pytest

from mispatch_finder.infra import llm as llm_module
from mispatch_finder.infra.llm import LLM
from mispatch_finder.infra.llm_adapters.types import LLMResponse, TokenUsage


def test_llm_initialization():
    llm = LLM(provider="openai", model="gpt-4", api_key="sk-test")

    assert llm._provider == "openai"
    assert llm._model == "gpt-4"
    assert llm._api_key == "sk-test"


def test_llm_call_returns_raw_text(monkeypatch):
    """Test that LLM returns raw text without JSON extraction."""
    class MockAdapter:
        def run(self, prompt, toolset):
            # Return JSON wrapped in markdown
            text = '```json\n{"patch_risk":"good","current_risk":"low","reason":"test"}\n```'
            return LLMResponse(text=text, usage=TokenUsage(10, 20, 30))

    def mock_get_adapter(provider, model, api_key):
        return MockAdapter()

    monkeypatch.setattr(llm_module, "get_adapter", mock_get_adapter)

    llm = LLM(provider="openai", model="gpt-4", api_key="sk-test")
    result = llm.call(prompt="test prompt", mcp_url="http://localhost", mcp_token="token")

    # Should return raw text (JSON extraction is now in JsonExtractor service)
    assert "```json" in result
    assert "patch_risk" in result


def test_llm_call_handles_plain_text(monkeypatch):
    """Test that LLM handles plain text responses."""
    class MockAdapter:
        def run(self, prompt, toolset):
            text = '{"patch_risk":"high","current_risk":"medium","reason":"vulnerability found"}'
            return LLMResponse(text=text, usage=TokenUsage(5, 10, 15))

    def mock_get_adapter(provider, model, api_key):
        return MockAdapter()

    monkeypatch.setattr(llm_module, "get_adapter", mock_get_adapter)

    llm = LLM(provider="openai", model="gpt-4", api_key="sk-test")
    result = llm.call(prompt="test", mcp_url="http://localhost", mcp_token="token")

    # Returns raw text
    assert result == '{"patch_risk":"high","current_risk":"medium","reason":"vulnerability found"}'


def test_llm_call_returns_any_text(monkeypatch):
    """Test that LLM returns any text as-is."""
    class MockAdapter:
        def run(self, prompt, toolset):
            return LLMResponse(text="No JSON here", usage=None)

    def mock_get_adapter(provider, model, api_key):
        return MockAdapter()

    monkeypatch.setattr(llm_module, "get_adapter", mock_get_adapter)

    llm = LLM(provider="openai", model="gpt-4", api_key="sk-test")
    result = llm.call(prompt="test", mcp_url="http://localhost", mcp_token="token")

    assert result == "No JSON here"


def test_llm_call_with_toolset(monkeypatch):
    """Test that LLM passes toolset correctly to adapter."""
    captured_toolset = []

    class MockAdapter:
        def run(self, prompt, toolset):
            captured_toolset.extend(toolset)
            return LLMResponse(text='{"test":"ok"}', usage=None)

    def mock_get_adapter(provider, model, api_key):
        return MockAdapter()

    monkeypatch.setattr(llm_module, "get_adapter", mock_get_adapter)

    llm = LLM(provider="openai", model="gpt-4", api_key="sk-test")
    llm.call(
        prompt="test",
        mcp_url="http://localhost:8080",
        mcp_token="secret-token"
    )

    assert len(captured_toolset) == 1
    assert captured_toolset[0].label == "mispatch_tools"
    assert captured_toolset[0].server_url == "http://localhost:8080"
    assert captured_toolset[0].bearer_token == "secret-token"
