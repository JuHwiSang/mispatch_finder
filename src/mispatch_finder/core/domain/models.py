from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


@dataclass(frozen=True)
class Repository:
    """Repository metadata for vulnerability analysis.

    Represents the minimal repository information needed for mispatch analysis.
    Extracted from external vulnerability sources (e.g., cve_collector).
    """
    owner: str
    name: str
    ecosystem: Optional[str] = None  # e.g., "npm", "pypi", "go"
    star_count: Optional[int] = None
    size_kb: Optional[int] = None  # Repository size in KB

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
    cve_id: Optional[str] = None
    summary: Optional[str] = None
    severity: Optional[str] = None  # e.g., "CRITICAL", "HIGH", "MEDIUM", "LOW"


@dataclass
class RepoContext:
    repo_url: str
    workdir_current: Optional[Path]
    workdir_previous: Optional[Path]
    commit: str
    parent_commit: Optional[str]


@dataclass
class AnalysisResult:
    ghsa: str
    provider: str
    model: str
    verdict: Optional[str]
    severity: Optional[str]
    rationale: Optional[str]
    evidence: Optional[List[Dict[str, object]]]
    poc_idea: Optional[str]
    raw_text: Optional[str]


