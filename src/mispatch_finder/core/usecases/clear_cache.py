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

    def execute(self, vuln_cache_prefix: str | None = None) -> None:
        """Clear application caches.

        Args:
            vuln_cache_prefix: Optional prefix for vulnerability cache clearing:
                - None: Clear all vulnerability caches
                - "osv": Clear only OSV data
                - "gh_repo": Clear only GitHub repository metadata
        """
        self._cache.clear_all()
        self._vuln_repo.clear_cache(prefix=vuln_cache_prefix)

