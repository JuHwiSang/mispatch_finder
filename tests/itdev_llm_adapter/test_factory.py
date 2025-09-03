import pytest

from itdev_llm_adapter import Toolset
from itdev_llm_adapter.factory import get_adapter, run_with_openai, run_with_anthropic


def test_get_adapter_openai(monkeypatch):
    class DummyAdapter:
        def __init__(self, model: str, api_key: str):
            self.model = model
            self.api_key = api_key

        def run(self, *args, **kwargs):
            return "ok"

    import itdev_llm_adapter.factory as mod
    monkeypatch.setattr(mod, "OpenAIHostedMCPAdapter", DummyAdapter)

    adapter = get_adapter("openai", "o3", api_key="k")
    assert adapter.run("p", []) == "ok"


def test_get_adapter_anthropic(monkeypatch):
    class DummyAdapter:
        def __init__(self, model: str, api_key: str):
            self.model = model
            self.api_key = api_key

        def run(self, *args, **kwargs):
            return "ok"

    import itdev_llm_adapter.factory as mod
    monkeypatch.setattr(mod, "AnthropicHostedMCPAdapter", DummyAdapter)

    adapter = get_adapter("anthropic", "claude", api_key="k")
    assert adapter.run("p", []) == "ok"


def test_run_with_openai_uses_adapter(monkeypatch):
    class DummyAdapter:
        def __init__(self, model: str, api_key: str):
            self.model = model
            self.api_key = api_key

        def run(self, prompt, toolsets, **kwargs):
            return f"ok:{prompt}:{len(toolsets)}:{self.model}:{self.api_key}"

    import itdev_llm_adapter.factory as mod
    monkeypatch.setattr(mod, "OpenAIHostedMCPAdapter", DummyAdapter)

    out = run_with_openai(model="o3", api_key="k", prompt="p", toolsets=[Toolset(label="a", server_url="u")])
    assert out == "ok:p:1:o3:k"


def test_run_with_anthropic_uses_adapter(monkeypatch):
    class DummyAdapter:
        def __init__(self, model: str, api_key: str):
            self.model = model
            self.api_key = api_key

        def run(self, prompt, toolsets, **kwargs):
            return f"ok:{prompt}:{len(toolsets)}:{self.model}:{self.api_key}"

    import itdev_llm_adapter.factory as mod
    monkeypatch.setattr(mod, "AnthropicHostedMCPAdapter", DummyAdapter)

    out = run_with_anthropic(model="c", api_key="k", prompt="p", toolsets=[Toolset(label="a", server_url="u")])
    assert out == "ok:p:1:c:k"


