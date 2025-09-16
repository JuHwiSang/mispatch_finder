from __future__ import annotations

from typing import List, Optional, Dict

import anthropic
from anthropic.types.beta import BetaRequestMCPServerURLDefinitionParam

from itdev_llm_adapter.types import Toolset, LLMResponse, TokenUsage


class AnthropicHostedMCPAdapter:
    """Anthropic Messages API adapter (Claude Sonnet, etc.).

    - Registers MCP servers via mcp_servers=[...]
    - Enables beta via betas=["mcp-client-2025-04-04"]
    - Reads ANTHROPIC_API_KEY from environment via anthropic.Anthropic()
    """

    def __init__(self, model: str, api_key: str) -> None:
        self.model = model
        self._client = anthropic.Anthropic(api_key=api_key)

    def run(
        self,
        prompt: str,
        toolsets: List[Toolset],
        *,
        max_output_tokens: int = 800,
        request_headers: Optional[Dict[str, str]] = None,
    ) -> LLMResponse:
        mcp_servers: List[BetaRequestMCPServerURLDefinitionParam] = []
        for toolset in toolsets:
            server: BetaRequestMCPServerURLDefinitionParam = {
                "type": "url",
                "name": toolset.label,
                "url": toolset.server_url,
            }
            if toolset.bearer_token:
                server["authorization_token"] = toolset.bearer_token
            if toolset.allowed_tools:
                server["tool_configuration"] = {"allowed_tools": toolset.allowed_tools}
            mcp_servers.append(server)

        message = self._client.beta.messages.create(
            model=self.model,
            max_tokens=max_output_tokens,
            messages=[{"role": "user", "content": prompt}],
            mcp_servers=mcp_servers,
            betas=["mcp-client-2025-04-04"],
        )
        # message.content is a list of content blocks; we only join text blocks
        texts: List[str] = []
        for block in message.content:
            try:
                if block.type == "text":
                    texts.append(block.text)
            except AttributeError:
                continue
        # usage tokens
        u = message.usage
        iu = u.input_tokens if u is not None else None
        ou = u.output_tokens if u is not None else None
        tt = (iu or 0) + (ou or 0) if (iu is not None or ou is not None) else None
        usage = TokenUsage(input_tokens=iu, output_tokens=ou, total_tokens=tt)
        return LLMResponse(text="".join(texts) if texts else str(message), usage=usage)


