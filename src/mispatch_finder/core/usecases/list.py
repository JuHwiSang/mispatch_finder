from __future__ import annotations

from ..domain.models import Vulnerability
from ..ports import VulnerabilityDataPort


class ListUseCase:
    """Use case for listing vulnerabilities.

    Separates DI concerns (dependencies) from runtime parameters.
    """

    def __init__(self, *, vuln_data: VulnerabilityDataPort) -> None:
        self._vuln_data = vuln_data

    def execute(
        self,
        *,
        limit: int,
        ecosystem: str = "npm",
        detailed: bool = False,
        filter_expr: str | None = None,
    ) -> list[str] | list[Vulnerability]:
        """Execute the use case.

        Args:
            limit: Maximum number of items to return
            ecosystem: Ecosystem filter (e.g., "npm", "pypi")
            detailed: If True, return full Vulnerability objects; if False, return GHSA IDs only
            filter_expr: Optional filter expression (e.g., "stars > 1000")

        Returns:
            list[str]: GHSA IDs when detailed=False
            list[Vulnerability]: Vulnerability objects when detailed=True
        """
        return self._vuln_data.list_vulnerabilities(
            limit=limit,
            ecosystem=ecosystem,
            detailed=detailed,
            filter_expr=filter_expr,
        )

