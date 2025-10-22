from __future__ import annotations

from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from ..ports import RepositoryPort


@dataclass
class DiffResult:
    """Result of diff generation with metadata."""
    full_text: str
    truncated_text: str
    full_len: int
    included_len: int
    was_truncated: bool


class DiffService:
    """Domain service for generating and processing diffs.

    Handles diff generation, truncation, and metadata tracking.
    """

    def __init__(self, *, repo: RepositoryPort, max_chars: int) -> None:
        self._repo = repo
        self._max_chars = max_chars

    def generate_diff(
        self,
        *,
        workdir: Optional[Path],
        commit: str,
    ) -> DiffResult:
        """Generate diff for a commit with optional truncation.

        Args:
            workdir: Working directory containing the repository
            commit: Commit hash to generate diff for

        Returns:
            DiffResult with full and truncated diff text
        """
        # Get full diff
        if workdir is None:
            full_text = ""
        else:
            full_text = self._repo.get_diff(workdir=workdir, commit=commit)

        # Truncate if needed (middle-truncation strategy)
        truncated_text = full_text
        was_truncated = False

        if len(full_text) > self._max_chars:
            was_truncated = True
            head = full_text[: self._max_chars // 2]
            tail = full_text[-(self._max_chars - len(head)) :]
            truncated_text = head + "\n...\n" + tail

        return DiffResult(
            full_text=full_text,
            truncated_text=truncated_text,
            full_len=len(full_text),
            included_len=len(truncated_text),
            was_truncated=was_truncated,
        )
