from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Optional

from cve_collector import detail
from cve_collector.core.domain.models import Vulnerability, Repository, Commit


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
    """Fetch GHSA metadata via cve_collector's new module API.

    - Uses `detail(ghsa)` to obtain a `Vulnerability`.
    - Builds `repo_url` from vulnerability's repo attribute (expects "owner/name" or URL).
    - Picks a reasonable commit from vulnerability's commits.
    - Raises ValueError when either is missing.
    """
    # Best-effort: ensure token available to the underlying collector when provided
    if github_token and not os.environ.get("GITHUB_TOKEN"):
        os.environ["GITHUB_TOKEN"] = github_token

    v = detail(ghsa)
    if v is None:
        raise ValueError(f"GHSA not found (ghsa={ghsa})")

    # Extract repository identifier explicitly
    if not v.repositories:
        raise ValueError(f"GHSA metadata missing repositories (ghsa={ghsa})")
    repo: Repository = v.repositories[0]
    repo_url_raw = repo.url
    if repo_url_raw is None:
        owner = repo.owner
        name = repo.name
        if owner is None or name is None:
            raise ValueError(f"GHSA repository missing owner/name (ghsa={ghsa})")
        repo_url_raw = f"{owner}/{name}"
    repo_url = _normalize_repo_url(repo_url_raw)

    # Extract commit candidates explicitly
    commits: tuple[Commit, ...] = v.commits
    commit_candidates: list[str] = [c.hash for c in commits]
    commit = _choose_commit(commit_candidates)
    if not commit:
        raise ValueError(f"GHSA metadata missing commit (ghsa={ghsa})")

    return GHSAInfo(ghsa=ghsa, repo_url=repo_url, commit=commit, parent_commit=None)


