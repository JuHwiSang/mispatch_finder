"""Shared fixtures for app-level tests."""
import json
import pytest
from pathlib import Path
from git import Repo
from dependency_injector import providers

from mispatch_finder.app.container import Container
from mispatch_finder.app import main
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

    def list_ids(self, limit: int, ecosystem: str = "npm") -> list[str]:
        return ["GHSA-1111-2222-3333", "GHSA-4444-5555-6666"]

    def clear_cache(self, prefix: str | None = None) -> None:
        pass


class MockLLM:
    """Mock implementation of LLMPort that returns canned responses."""
    
    def __init__(self, **kwargs):
        pass

    def call(self, *, prompt: str, mcp_url: str, mcp_token: str) -> str:
        return json.dumps({
            "patch_risk": "good",
            "current_risk": "good",
            "reason": "Mock LLM response",
            "poc": "echo 'test'"
        })


class MockMCPServer:
    """Mock implementation of MCPServerPort."""
    
    def __init__(self, **kwargs):
        pass

    def start_servers(self, *, current_workdir, previous_workdir, auth_token: str) -> MCPServerContext:
        return MCPServerContext(
            local_url="http://127.0.0.1:18080",
            public_url="http://mock.test",
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
        # (in a real test, you'd create separate checkouts)
        return self._repo_dir, self._repo_dir
    
    def get_diff(self, *, workdir: Path, commit: str) -> str:
        """Return a mock diff."""
        return "--- a/test.py\n+++ b/test.py\n@@ -1 +1 @@\n-print('v1')\n+print('v2')"


def _create_mocked_container(
    tmp_path: Path,
    repo_dir: Path,
    c1: str,
    c2: str,
    **config_overrides
) -> Container:
    """Helper to create a mocked container."""
    container = Container()
    config = main._get_default_config()
    config.update({
        "cache_dir": tmp_path / "cache",
        "results_dir": tmp_path / "results",
        "logs_dir": tmp_path / "logs",
    })
    config.update(config_overrides)
    
    # Apply parameter mapping for CLI-style params
    param_to_config = {
        "provider": "llm_provider_name",
        "model": "llm_model_name",
        "api_key": "llm_api_key",
    }
    for old_key in list(config.keys()):
        if old_key in param_to_config:
            new_key = param_to_config[old_key]
            config[new_key] = config.pop(old_key)
    
    container.config.from_dict(config)
    
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
def mock_container_for_analyze(tmp_path, monkeypatch):
    """Fixture to override container with mocks for analyze tests.
    
    This fixture:
    - Creates a test git repository with two commits
    - Mocks the Tunnel to avoid real SSH connections
    - Patches Container() to return mocked instance
    
    Returns:
        tuple: (repo_dir, commit1_sha, commit2_sha)
    """
    repo_dir, c1, c2 = create_test_repo(tmp_path)
    
    # Mock Tunnel to avoid real network calls
    def fake_start_tunnel(host, port):
        return f"http://{host}:{port}", DummyTunnel()
    
    monkeypatch.setattr(Tunnel, "start_tunnel", fake_start_tunnel)
    
    # Patch Container to return mocked instance
    original_container = Container
    
    def mocked_container_class():
        return _create_mocked_container(tmp_path, repo_dir, c1, c2)
    
    monkeypatch.setattr("mispatch_finder.app.main.Container", mocked_container_class)
    
    return repo_dir, c1, c2


@pytest.fixture
def mock_container_for_list(tmp_path, monkeypatch):
    """Fixture for list_ids tests."""
    repo_dir, c1, c2 = create_test_repo(tmp_path)
    
    def mocked_container_class():
        container = Container()
        config = main._get_default_config()
        container.config.from_dict(config)
        container.vuln_data.override(providers.Singleton(MockVulnerabilityRepository))
        return container
    
    monkeypatch.setattr("mispatch_finder.app.main.Container", mocked_container_class)


@pytest.fixture
def mock_container_for_clear(tmp_path, monkeypatch):
    """Fixture for clear tests."""
    def mocked_container_class():
        container = Container()
        config = main._get_default_config()
        config.update({"cache_dir": tmp_path / "cache"})
        container.config.from_dict(config)
        container.vuln_data.override(providers.Singleton(MockVulnerabilityRepository))
        return container
    
    monkeypatch.setattr("mispatch_finder.app.main.Container", mocked_container_class)


@pytest.fixture
def mock_container_for_logs(tmp_path, monkeypatch):
    """Fixture for logs tests."""
    def mocked_container_class():
        container = Container()
        config = main._get_default_config()
        config.update({"logs_dir": tmp_path / "logs"})
        container.config.from_dict(config)
        return container

    monkeypatch.setattr("mispatch_finder.app.main.Container", mocked_container_class)

