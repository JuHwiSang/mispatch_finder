"""Shared fixtures for app-level tests."""
import json
import pytest
from pathlib import Path
from typing import Iterator
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
from mispatch_finder.core.domain.models import Vulnerability, Repository
from mispatch_finder.infra.mcp.tunnel import Tunnel


def create_test_repo(tmp_path: Path) -> tuple[Path, str, str]:
    """Helper to create a git repo with two commits."""
    repo_dir = tmp_path / "repo"
    repo = Repo.init(repo_dir)

    (repo_dir / "test.py").write_text("print('v1')", encoding="utf-8")
    repo.index.add(["test.py"])
    c1 = repo.index.commit("first commit").hexsha

    (repo_dir / "test.py").write_text("print('v2')", encoding="utf-8")
    repo.index.add(["test.py"])
    c2 = repo.index.commit("second commit").hexsha

    repo.close()
    return repo_dir, c1, c2


class MockVulnerabilityRepository:
    """Mock implementation of VulnerabilityDataPort."""

    def __init__(self, repo_url: str = "", commit: str = "", **kwargs):
        # Parse repo_url to extract owner/name
        if repo_url and "/" in repo_url:
            parts = repo_url.rstrip("/").split("/")
            self._owner = parts[-2] if len(parts) >= 2 else "test"
            self._name = parts[-1] if len(parts) >= 1 else "repo"
        else:
            self._owner = "test"
            self._name = "repo"
        self._commit = commit

    def fetch_metadata(self, ghsa: str) -> Vulnerability:
        return Vulnerability(
            ghsa_id=ghsa,
            repository=Repository(owner=self._owner, name=self._name),
            commit_hash=self._commit,
        )

    def list_vulnerabilities(
        self, limit: int, ecosystem: str = "npm", detailed: bool = False, filter_expr: str | None = None
    ):
        """Mock list_vulnerabilities implementation."""
        if not detailed:
            return ["GHSA-1111-2222-3333", "GHSA-4444-5555-6666"]
        else:
            return [
                Vulnerability(
                    ghsa_id="GHSA-1111-2222-3333",
                    repository=Repository(
                        owner=self._owner, name=self._name, ecosystem="npm", star_count=100, size_kb=500
                    ),
                    commit_hash=self._commit,
                    cve_id="CVE-2023-1111",
                    summary="Test vulnerability 1",
                    severity="HIGH",
                ),
                Vulnerability(
                    ghsa_id="GHSA-4444-5555-6666",
                    repository=Repository(
                        owner=self._owner, name=self._name, ecosystem="npm", star_count=200, size_kb=1000
                    ),
                    commit_hash=self._commit,
                    cve_id="CVE-2023-4444",
                    summary="Test vulnerability 2",
                    severity="CRITICAL",
                ),
            ]

    def list_vulnerabilities_iter(
        self,
        ecosystem: str = "npm",
        detailed: bool = False,
        filter_expr: str | None = None,
    ) -> Iterator[str] | Iterator[Vulnerability]:
        """Mock list_vulnerabilities_iter implementation."""
        if not detailed:
            yield "GHSA-1111-2222-3333"
            yield "GHSA-4444-5555-6666"
        else:
            yield Vulnerability(
                ghsa_id="GHSA-1111-2222-3333",
                repository=Repository(
                    owner=self._owner, name=self._name, ecosystem="npm", star_count=100, size_kb=500
                ),
                commit_hash=self._commit,
                cve_id="CVE-2023-1111",
                summary="Test vulnerability 1",
                severity="HIGH",
            )
            yield Vulnerability(
                ghsa_id="GHSA-4444-5555-6666",
                repository=Repository(
                    owner=self._owner, name=self._name, ecosystem="npm", star_count=200, size_kb=1000
                ),
                commit_hash=self._commit,
                cve_id="CVE-2023-4444",
                summary="Test vulnerability 2",
                severity="CRITICAL",
            )

    def clear_cache(self, prefix: str | None = None) -> None:
        pass


class MockLLM:
    """Mock implementation of LLMPort that returns canned responses."""

    def __init__(self, **kwargs):
        pass

    def call(self, *, prompt: str, mcp_url: str, mcp_token: str) -> str:
        return json.dumps(
            {"patch_risk": "good", "current_risk": "good", "reason": "Mock LLM response", "poc": "echo 'test'"}
        )


class MockMCPServer:
    """Mock implementation of MCPServerPort."""

    def __init__(self, **kwargs):
        pass

    def start_servers(self, *, current_workdir, previous_workdir, auth_token: str, port: int, use_tunnel: bool = True) -> MCPServerContext:
        return MCPServerContext(
            local_url=f"http://127.0.0.1:{port}",
            public_url="http://mock.test" if use_tunnel else None,
            has_current=current_workdir is not None,
            has_previous=previous_workdir is not None,
        )


class DummyTunnel:
    """Dummy tunnel for testing."""

    def stop_tunnel(self):
        pass


class MockRepository:
    """Mock implementation of RepositoryPort."""

    def __init__(self, repo_dir: Path, commit: str, **kwargs):
        self._repo_dir = repo_dir
        self._commit = commit

    def prepare_workdirs(self, *, repo_url: str, commit: str, force_reclone: bool):
        """Return the actual test repo directories."""
        # Return the test repo as both current and previous
        return self._repo_dir, self._repo_dir

    def get_diff(self, *, workdir: Path, commit: str) -> str:
        """Return a mock diff."""
        return "--- a/test.py\n+++ b/test.py\n@@ -1 +1 @@\n-print('v1')\n+print('v2')"


@pytest.fixture
def test_config(tmp_path):
    """Create test configuration with explicit values."""
    return AppConfig(
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


def _create_mocked_container(
    tmp_path: Path, repo_dir: Path, c1: str, c2: str, config: AppConfig
) -> Container:
    """Helper to create a mocked container with test config."""
    container = Container()
    container.config.from_pydantic(config)

    # Override providers with mocks
    container.vuln_data.override(
        providers.Singleton(
            MockVulnerabilityRepository,
            repo_url=str(repo_dir),
            commit=c2,
            parent_commit=c1,
        )
    )
    container.repo.override(
        providers.Factory(
            MockRepository,
            repo_dir=repo_dir,
            commit=c2,
        )
    )
    container.llm.override(providers.Factory(MockLLM))
    container.mcp_server.override(providers.Factory(MockMCPServer))

    return container


@pytest.fixture
def mock_container_for_analyze(tmp_path, test_config, monkeypatch):
    """Fixture to override container with mocks for analyze tests."""
    repo_dir, c1, c2 = create_test_repo(tmp_path)

    # Mock Tunnel to avoid real network calls
    def fake_start_tunnel(host, port):
        return f"http://{host}:{port}", DummyTunnel()

    monkeypatch.setattr(Tunnel, "start_tunnel", fake_start_tunnel)

    # Patch Container class to return mocked instance
    monkeypatch.setattr("mispatch_finder.app.cli.Container", lambda: _create_mocked_container(tmp_path, repo_dir, c1, c2, test_config))

    return repo_dir, c1, c2


@pytest.fixture
def mock_container_for_list(tmp_path, test_config, monkeypatch):
    """Fixture for list tests."""
    repo_dir, c1, c2 = create_test_repo(tmp_path)

    def create_mock_container():
        c = Container()
        c.config.from_pydantic(test_config)
        c.vuln_data.override(providers.Singleton(MockVulnerabilityRepository))
        return c

    monkeypatch.setattr("mispatch_finder.app.cli.Container", create_mock_container)


@pytest.fixture
def mock_container_for_clear(tmp_path, test_config, monkeypatch):
    """Fixture for clear tests."""
    def create_mock_container():
        c = Container()
        c.config.from_pydantic(test_config)
        c.vuln_data.override(providers.Singleton(MockVulnerabilityRepository))
        return c

    monkeypatch.setattr("mispatch_finder.app.cli.Container", create_mock_container)


@pytest.fixture
def mock_container_for_logs(tmp_path, test_config, monkeypatch):
    """Fixture for logs tests."""
    def create_mock_container():
        c = Container()
        c.config.from_pydantic(test_config)
        return c

    monkeypatch.setattr("mispatch_finder.app.cli.Container", create_mock_container)
