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
    print(f"base: {base}")
    print(f"force_reclone: {force_reclone}")
    print(f"base.exists(): {base.exists()}")
    if force_reclone and base.exists():
        shutil.rmtree(base)
    if not base.exists():
        base.parent.mkdir(parents=True, exist_ok=True)
        print(f"Repo.clone_from: {repo_url} -> {base}")
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
    parent_commit: Optional[str],
    force_reclone: bool,
) -> Tuple[Optional[Path], Optional[Path]]:
    """Clone/fetch repo and checkout two working directories (post, pre).

    Returns (workdir_post, workdir_pre).
    """
    base = _ensure_repo(cache_dir, repo_url, force_reclone)

    work_base = cache_dir / "worktrees"
    post = work_base / f"{base.name}-{commit[:12]}-post"
    pre = work_base / f"{base.name}-{commit[:12]}-pre"

    repo = Repo(base)

    # Derive parent commit if missing
    if not parent_commit:
        try:
            commit_obj = repo.commit(commit)
            if commit_obj.parents:
                parent_commit = commit_obj.parents[0].hexsha
        except Exception:
            parent_commit = None

    # Create independent working copies by copying the entire repo (including .git)
    post_repo = _copy_repo(base, post, overwrite=force_reclone)
    post_repo.git.checkout(commit)

    if parent_commit:
        pre_repo = _copy_repo(base, pre, overwrite=force_reclone)
        pre_repo.git.checkout(parent_commit)
    else:
        pre = None

    return post, pre


