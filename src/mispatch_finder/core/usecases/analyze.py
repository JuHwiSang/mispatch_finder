from __future__ import annotations

from ..services import AnalysisOrchestrator


class AnalyzeUseCase:
    """Use case for analyzing vulnerability.

    Thin orchestration layer that delegates to AnalysisOrchestrator.
    """

    def __init__(
        self,
        *,
        orchestrator: AnalysisOrchestrator,
    ) -> None:
        self._orchestrator = orchestrator

    def execute(self, *, ghsa: str, force_reclone: bool = False) -> dict[str, object]:
        """Execute analysis workflow.

        Args:
            ghsa: GHSA identifier
            force_reclone: Whether to force re-clone repository

        Returns:
            Analysis result as dictionary
        """
        # Run analysis (orchestrator handles all business logic)
        return self._orchestrator.analyze(ghsa=ghsa, force_reclone=force_reclone)
