"""End-to-end tests for main facade functions."""
import json
import shutil
from pathlib import Path
from git import Repo
from dependency_injector import providers

from mispatch_finder.app import main
from mispatch_finder.app.config import (
    AppConfig,
    DirectoryConfig,
    LLMConfig,
    GitHubConfig,
    VulnerabilityConfig,
    AnalysisConfig,
)
from mispatch_finder.app.container import Container
from mispatch_finder.core.ports import MCPServerContext
from mispatch_finder.infra.mcp.tunnel import Tunnel
from tests.mispatch_finder.app.conftest import MockVulnerabilityRepository, MockLLM, MockMCPServer, DummyTunnel, MockRepository


def _init_repo_with_two_commits(tmp_path: Path) -> tuple[Path, str, str]:
    """Create a git repo with two commits for E2E testing."""
    if tmp_path.exists():
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


def test_run_analysis_end_to_end_with_local_repo(tmp_path, monkeypatch):
    """E2E test: run_analysis with DI container overrides."""
    base, c1, c2 = _init_repo_with_two_commits(tmp_path)

    # Mock Tunnel to avoid real network calls
    def fake_start_tunnel(host, port):
        return f"http://{host}:{port}", DummyTunnel()

    monkeypatch.setattr(Tunnel, "start_tunnel", fake_start_tunnel)

    # Create test config
    test_config = AppConfig(
        directories=DirectoryConfig(home=tmp_path),
        llm=LLMConfig(
            api_key="test-key",
            provider_name="openai",
            model_name="gpt-4",
        ),
        github=GitHubConfig(token="test-token"),
        vulnerability=VulnerabilityConfig(ecosystem="npm"),
        analysis=AnalysisConfig(diff_max_chars=200_000),
    )

    # Patch _create_container to return mocked instance
    def mocked_create_container(config=None):
        container = Container()
        cfg = config or test_config
        container.config.from_pydantic(cfg)

        # Override with mocks
        container.vuln_data.override(
            providers.Singleton(
                MockVulnerabilityRepository,
                repo_url=base.as_posix(),
                commit=c2,
            )
        )
        container.repo.override(
            providers.Factory(
                MockRepository,
                repo_dir=base,
                commit=c2,
            )
        )
        container.llm.override(providers.Factory(MockLLM))
        container.mcp_server.override(providers.Factory(MockMCPServer))

        return container

    monkeypatch.setattr("mispatch_finder.app.main._create_container", mocked_create_container)

    result = main.analyze(
        ghsa="GHSA-TEST-E2E",
        force_reclone=True,
    )

    assert result["ghsa"] == "GHSA-TEST-E2E"
    assert result["raw_text"]

    data = json.loads(result["raw_text"]) if isinstance(result["raw_text"], str) else result["raw_text"]

    assert isinstance(data, dict)
    assert data["patch_risk"] == "good"
    assert data["current_risk"] == "good"
    assert data["reason"] == "Mock LLM response"
