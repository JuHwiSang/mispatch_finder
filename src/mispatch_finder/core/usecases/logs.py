from __future__ import annotations

from ..ports import AnalysisStorePort


class LogsUseCase:
    def __init__(self, *, analysis_store: AnalysisStorePort) -> None:
        self._analysis_store = analysis_store

    def execute(self, ghsa: str | None, verbose: bool) -> list[str]:
        if ghsa:
            return self._analysis_store.read_log(ghsa, verbose)
        return self._analysis_store.summarize_all(verbose)

