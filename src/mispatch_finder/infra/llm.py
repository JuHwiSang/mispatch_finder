from __future__ import annotations

from .llm_adapters import Toolset, get_adapter
from ..core.ports import LLMPort, LoggerPort


class LLM:
    def __init__(self, *, provider: str, model: str, api_key: str, logger: LoggerPort) -> None:
        self._provider = provider
        self._model = model
        self._api_key = api_key
        self._logger = logger

    def call(
        self,
        *,
        prompt: str,
        mcp_url: str,
        mcp_token: str,
    ) -> str:
        # Log LLM input with provider/model info
        self._logger.info(
            "llm_input",
            type="llm_input",
            provider=self._provider,
            model=self._model,
            prompt_len=len(prompt),
            prompt=prompt,
        )

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
            self._logger.info(
                "llm_usage",
                type="llm_usage",
                provider=self._provider,
                model=self._model,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                total_tokens=usage.total_tokens,
            )

        # Log LLM output
        self._logger.info(
            "llm_output",
            type="llm_output",
            provider=self._provider,
            model=self._model,
            raw_text_len=len(text),
            raw_text=text,
        )

        return text
