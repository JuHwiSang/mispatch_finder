from __future__ import annotations

from ..domain.prompt import build_prompt
from ..ports import RepositoryPort, VulnerabilityDataPort
from ..services import DiffService


class PromptUseCase:
    """Use case for generating and displaying the analysis prompt.

    Shows the raw prompt that would be sent to the LLM for a given GHSA.
    """

    def __init__(
        self,
        *,
        vuln_data: VulnerabilityDataPort,
        repo: RepositoryPort,
        diff_service: DiffService,
    ) -> None:
        self._vuln_data = vuln_data
        self._repo = repo
        self._diff_service = diff_service

    def execute(self, *, ghsa: str, force_reclone: bool = False) -> str:
        """Generate and return the analysis prompt.

        Args:
            ghsa: GHSA identifier
            force_reclone: Whether to force re-clone repository

        Returns:
            The complete prompt string
        """
        # 1) Fetch GHSA metadata
        vuln = self._vuln_data.fetch_metadata(ghsa)

        # 2) Prepare repositories to check availability
        current, previous = self._repo.prepare_workdirs(
            repo_url=vuln.repository.url,
            commit=vuln.commit_hash,
            force_reclone=force_reclone,
        )

        # 3) Generate diff
        base_worktree = current or previous
        diff_result = self._diff_service.generate_diff(
            workdir=base_worktree,
            commit=vuln.commit_hash,
        )

        # 4) Build and return prompt
        return build_prompt(
            ghsa=ghsa,
            repo_url=vuln.repository.url,
            commit=vuln.commit_hash,
            has_previous=previous is not None,
            has_current=current is not None,
            diff_text=diff_result.truncated_text,
        )
