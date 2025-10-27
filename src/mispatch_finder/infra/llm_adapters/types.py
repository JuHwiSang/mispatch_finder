from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    # Type-only import to align exactly with OpenAI SDK schema
    from openai.types.responses.tool_param import McpRequireApproval


# Public provider literal
Provider = Literal["openai", "anthropic"]


@dataclass
class Toolset:
    """Declarative configuration for one remote MCP server.

    - For OpenAI: converted to Responses API tools entries
    - For Anthropic: converted to Messages API mcp_servers entries
    """

    label: str
    server_url: str
    bearer_token: str | None = None
    headers: dict[str, str] = field(default_factory=dict)
    allowed_tools: list[str] | None = None
    require_approval: "McpRequireApproval" | None = "never"


@dataclass
class TokenUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


@dataclass
class LLMResponse:
    text: str
    usage: TokenUsage | None = None
