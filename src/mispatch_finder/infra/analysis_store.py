from __future__ import annotations

from pathlib import Path

from ..core.ports import AnalysisStorePort
from .logging.log_summary import (
    format_single_summary,
    format_summary_table,
    parse_log_details,
    summarize_logs,
)


class AnalysisStore:
    """Store for reading analysis logs.

    Reads JSONL log files written by AnalysisLogger.
    Each line is a JSON log entry with message and optional payload.
    """

    def __init__(self, *, analysis_dir: Path) -> None:
        """Initialize the analysis store.

        Args:
            analysis_dir: Directory containing analysis .jsonl log files
        """
        self._analysis_dir = analysis_dir

    def read_log(self, ghsa: str, verbose: bool) -> list[str]:
        """Read and format log for a single GHSA.

        Args:
            ghsa: GHSA identifier
            verbose: If True, return raw log lines; if False, return summary

        Returns:
            List of formatted log lines

        Raises:
            FileNotFoundError: If log file doesn't exist
        """
        log_fp = self._analysis_dir / f"{ghsa}.jsonl"
        if not log_fp.exists():
            raise FileNotFoundError(f"Log file not found: {log_fp}")

        if verbose:
            return log_fp.read_text(encoding="utf-8").splitlines()

        details = parse_log_details(log_fp)
        return format_single_summary(details)

    def summarize_all(self, verbose: bool) -> list[str]:
        """Summarize all logs as table.

        Args:
            verbose: If True, include detailed information

        Returns:
            List of formatted summary lines
        """
        summaries = summarize_logs(self._analysis_dir, verbose=verbose)
        return format_summary_table(summaries, verbose=verbose)

    def get_analyzed_ids(self) -> set[str]:
        """Return set of GHSA IDs that have been analyzed (done=True).

        Returns:
            Set of GHSA identifiers that have completed analysis
        """
        summaries = summarize_logs(self._analysis_dir, verbose=False)
        return {ghsa_id for ghsa_id, summary in summaries.items() if summary.done}
