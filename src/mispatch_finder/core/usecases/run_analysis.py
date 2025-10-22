from __future__ import annotations

from typing import Dict

from ..ports import ResultStorePort
from ..services import AnalysisOrchestrator


class RunAnalysisUseCase:
    """Use case for running vulnerability analysis.

    Thin orchestration layer that delegates to AnalysisOrchestrator
    and persists results.
    """

    def __init__(
        self,
        *,
        orchestrator: AnalysisOrchestrator,
        store: ResultStorePort,
    ) -> None:
        self._orchestrator = orchestrator
        self._store = store

    def execute(self, *, ghsa: str, force_reclone: bool = False) -> Dict[str, object]:
        """Execute analysis workflow.

        Args:
            ghsa: GHSA identifier
            force_reclone: Whether to force re-clone repository

        Returns:
            Analysis result as dictionary
        """
        # Run analysis (orchestrator handles all business logic)
        result = self._orchestrator.analyze(ghsa=ghsa, force_reclone=force_reclone)

        # Persist result
        self._store.save(ghsa, result)

        return result
