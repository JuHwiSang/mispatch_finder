from pathlib import Path
from git import Repo

from mispatch_finder.infra.adapters.repository import Repository


def test_repository_adapter_prepare_workdirs(tmp_path):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    
    # Create a simple repo
    repo_dir = tmp_path / "source"
    repo = Repo.init(repo_dir)
    (repo_dir / "test.txt").write_text("hello", encoding="utf-8")
    repo.index.add(["test.txt"])
    c1 = repo.index.commit("first").hexsha
    (repo_dir / "test.txt").write_text("hello\nworld", encoding="utf-8")
    repo.index.add(["test.txt"])
    c2 = repo.index.commit("second").hexsha
    repo.close()

    adapter = Repository(cache_dir=cache_dir)
    current, previous = adapter.prepare_workdirs(
        repo_url=str(repo_dir),
        commit=c2,
        force_reclone=False,
    )

    assert current is not None
    assert current.exists()
    assert previous is not None
    assert previous.exists()


def test_repository_adapter_get_diff(tmp_path):
    repo_dir = tmp_path / "repo"
    repo = Repo.init(repo_dir)
    (repo_dir / "a.txt").write_text("line1", encoding="utf-8")
    repo.index.add(["a.txt"])
    c1 = repo.index.commit("first").hexsha
    (repo_dir / "a.txt").write_text("line1\nline2", encoding="utf-8")
    repo.index.add(["a.txt"])
    c2 = repo.index.commit("second").hexsha
    repo.close()

    adapter = Repository(cache_dir=tmp_path / "cache")
    diff = adapter.get_diff(workdir=repo_dir, commit=c2)
    
    assert "diff --git" in diff
    assert "+line2" in diff

