from __future__ import annotations

import json
import logging

from itdev_llm_adapter import Toolset
from itdev_llm_adapter.factory import get_adapter

from ...core.ports import LLMPort

logger = logging.getLogger(__name__)


class LLM:
    def __init__(self, *, provider: str, model: str, api_key: str) -> None:
        self._provider = provider
        self._model = model
        self._api_key = api_key

    def call(
        self,
        *,
        prompt: str,
        mcp_url: str,
        mcp_token: str,
    ) -> str:
        # Log LLM input with provider/model info
        logger.info("llm_input", extra={
            "payload": {
                "type": "llm_input",
                "provider": self._provider,
                "model": self._model,
                "prompt_len": len(prompt),
                "prompt": prompt,
            }
        })
        
        adapter = get_adapter(self._provider, self._model, self._api_key)
        toolset = [
            Toolset(
                label="mispatch_tools",
                server_url=mcp_url,
                bearer_token=mcp_token,
            )
        ]
        resp = adapter.run(prompt, toolset)
        text = resp.text

        # Log token usage
        usage = resp.usage
        if usage is not None:
            logger.info("llm_usage", extra={
                "payload": {
                    "type": "llm_usage",
                    "provider": self._provider,
                    "model": self._model,
                    "input_tokens": usage.input_tokens,
                    "output_tokens": usage.output_tokens,
                    "total_tokens": usage.total_tokens,
                }
            })

        # Extract JSON block if wrapped in markdown or text
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1 and end > start:
            parsed = json.loads(text[start:end+1])
            result = json.dumps(parsed, ensure_ascii=False)
        else:
            result = text
        
        # Log LLM output
        logger.info("llm_output", extra={
            "payload": {
                "type": "llm_output",
                "provider": self._provider,
                "model": self._model,
                "raw_text_len": len(result),
                "raw_text": result,
            }
        })
        
        return result
