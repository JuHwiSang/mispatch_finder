import pytest
from pathlib import Path
from typing import Optional

from mispatch_finder.core.ports import (
    VulnerabilityRepositoryPort,
    RepositoryPort,
    MCPServerPort,
    LLMPort,
    ResultStorePort,
    TokenGeneratorPort,
    MCPServerContext,
)
from mispatch_finder.core.domain.models import Vulnerability, Repository
from mispatch_finder.core.usecases.analyze import AnalyzeUseCase
from mispatch_finder.core.usecases.list import ListUseCase
from mispatch_finder.core.usecases.clear_cache import ClearCacheUseCase


class FakeVulnRepo:
    def __init__(self):
        self.fetched = []
        self.listed = []
        self.cache_cleared_with = []

    def fetch_metadata(self, ghsa: str) -> Vulnerability:
        self.fetched.append(ghsa)
        return Vulnerability(
            ghsa_id=ghsa,
            repository=Repository(owner="test", name="repo"),
            commit_hash="abc123",
        )

    def list_ids(self, limit: int, ecosystem: str = "npm") -> list[str]:
        self.listed.append((limit, ecosystem))
        return ["GHSA-1111-2222-3333", "GHSA-4444-5555-6666"]

    def list_with_metadata(self, limit: int, ecosystem: str = "npm") -> list[Vulnerability]:
        return [
            Vulnerability(
                ghsa_id="GHSA-1111-2222-3333",
                repository=Repository(owner="test", name="repo1"),
                commit_hash="abc123",
            ),
            Vulnerability(
                ghsa_id="GHSA-4444-5555-6666",
                repository=Repository(owner="test", name="repo2"),
                commit_hash="def456",
            ),
        ]

    def clear_cache(self, prefix: Optional[str] = None) -> None:
        self.cache_cleared_with.append(prefix)


class FakeRepo:
    def prepare_workdirs(self, *, repo_url: str, commit: str, force_reclone: bool) -> tuple[Optional[Path], Optional[Path]]:
        return Path("/fake/current"), Path("/fake/previous")

    def get_diff(self, *, workdir: Path, commit: str) -> str:
        return "diff --git a/test.py b/test.py\n+added line"


class FakeMCP:
    def __init__(self):
        self.cleanup_called = False

    def start_servers(self, *, current_workdir, previous_workdir, auth_token) -> MCPServerContext:
        ctx = MCPServerContext(
            local_url="http://127.0.0.1:18080",
            public_url="https://test.lhr.life",
            has_current=True,
            has_previous=True,
        )
        ctx.cleanup = lambda: setattr(self, "cleanup_called", True)
        return ctx


class FakeLLM:
    def call(self, *, prompt: str, mcp_url: str, mcp_token: str) -> str:
        return '{"patch_risk":"good","current_risk":"good","reason":"test","poc":"test poc"}'


class FakeStore:
    def __init__(self):
        self.saved = []

    def save(self, ghsa: str, payload: dict) -> None:
        self.saved.append((ghsa, payload))
    
    def load(self, ghsa: str) -> Optional[dict]:
        for saved_ghsa, saved_payload in self.saved:
            if saved_ghsa == ghsa:
                return saved_payload
        return None
    
    def list_all(self) -> list[dict]:
        return [payload for _, payload in self.saved]


class FakeTokenGen:
    def generate(self) -> str:
        return "fake-token-12345"


class FakeLogger:
    """Fake logger for testing."""
    def debug(self, message: str, payload=None) -> None:
        pass

    def info(self, message: str, payload=None) -> None:
        pass

    def warning(self, message: str, payload=None) -> None:
        pass

    def error(self, message: str, payload=None, exc_info: bool = False) -> None:
        pass

    def exception(self, message: str, payload=None) -> None:
        pass


def test_run_analysis_usecase_executes_full_flow():
    """Test that AnalyzeUseCase delegates to orchestrator and stores result."""
    from mispatch_finder.core.services import AnalysisOrchestrator, DiffService, JsonExtractor

    vuln_repo = FakeVulnRepo()
    repo = FakeRepo()
    mcp = FakeMCP()
    llm = FakeLLM()
    store = FakeStore()
    token_gen = FakeTokenGen()
    logger = FakeLogger()

    # Create services
    diff_service = DiffService(repo=repo, max_chars=100000)
    json_extractor = JsonExtractor()

    # Create orchestrator
    orchestrator = AnalysisOrchestrator(
        vuln_repo=vuln_repo,
        repo=repo,
        mcp=mcp,
        llm=llm,
        token_gen=token_gen,
        logger=logger,
        diff_service=diff_service,
        json_extractor=json_extractor,
    )

    # Create use case (now much simpler)
    uc = AnalyzeUseCase(
        orchestrator=orchestrator,
        store=store,
    )

    result = uc.execute(ghsa="GHSA-TEST-1234-5678", force_reclone=False)

    assert vuln_repo.fetched == ["GHSA-TEST-1234-5678"]
    assert store.saved[0][0] == "GHSA-TEST-1234-5678"
    assert result["ghsa"] == "GHSA-TEST-1234-5678"
    # provider/model are logged by LLM adapter, not in result
    assert mcp.cleanup_called


def test_list_ghsa_usecase():
    vuln_repo = FakeVulnRepo()
    uc = ListUseCase(vuln_repo=vuln_repo, limit=500, ecosystem="npm")

    result = uc.execute()

    assert result == ["GHSA-1111-2222-3333", "GHSA-4444-5555-6666"]
    assert vuln_repo.listed == [(500, "npm")]


def test_list_ghsa_usecase_custom_ecosystem():
    vuln_repo = FakeVulnRepo()
    uc = ListUseCase(vuln_repo=vuln_repo, limit=100, ecosystem="pypi")

    result = uc.execute()

    assert result == ["GHSA-1111-2222-3333", "GHSA-4444-5555-6666"]
    assert vuln_repo.listed == [(100, "pypi")]


def test_clear_cache_usecase():
    from mispatch_finder.core.ports import CachePort

    class FakeCache:
        def __init__(self):
            self.cleared = False

        def clear_all(self) -> None:
            self.cleared = True

    cache = FakeCache()
    vuln_repo = FakeVulnRepo()

    uc = ClearCacheUseCase(cache=cache, vuln_repo=vuln_repo)
    uc.execute()

    assert cache.cleared
    assert vuln_repo.cache_cleared_with == [None]


def test_clear_cache_usecase_with_prefix():
    from mispatch_finder.core.ports import CachePort

    class FakeCache:
        def __init__(self):
            self.cleared = False

        def clear_all(self) -> None:
            self.cleared = True

    cache = FakeCache()
    vuln_repo = FakeVulnRepo()

    uc = ClearCacheUseCase(cache=cache, vuln_repo=vuln_repo)
    uc.execute(vuln_cache_prefix="osv")

    assert cache.cleared
    assert vuln_repo.cache_cleared_with == ["osv"]

