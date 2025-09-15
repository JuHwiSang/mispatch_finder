from __future__ import annotations

from typing import Dict, List, Optional, Protocol, runtime_checkable

from .types import Toolset, LLMResponse


@runtime_checkable
class LLMHostedMCPAdapter(Protocol):
    """Minimal interface for running a prompt with hosted MCP tool access."""

    def run(
        self,
        prompt: str,
        toolsets: List[Toolset],
        *,
        max_output_tokens: int = 800,
        request_headers: Optional[Dict[str, str]] = None,
    ) -> LLMResponse:
        """Run a request with MCP access and return normalized text + token usage."""
        raise NotImplementedError


