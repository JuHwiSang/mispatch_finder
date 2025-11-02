"""Domain exceptions for mispatch_finder."""

from __future__ import annotations


class GHSANotFoundError(Exception):
    """Raised when a GHSA identifier does not exist in the vulnerability database.

    This exception is specifically for cases where the GHSA ID is invalid or
    the vulnerability data is not available (e.g., 404 from API).
    """

    def __init__(self, ghsa: str, message: str | None = None) -> None:
        self.ghsa = ghsa
        if message is None:
            message = f"GHSA not found: {ghsa}"
        super().__init__(message)
