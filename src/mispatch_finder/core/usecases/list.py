from __future__ import annotations

from typing import cast

from ..domain.models import Vulnerability
from ..ports import VulnerabilityDataPort, AnalysisStorePort


class ListUseCase:
    """Use case for listing vulnerabilities.

    Separates DI concerns (dependencies) from runtime parameters.
    Business logic: Fetch vulnerabilities, filter out analyzed ones, apply limit.
    """

    def __init__(self, *, vuln_data: VulnerabilityDataPort, analysis_store: AnalysisStorePort) -> None:
        self._vuln_data = vuln_data
        self._analysis_store = analysis_store

    def execute(
        self,
        *,
        limit: int | None = None,
        ecosystem: str = "npm",
        detailed: bool = False,
        filter_expr: str | None = None,
        include_analyzed: bool = False,
    ) -> list[str] | list[Vulnerability]:
        """Execute the use case.

        Args:
            limit: Maximum number of items to return (after filtering). Defaults to 10 if None.
            ecosystem: Ecosystem filter (e.g., "npm", "pypi")
            detailed: If True, return full Vulnerability objects; if False, return GHSA IDs only
            filter_expr: Optional filter expression (e.g., "stars > 1000")
            include_analyzed: If True, include already analyzed vulnerabilities

        Returns:
            list[str]: GHSA IDs when detailed=False
            list[Vulnerability]: Vulnerability objects when detailed=True
        """
        # Default limit
        if limit is None:
            limit = 10

        # If include_analyzed=True, collect without filtering
        if include_analyzed:
            result: list[str] | list[Vulnerability] = []
            for item in self._vuln_data.list_vulnerabilities_iter(
                ecosystem=ecosystem,
                detailed=detailed,
                filter_expr=filter_expr,
            ):
                result.append(cast(Vulnerability, item))
                if len(result) >= limit:
                    break
            return result

        # Filter out analyzed items using lazy iteration
        analyzed_ids = self._analysis_store.get_analyzed_ids()
        result_filtered: list[str] | list[Vulnerability] = []

        for item in self._vuln_data.list_vulnerabilities_iter(
            ecosystem=ecosystem,
            detailed=detailed,
            filter_expr=filter_expr,
        ):
            # Extract GHSA ID for checking
            if detailed:
                ghsa_id = cast(str, cast(Vulnerability, item).ghsa_id)
            else:
                ghsa_id = cast(str, item)

            # Skip if already analyzed
            if ghsa_id in analyzed_ids:
                continue

            result_filtered.append(cast(Vulnerability, item))
            if len(result_filtered) >= limit:
                break

        return result_filtered

