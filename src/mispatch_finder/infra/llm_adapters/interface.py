from __future__ import annotations

from typing import Protocol, runtime_checkable

from .types import LLMResponse, Toolset


@runtime_checkable
class LLMHostedMCPAdapter(Protocol):
    """Minimal interface for running a prompt with hosted MCP tool access."""

    def run(
        self,
        prompt: str,
        toolsets: list[Toolset],
        *,
        max_output_tokens: int = 800,
        request_headers: dict[str, str] | None = None,
    ) -> LLMResponse:
        """Run a request with MCP access and return normalized text + token usage."""
        raise NotImplementedError
