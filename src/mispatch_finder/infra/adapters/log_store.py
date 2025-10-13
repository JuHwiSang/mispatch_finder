from __future__ import annotations

from pathlib import Path
from typing import Optional

from ...core.ports import LogStorePort
from ...shared.log_summary import summarize_logs, format_summary_table, parse_log_details, format_single_summary


class LogStore:
    def __init__(self, *, logs_dir: Path) -> None:
        self._logs_dir = logs_dir

    def read_log(self, ghsa: str, verbose: bool) -> list[str]:
        log_fp = self._logs_dir / f"{ghsa}.jsonl"
        if not log_fp.exists():
            raise FileNotFoundError(f"Log file not found: {log_fp}")
        
        if verbose:
            return log_fp.read_text(encoding="utf-8").splitlines()
        
        details = parse_log_details(log_fp)
        return format_single_summary(details)

    def summarize_all(self, verbose: bool) -> list[str]:
        summaries = summarize_logs(self._logs_dir, verbose=verbose)
        return format_summary_table(summaries, verbose=verbose)

