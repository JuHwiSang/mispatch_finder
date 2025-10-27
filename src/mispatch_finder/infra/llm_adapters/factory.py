from __future__ import annotations

from .anthropic_adapter import AnthropicHostedMCPAdapter
from .interface import LLMHostedMCPAdapter
from .openai_adapter import OpenAIHostedMCPAdapter
from .types import LLMResponse, Toolset


def get_adapter(provider: str, model: str, api_key: str) -> LLMHostedMCPAdapter:
    """Factory that returns an adapter for the requested provider/model."""
    if provider == "openai":
        return OpenAIHostedMCPAdapter(model, api_key)
    if provider == "anthropic":
        return AnthropicHostedMCPAdapter(model, api_key)
    raise ValueError("provider must be 'openai' or 'anthropic'")


def run_with_openai(
    *,
    model: str,
    api_key: str,
    prompt: str,
    toolsets: list[Toolset],
    request_headers: dict[str, str] | None = None,
) -> LLMResponse:
    """One-shot helper to run with OpenAI using the MCP tools block."""
    return OpenAIHostedMCPAdapter(model, api_key).run(prompt, toolsets, request_headers=request_headers)


def run_with_anthropic(
    *,
    model: str,
    api_key: str,
    prompt: str,
    toolsets: list[Toolset],
    max_output_tokens: int = 800,
) -> LLMResponse:
    """One-shot helper to run with Anthropic using the MCP connector beta."""
    return AnthropicHostedMCPAdapter(model, api_key).run(prompt, toolsets, max_output_tokens=max_output_tokens)
