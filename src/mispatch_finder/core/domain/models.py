from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Repository:
    """Repository metadata for vulnerability analysis.

    Represents the minimal repository information needed for mispatch analysis.
    Extracted from external vulnerability sources (e.g., cve_collector).
    """
    owner: str
    name: str
    ecosystem: str | None = None  # e.g., "npm", "pypi", "go"
    star_count: int | None = None
    size_kb: int | None = None  # Repository size in KB

    @property
    def slug(self) -> str:
        """Returns owner/name format."""
        return f"{self.owner}/{self.name}"

    @property
    def url(self) -> str:
        """Returns GitHub HTTPS URL."""
        return f"https://github.com/{self.slug}"


@dataclass(frozen=True)
class Vulnerability:
    """Core vulnerability domain model.

    Represents a security vulnerability with repository and commit context.
    This is the primary aggregate root for vulnerability analysis.
    """
    ghsa_id: str
    repository: Repository
    commit_hash: str

    # Optional enrichment data
    cve_id: str | None = None
    summary: str | None = None
    severity: str | None = None  # e.g., "CRITICAL", "HIGH", "MEDIUM", "LOW"


@dataclass
class RepoContext:
    repo_url: str
    workdir_current: Path | None
    workdir_previous: Path | None
    commit: str
    parent_commit: str | None


@dataclass
class AnalysisResult:
    ghsa: str
    provider: str
    model: str
    verdict: str | None
    severity: str | None
    rationale: str | None
    evidence: list[dict[str, object]] | None
    poc_idea: str | None
    raw_text: str | None


