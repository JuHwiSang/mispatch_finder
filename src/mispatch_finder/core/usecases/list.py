from __future__ import annotations

from ..ports import VulnerabilityDataPort


class ListUseCase:
    def __init__(self, *, vuln_repo: VulnerabilityDataPort, limit: int, ecosystem: str = "npm") -> None:
        self._vuln_repo = vuln_repo
        self._limit = limit
        self._ecosystem = ecosystem

    def execute(self) -> list[str]:
        return self._vuln_repo.list_ids(self._limit, ecosystem=self._ecosystem)

