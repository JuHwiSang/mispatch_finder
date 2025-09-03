from pathlib import Path
from git import Repo

from mispatch_finder.infra.git_repo import get_commit_diff_text, prepare_repos


def _init_repo_with_two_commits(tmp_path: Path) -> tuple[Path, str, str]:
    repo_dir = tmp_path / "repo"
    repo = Repo.init(repo_dir)
    (repo_dir / "a.txt").write_text("one", encoding="utf-8")
    repo.index.add(["a.txt"])
    c1 = repo.index.commit("first").hexsha
    (repo_dir / "a.txt").write_text("one\ntwo", encoding="utf-8")
    repo.index.add(["a.txt"])
    c2 = repo.index.commit("second").hexsha
    return repo_dir, c1, c2


def test_get_commit_diff_text(tmp_path):
    base, c1, c2 = _init_repo_with_two_commits(tmp_path)
    diff = get_commit_diff_text(base, c2)
    assert "+two" in diff
    # first commit has no parent, should be empty
    assert get_commit_diff_text(base, c1) == ""


def test_prepare_repos_worktrees(tmp_path):
    base, c1, c2 = _init_repo_with_two_commits(tmp_path)
    post, pre = prepare_repos(
        cache_dir=tmp_path,
        repo_url=base.as_posix(),
        commit=c2,
        parent_commit=c1,
        force_reclone=False,
    )
    assert post and post.exists()
    assert pre and pre.exists()

