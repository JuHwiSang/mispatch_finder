from __future__ import annotations

import shutil
from pathlib import Path

from git import Repo

from ..core.ports import RepositoryPort


class Repository:
    def __init__(self, *, cache_dir: Path) -> None:
        self._cache_dir = cache_dir

    def prepare_workdirs(
        self,
        *,
        repo_url: str,
        commit: str,
        force_reclone: bool,
    ) -> tuple[Path | None, Path | None]:
        """Clone repo and prepare current/previous workdirs."""
        base = self._ensure_repo(repo_url, force_reclone)
        repo = Repo(base)

        # current = base repo at HEAD
        current = base

        # previous = copy at parent of target commit
        commit_obj = repo.commit(commit)
        parent = commit_obj.parents[0] if commit_obj.parents else None

        if parent is not None:
            work_base = self._cache_dir / "worktrees"
            previous = work_base / f"{base.name}-{commit[:12]}-previous"
            previous_repo = self._copy_repo(base, previous, overwrite=force_reclone)
            previous_repo.git.checkout(parent.hexsha)
        else:
            previous = None

        return current, previous

    def get_diff(self, *, workdir: Path, commit: str) -> str:
        """Return unified diff for commit against its parent."""
        repo = Repo(workdir)
        commit_obj = repo.commit(commit)
        if not commit_obj.parents:
            return ""
        parent = commit_obj.parents[0]
        return repo.git.diff(f"{parent.hexsha}..{commit_obj.hexsha}")

    def _ensure_repo(self, repo_url: str, force_reclone: bool) -> Path:
        slug = repo_url.rstrip("/").split("/")[-1]
        if slug.endswith(".git"):
            slug = slug[:-4]
        base = self._cache_dir / "repos" / slug
        if force_reclone and base.exists():
            shutil.rmtree(base)
        if not base.exists():
            base.parent.mkdir(parents=True, exist_ok=True)
            Repo.clone_from(repo_url, base)
        return base

    def _copy_repo(self, src: Path, dst: Path, *, overwrite: bool) -> Repo:
        if dst.exists():
            if overwrite:
                shutil.rmtree(dst)
            else:
                return Repo(dst)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dst)
        return Repo(dst)
