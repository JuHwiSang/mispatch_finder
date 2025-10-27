from __future__ import annotations

import secrets
from pathlib import Path
from typing import Protocol, Optional, Dict, Any
from dataclasses import dataclass

from .domain.models import Vulnerability


class VulnerabilityDataPort(Protocol):
    """Port for fetching vulnerability metadata and listing vulnerabilities.

    This port abstracts the cve_collector library, providing domain model conversion:
    - cve_collector.detail(id) → domain.Vulnerability
    - cve_collector.list_vulnerabilities() → list[domain.Vulnerability]
    - cve_collector.clear_cache(prefix) → cache management
    """

    def fetch_metadata(self, ghsa: str) -> Vulnerability:
        """Fetch detailed metadata for a specific GHSA.

        Returns:
            Vulnerability domain model with repository and commit context

        Raises:
            ValueError: If GHSA not found or metadata is invalid
        """
        ...

    def list_ids(self, limit: int, ecosystem: str = "npm") -> list[str]:
        """List available GHSA identifiers (ID only, no metadata)."""
        ...

    def clear_cache(self, prefix: Optional[str] = None) -> None:
        """Clear cached vulnerability data.

        Args:
            prefix: Cache key prefix ('osv', 'gh_repo', or None for all)
        """
        ...


class RepositoryPort(Protocol):
    """Port for git repository operations."""
    
    def prepare_workdirs(
        self,
        *,
        repo_url: str,
        commit: str,
        force_reclone: bool,
    ) -> tuple[Optional[Path], Optional[Path]]:
        """Prepare and return (current_workdir, previous_workdir)."""
        ...

    def get_diff(self, *, workdir: Path, commit: str) -> str:
        """Get unified diff for a commit."""
        ...


@dataclass
class MCPServerContext:
    """MCP server runtime context."""
    local_url: str
    public_url: str
    has_current: bool
    has_previous: bool
    
    def cleanup(self) -> None:
        """Cleanup hook called by context manager."""
        pass


class MCPServerPort(Protocol):
    """Port for MCP server lifecycle."""
    
    def start_servers(
        self,
        *,
        current_workdir: Optional[Path],
        previous_workdir: Optional[Path],
        auth_token: str,
    ) -> MCPServerContext:
        """Start child servers, aggregator, and tunnel. Return context."""
        ...


class LLMPort(Protocol):
    """Port for LLM inference."""
    
    def call(
        self,
        *,
        prompt: str,
        mcp_url: str,
        mcp_token: str,
    ) -> str:
        """Call LLM with prompt and MCP context."""
        ...


class ResultStorePort(Protocol):
    """Port for persisting analysis results."""
    
    def save(self, ghsa: str, payload: dict) -> None:
        ...

    def load(self, ghsa: str) -> Optional[dict]:
        ...

    def list_all(self) -> list[dict]:
        ...


class LogStorePort(Protocol):
    """Port for reading log files."""
    
    def read_log(self, ghsa: str, verbose: bool) -> list[str]:
        """Read and format log for a single GHSA."""
        ...

    def summarize_all(self, verbose: bool) -> list[str]:
        """Summarize all logs as table."""
        ...


class CachePort(Protocol):
    """Port for cache management."""
    
    def clear_all(self) -> None:
        """Clear all application caches."""
        ...


class TokenGeneratorPort(Protocol):
    def generate(self) -> str:
        ...


class LoggerPort(Protocol):
    """Port for structured logging.

    Provides structured logging with optional payload data.
    Implementations should handle JSON serialization and formatting.
    """

    def debug(self, message: str, payload: Optional[Dict[str, Any]] = None) -> None:
        ...

    def info(self, message: str, payload: Optional[Dict[str, Any]] = None) -> None:
        ...

    def warning(self, message: str, payload: Optional[Dict[str, Any]] = None) -> None:
        ...

    def error(self, message: str, payload: Optional[Dict[str, Any]] = None, exc_info: bool = False) -> None:
        ...

    def exception(self, message: str, payload: Optional[Dict[str, Any]] = None) -> None:
        ...


class DefaultTokenGenerator:
    def generate(self) -> str:
        return secrets.token_urlsafe(32)
