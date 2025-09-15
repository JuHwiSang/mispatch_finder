from __future__ import annotations

from typing import Dict, List, Optional

from openai import OpenAI
from openai.types.responses.tool_param import ToolParam

from itdev_llm_adapter.types import Toolset, LLMResponse, TokenUsage


class OpenAIHostedMCPAdapter:
    """OpenAI Responses API adapter (o3, gpt-4o, etc.).

    - Uses tools=[{"type": "mcp", ...}] with optional headers/approval fields
    - Reads OPENAI_API_KEY from environment via OpenAI()
    """

    def __init__(self, model: str, api_key: str) -> None:
        self.model = model
        self._client = OpenAI(api_key=api_key)
        self.last_usage: Optional[Dict[str, int]] = None

    def run(
        self,
        prompt: str,
        toolsets: List[Toolset],
        *,
        max_output_tokens: int = 800,
        request_headers: Optional[Dict[str, str]] = None,
    ) -> LLMResponse:
        request_headers = request_headers or {}

        tools: List[ToolParam] = []
        for toolset in toolsets:
            headers = dict(toolset.headers)
            if toolset.bearer_token and "Authorization" not in headers:
                headers["Authorization"] = f"Bearer {toolset.bearer_token}"

            tool_obj: ToolParam = {
                "type": "mcp",
                "server_label": toolset.label,
                "server_url": toolset.server_url,
            }
            if toolset.allowed_tools:
                tool_obj["allowed_tools"] = toolset.allowed_tools
            if headers:
                tool_obj["headers"] = headers
            if toolset.require_approval is not None:
                tool_obj["require_approval"] = toolset.require_approval
            else:
                tool_obj["require_approval"] = "never" # 기본값은 never, 즉 '승인 없이 사용'

            tools.append(tool_obj)

        response = self._client.responses.create(
            model=self.model,
            input=prompt,
            tools=tools,
            tool_choice="auto",
            extra_headers=request_headers or None,
            store=True,
        )
        usage = None
        if hasattr(response, "usage") and response.usage is not None:
            u = response.usage
            usage = TokenUsage(
                input_tokens=getattr(u, "input_tokens", None) if isinstance(getattr(u, "input_tokens", None), int) else None,
                output_tokens=getattr(u, "output_tokens", None) if isinstance(getattr(u, "output_tokens", None), int) else None,
                total_tokens=getattr(u, "total_tokens", None) if isinstance(getattr(u, "total_tokens", None), int) else None,
            )
        return LLMResponse(text=response.output_text or str(response), usage=usage)


