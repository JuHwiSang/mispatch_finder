from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional, Tuple

from git import Repo


def _ensure_repo(cache_dir: Path, repo_url: str, force_reclone: bool) -> Path:
    slug = repo_url.rstrip("/").split("/")[-1]
    if slug.endswith(".git"):
        slug = slug[:-4]
    base = cache_dir / "repos" / slug
    if force_reclone and base.exists():
        shutil.rmtree(base)
    if not base.exists():
        base.parent.mkdir(parents=True, exist_ok=True)
        Repo.clone_from(repo_url, base)
    return base


def _copy_repo(src_repo_dir: Path, dst_dir: Path, *, overwrite: bool) -> Repo:
    """Copy a full git repository (including .git) into dst_dir.

    If dst exists and overwrite is True, it is removed first.
    Returns a Repo opened on dst_dir.
    """
    if dst_dir.exists():
        if overwrite:
            shutil.rmtree(dst_dir)
        else:
            return Repo(dst_dir)
    dst_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src_repo_dir, dst_dir)
    return Repo(dst_dir)


def get_commit_diff_text(base_repo_dir: Path, commit: str) -> str:
    """Return unified diff text for the given commit against its first parent.

    If no parent exists, returns an empty string.
    """
    repo = Repo(base_repo_dir)
    commit_obj = repo.commit(commit)
    if not commit_obj.parents:
        return ""
    parent = commit_obj.parents[0]
    return repo.git.diff(f"{parent.hexsha}..{commit_obj.hexsha}")


def prepare_repos(
    *,
    cache_dir: Path,
    repo_url: str,
    commit: str,
    force_reclone: bool,
) -> Tuple[Optional[Path], Optional[Path]]:
    """Clone/fetch repo and prepare two working directories (current, previous).

    Strategy:
    - 'current' is the repository's present state (HEAD of the cloned repo). We do not
      check it out to the patched commit.
    - 'previous' is a copy of 'current' checked out to the parent of the patched commit
      (if a parent exists).

    Returns (workdir_current, workdir_previous).
    """
    base = _ensure_repo(cache_dir, repo_url, force_reclone)

    # Optional: ensure we can resolve the target commit (best-effort fetch not required for local tests)
    repo = Repo(base)

    work_base = cache_dir / "worktrees"
    previous = work_base / f"{base.name}-{commit[:12]}-previous"

    # current is the base repo at its present HEAD
    current = base

    # Determine parent commit of the target commit
    try:
        commit_obj = repo.commit(commit)
        parent = commit_obj.parents[0] if commit_obj.parents else None
    except Exception:
        parent = None

    if parent is not None:
        previous_repo = _copy_repo(base, previous, overwrite=force_reclone)
        previous_repo.git.checkout(parent.hexsha)
    else:
        previous = None

    return current, previous


