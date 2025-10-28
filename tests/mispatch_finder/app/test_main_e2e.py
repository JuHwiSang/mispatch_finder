"""End-to-end tests for main facade functions."""
import json
import shutil
from pathlib import Path
from git import Repo
from dependency_injector import providers

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


def test_analyze_end_to_end(tmp_path, monkeypatch):
    """E2E test: analyze command with mocked dependencies."""
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

    # Create mocked container
    def create_mocked_container():
        container = Container()
        container.config.from_pydantic(test_config)

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

    # Execute (mimics CLI implementation)
    container = create_mocked_container()
    uc = container.analyze_uc()
    result = uc.execute(ghsa="GHSA-TEST-E2E", force_reclone=True)

    assert result["ghsa"] == "GHSA-TEST-E2E"
    assert result["raw_text"]

    data = json.loads(result["raw_text"]) if isinstance(result["raw_text"], str) else result["raw_text"]

    assert isinstance(data, dict)
    assert data["patch_risk"] == "good"
    assert data["current_risk"] == "good"
    assert data["reason"] == "Mock LLM response"


def test_list_vulnerabilities(tmp_path):
    """E2E test: list command returns vulnerability list."""
    from mispatch_finder.core.usecases.list import ListUseCase

    test_config = AppConfig(
        directories=DirectoryConfig(home=tmp_path),
        llm=LLMConfig(api_key="test-key", provider_name="openai", model_name="gpt-4"),
        github=GitHubConfig(token="test-token"),
        vulnerability=VulnerabilityConfig(ecosystem="npm"),
        analysis=AnalysisConfig(diff_max_chars=200_000),
    )

    # Create container with mocked vuln_data
    container = Container()
    container.config.from_pydantic(test_config)
    container.vuln_data.override(providers.Singleton(MockVulnerabilityRepository))

    # Execute (mimics CLI implementation)
    uc = ListUseCase(
        vuln_data=container.vuln_data(),
        limit=10,
        ecosystem=container.config.vulnerability.ecosystem(),
        detailed=False,
        filter_expr=None,
    )
    result = uc.execute()

    assert isinstance(result, list)
    assert len(result) == 2
    assert all(isinstance(ghsa, str) and ghsa.startswith("GHSA-") for ghsa in result)


def test_clear_cache(tmp_path):
    """E2E test: clear command clears caches."""
    test_config = AppConfig(
        directories=DirectoryConfig(home=tmp_path),
        llm=LLMConfig(api_key="test-key", provider_name="openai", model_name="gpt-4"),
        github=GitHubConfig(token="test-token"),
        vulnerability=VulnerabilityConfig(ecosystem="npm"),
        analysis=AnalysisConfig(diff_max_chars=200_000),
    )

    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(exist_ok=True)
    (cache_dir / "test.txt").write_text("test", encoding="utf-8")

    # Create container with mocked vuln_data
    container = Container()
    container.config.from_pydantic(test_config)
    container.vuln_data.override(providers.Singleton(MockVulnerabilityRepository))

    # Execute (mimics CLI implementation)
    uc = container.clear_cache_uc()
    uc.execute()  # Should not raise


def test_logs_with_ghsa(tmp_path):
    """E2E test: logs command returns log details for specific GHSA."""
    test_config = AppConfig(
        directories=DirectoryConfig(home=tmp_path),
        llm=LLMConfig(api_key="test-key", provider_name="openai", model_name="gpt-4"),
        github=GitHubConfig(token="test-token"),
        vulnerability=VulnerabilityConfig(ecosystem="npm"),
        analysis=AnalysisConfig(diff_max_chars=200_000),
    )

    logs_dir = tmp_path / "logs"
    logs_dir.mkdir(exist_ok=True)

    log_file = logs_dir / "GHSA-TEST.jsonl"
    log_file.write_text(
        '{"message":"run_started","ghsa":"GHSA-TEST"}\n'
        '{"message":"final_result","payload":{"type":"final_result","result":{"ghsa":"GHSA-TEST"}}}\n',
        encoding="utf-8"
    )

    # Create container
    container = Container()
    container.config.from_pydantic(test_config)

    # Execute (mimics CLI implementation)
    uc = container.logs_uc()
    result = uc.execute("GHSA-TEST", verbose=False)

    assert isinstance(result, list)
    assert len(result) > 0


def test_logs_without_ghsa(tmp_path):
    """E2E test: logs command returns summary when no GHSA provided."""
    test_config = AppConfig(
        directories=DirectoryConfig(home=tmp_path),
        llm=LLMConfig(api_key="test-key", provider_name="openai", model_name="gpt-4"),
        github=GitHubConfig(token="test-token"),
        vulnerability=VulnerabilityConfig(ecosystem="npm"),
        analysis=AnalysisConfig(diff_max_chars=200_000),
    )

    logs_dir = tmp_path / "logs"
    logs_dir.mkdir(exist_ok=True)

    # Create container
    container = Container()
    container.config.from_pydantic(test_config)

    # Execute (mimics CLI implementation)
    uc = container.logs_uc()
    result = uc.execute(None, verbose=False)

    assert isinstance(result, list)
