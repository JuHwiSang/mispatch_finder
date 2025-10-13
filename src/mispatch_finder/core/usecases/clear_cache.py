from __future__ import annotations

from ..ports import CachePort, VulnerabilityRepositoryPort


class ClearCacheUseCase:
    def __init__(
        self,
        *,
        cache: CachePort,
        vuln_repo: VulnerabilityRepositoryPort,
    ) -> None:
        self._cache = cache
        self._vuln_repo = vuln_repo

    def execute(self) -> None:
        self._cache.clear_all()
        self._vuln_repo.clear_cache()

