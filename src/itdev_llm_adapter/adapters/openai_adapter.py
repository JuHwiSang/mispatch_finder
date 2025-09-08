from __future__ import annotations

from typing import Dict, List, Optional

from openai import OpenAI
from openai.types.responses.tool_param import ToolParam

from itdev_llm_adapter.types import Toolset


class OpenAIHostedMCPAdapter:
    """OpenAI Responses API adapter (o3, gpt-4o, etc.).

    - Uses tools=[{"type": "mcp", ...}] with optional headers/approval fields
    - Reads OPENAI_API_KEY from environment via OpenAI()
    """

    def __init__(self, model: str, api_key: str) -> None:
        self.model = model
        self._client = OpenAI(api_key=api_key)

    def run(
        self,
        prompt: str,
        toolsets: List[Toolset],
        *,
        max_output_tokens: int = 800,
        request_headers: Optional[Dict[str, str]] = None,
    ) -> str:
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
            if toolset.require_approval is not None:
                tool_obj["require_approval"] = toolset.require_approval
            if headers:
                tool_obj["headers"] = headers

            tools.append(tool_obj)

        response = self._client.responses.create(
            model=self.model,
            input=prompt,
            tools=tools,
            tool_choice="auto",
            extra_headers=request_headers or None,
        )
        return getattr(response, "output_text", None) or str(response)


