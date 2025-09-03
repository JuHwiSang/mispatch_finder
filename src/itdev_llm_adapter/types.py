from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional, Union


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
    bearer_token: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)
    allowed_tools: Optional[List[str]] = None
    require_approval: Union[Literal["never"], Dict[str, bool], None] = "never"


