from __future__ import annotations

from ..ports import VulnerabilityDataPort


class ListUseCase:
    def __init__(self, *, vuln_data: VulnerabilityDataPort, limit: int, ecosystem: str = "npm") -> None:
        self._vuln_data = vuln_data
        self._limit = limit
        self._ecosystem = ecosystem

    def execute(self) -> list[str]:
        return self._vuln_data.list_ids(self._limit, ecosystem=self._ecosystem)

