from __future__ import annotations

import secrets
from pathlib import Path
from typing import Protocol, Optional
from dataclasses import dataclass


@dataclass
class GHSAMeta:
    ghsa: str
    repo_url: str
    commit: str
    parent_commit: Optional[str]
    repo_size_kb: Optional[int] = None  # Repository size in KB, if available


class VulnerabilityRepositoryPort(Protocol):
    """Port for fetching vulnerability metadata and listing vulnerabilities."""
    
    def fetch_metadata(self, ghsa: str) -> GHSAMeta:
        """Fetch detailed metadata for a specific GHSA."""
        ...

    def list_ids(self, limit: int) -> list[str]:
        """List available GHSA identifiers (ID only, no metadata)."""
        ...
    
    def list_with_metadata(self, limit: int) -> list[GHSAMeta]:
        """List vulnerabilities with full metadata (more efficient than fetching individually)."""
        ...

    def clear_cache(self) -> None:
        """Clear cached vulnerability data."""
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


class DefaultTokenGenerator:
    def generate(self) -> str:
        return secrets.token_urlsafe(32)
