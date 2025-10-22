from __future__ import annotations

from typing import Optional

from ..ports import LogStorePort


class LogsUseCase:
    def __init__(self, *, log_store: LogStorePort) -> None:
        self._log_store = log_store

    def execute(self, ghsa: Optional[str], verbose: bool) -> list[str]:
        if ghsa:
            return self._log_store.read_log(ghsa, verbose)
        return self._log_store.summarize_all(verbose)

