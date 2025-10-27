from __future__ import annotations

from typing import Union, Optional

from ..ports import VulnerabilityDataPort
from ..domain.models import Vulnerability


class ListUseCase:
    def __init__(
        self,
        *,
        vuln_data: VulnerabilityDataPort,
        limit: int,
        ecosystem: str = "npm",
        detailed: bool = False,
        filter_expr: Optional[str] = None,
    ) -> None:
        self._vuln_data = vuln_data
        self._limit = limit
        self._ecosystem = ecosystem
        self._detailed = detailed
        self._filter_expr = filter_expr

    def execute(self) -> list[str]:
        return self._vuln_data.list_vulnerabilities(
            limit=self._limit,
            ecosystem=self._ecosystem,
            detailed=self._detailed,
            filter_expr=self._filter_expr,
        )

