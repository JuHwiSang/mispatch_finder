import os
import sys
import json
from pathlib import Path
import pytest
from helpers import mark_by_dir

from mispatch_finder.infra import llm
from itdev_llm_adapter.types import LLMResponse, TokenUsage

class DummyAdapter:
    def __init__(self, provider: str, model: str, api_key: str):
        self.provider = provider
        self.model = model
        self.api_key = api_key

    def run(self, prompt: str, toolsets, *, max_output_tokens: int = 800, request_headers=None) -> LLMResponse:  # noqa: ANN001
        # Return deterministic fake JSON-like text to simulate model output
        payload = {
            "verdict": "good",
            "severity": "low",
            "rationale": "stubbed",
            "evidence": [],
        }
        return LLMResponse(text=json.dumps(payload), usage=TokenUsage(input_tokens=1, output_tokens=2, total_tokens=3))


@pytest.fixture(autouse=True)
def _ensure_src_on_syspath():
    # Add project src/ to sys.path for src-layout imports
    root = Path(__file__).resolve().parents[1]
    src_path = root / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
    yield


@pytest.fixture(autouse=True)
def mock_itdev_adapter(monkeypatch):
    # Prevent real OpenAI/Anthropic calls by mocking factory.get_adapter

    def fake_get_adapter(provider: str, model: str, api_key: str):
        print('fake_get_adapter', provider, model, api_key)
        return DummyAdapter(provider, model, api_key)

    monkeypatch.setattr(llm, "get_adapter", fake_get_adapter)
    yield


TESTS = Path(__file__).parent

def pytest_collection_modifyitems(config, items):
    mark_by_dir(items, TESTS / "mispatch_finder" / "unit", pytest.mark.unit)
    mark_by_dir(items, TESTS / "mispatch_finder" / "integration", pytest.mark.integration)