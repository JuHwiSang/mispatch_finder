from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class RepoContext:
    repo_url: str
    workdir_post: Optional[Path]
    workdir_pre: Optional[Path]
    commit: str
    parent_commit: Optional[str]


@dataclass
class AnalysisRequest:
    ghsa: str
    provider: str
    model: str
    api_key: str
    github_token: str
    force_reclone: bool = False


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


