from __future__ import annotations

from ..ports import VulnerabilityRepositoryPort


class ListGHSAUseCase:
    def __init__(self, *, vuln_repo: VulnerabilityRepositoryPort, limit: int) -> None:
        self._vuln_repo = vuln_repo
        self._limit = limit

    def execute(self) -> list[str]:
        return self._vuln_repo.list_ids(self._limit)

