from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from cve_collector import CVECollector


@dataclass
class GHSAInfo:
    ghsa: str
    repo_url: str
    commit: str
    parent_commit: Optional[str] = None


def _normalize_repo_url(repo: str) -> str:
    """Normalize various repo notations to an https GitHub URL.

    Accepts:
    - "owner/name"
    - "https://github.com/owner/name[.git]"
    - "git@github.com:owner/name[.git]"
    """
    if repo.startswith("http://") or repo.startswith("https://"):
        return repo[:-4] if repo.endswith(".git") else repo
    if repo.startswith("git@github.com:"):
        owner_name = repo.split(":", 1)[1]
        if owner_name.endswith(".git"):
            owner_name = owner_name[:-4]
        return f"https://github.com/{owner_name}"
    return f"https://github.com/{repo}"


def _choose_commit(commits: list[str]) -> Optional[str]:
    """Choose a reasonable commit SHA from a list: prefer full 40-hex."""
    valid = [c for c in commits if re.fullmatch(r"[0-9a-fA-F]{7,40}", c)]
    if not valid:
        return None
    return max(valid, key=len)


def fetch_ghsa_metadata(ghsa: str, *, github_token: Optional[str]) -> GHSAInfo:
    """Fetch GHSA metadata via cve_collector using its CVE structure.

    - Builds `repo_url` from CVE.repo (expects "owner/name").
    - Picks the first commit from CVE.commits.
    - Raises ValueError when either is missing.
    """
    collector = CVECollector(github_token=github_token or "")
    cve = collector.collect_one(ghsa)

    if not cve.repo:
        raise ValueError(f"GHSA metadata missing repo (ghsa={ghsa})")
    repo_url = _normalize_repo_url(cve.repo)

    commit = _choose_commit(cve.commits)
    if not commit:
        raise ValueError(f"GHSA metadata missing commit (ghsa={ghsa})")

    return GHSAInfo(
        ghsa=ghsa,
        repo_url=repo_url,
        commit=commit,
        parent_commit=None,
    )


