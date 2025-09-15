from __future__ import annotations

import json

from itdev_llm_adapter import Toolset
from itdev_llm_adapter.factory import get_adapter
from typing import Optional


def call_llm(
    *,
    provider: str,
    model: str,
    api_key: str,
    mcp_url: str,
    mcp_token: str,
    prompt: str,
    usage_sink: Optional[object] = None,
) -> str:
    adapter = get_adapter(provider, model, api_key)
    ts = [
        Toolset(
            label="mispatch_tools",
            server_url=mcp_url,
            bearer_token=mcp_token,
        )
    ]
    resp = adapter.run(prompt, ts)
    text = resp.text
    # Best-effort: if the model returned markup or extra text, try to extract JSON block
    try:
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1 and end > start:
            parsed = json.loads(text[start:end+1])
            return json.dumps(parsed, ensure_ascii=False)
    except Exception:
        pass
    return text


