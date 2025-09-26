import json
from pathlib import Path
from git import Repo
import shutil

from mispatch_finder.app.main import run_analysis
from mispatch_finder.core import analyze as analyze_mod
from mispatch_finder.infra.mcp import tunnel as tun_mod


def _init_repo_with_two_commits(tmp_path: Path) -> tuple[Path, str, str]:
    shutil.rmtree(tmp_path)
    repo_dir = tmp_path / "repo"
    repo = Repo.init(repo_dir)
    (repo_dir / "a.txt").write_text("one", encoding="utf-8")
    repo.index.add(["a.txt"])
    c1 = repo.index.commit(
        "first",
        author_date="2024-02-01T12:34:56+0900",
        commit_date="2024-02-01T12:34:56+0900",
    ).hexsha
    (repo_dir / "a.txt").write_text("one\ntwo", encoding="utf-8")
    repo.index.add(["a.txt"])
    c2 = repo.index.commit(
        "second",
        author_date="2024-02-01T13:34:56+0900",
        commit_date="2024-02-01T13:34:56+0900",
    ).hexsha
    repo.close()
    return repo_dir, c1, c2


def test_run_analysis_end_to_end_local_repo(tmp_path, monkeypatch):
    # Create local repo and mock cve metadata to point to it

    base, c1, c2 = _init_repo_with_two_commits(tmp_path)

    class DummyGHSA:
        def __init__(self, ghsa: str, repo_url: str, commit: str):
            self.ghsa = ghsa
            self.repo_url = repo_url
            self.commit = commit
            self.parent_commit = c1

    monkeypatch.setattr(
        analyze_mod,
        "fetch_ghsa_metadata",
        lambda ghsa, github_token=None: DummyGHSA(ghsa, base.as_posix(), c2),
    )

    class DummyTunnel:
        def stop_tunnel(self):
            return None

    def fake_start_tunnel(host, port):
        local_url = f"http://{host}:{port}"
        return local_url, DummyTunnel()

    monkeypatch.setattr(tun_mod.Tunnel, "start_tunnel", fake_start_tunnel)

    print("test_run_analysis_end_to_end_local_repo")
    out = run_analysis(
        ghsa="GHSA-TEST-LOCAL",
        provider="openai",
        model="gpt-test",
        api_key="sk-xxx",
        github_token="ghp-xxx",
        force_reclone=True,  # 매번마다 init한 repo 결과가 다르므로, 매번 새로 fetch해오도록 해야 함
    )

    # Should contain our dummy adapter's JSON
    assert out["raw_text"]
    if isinstance(out["raw_text"], str):
        data = json.loads(out["raw_text"])
    else:
        data = out["raw_text"]
    assert isinstance(data, dict)
    assert data.get("patch_risk") in {"good", "low", "medium", "high"}
    assert data.get("current_risk") in {"good", "low", "medium", "high"}
    assert isinstance(data.get("reason"), str)
    assert isinstance(data.get("poc"), str)
