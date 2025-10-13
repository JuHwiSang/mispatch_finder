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
    GHSAMeta,
    MCPServerContext,
)
from mispatch_finder.core.usecases.run_analysis import RunAnalysisUseCase
from mispatch_finder.core.usecases.list_ghsa import ListGHSAUseCase
from mispatch_finder.core.usecases.clear_cache import ClearCacheUseCase


class FakeVulnRepo:
    def __init__(self):
        self.fetched = []
        self.listed = []

    def fetch_metadata(self, ghsa: str) -> GHSAMeta:
        self.fetched.append(ghsa)
        return GHSAMeta(
            ghsa=ghsa,
            repo_url="https://github.com/test/repo",
            commit="abc123",
            parent_commit="parent123",
        )

    def list_ids(self, limit: int) -> list[str]:
        self.listed.append(limit)
        return ["GHSA-1111-2222-3333", "GHSA-4444-5555-6666"]

    def clear_cache(self) -> None:
        pass


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


def test_run_analysis_usecase_executes_full_flow():
    vuln_repo = FakeVulnRepo()
    repo = FakeRepo()
    mcp = FakeMCP()
    llm = FakeLLM()
    store = FakeStore()
    token_gen = FakeTokenGen()

    uc = RunAnalysisUseCase(
        vuln_repo=vuln_repo,
        repo=repo,
        mcp=mcp,
        llm=llm,
        store=store,
        token_gen=token_gen,
        prompt_diff_max_chars=100000,
    )

    result = uc.execute(ghsa="GHSA-TEST-1234-5678", force_reclone=False)

    assert vuln_repo.fetched == ["GHSA-TEST-1234-5678"]
    assert store.saved[0][0] == "GHSA-TEST-1234-5678"
    assert result["ghsa"] == "GHSA-TEST-1234-5678"
    # provider/model are logged by LLM adapter, not in result
    assert mcp.cleanup_called


def test_list_ghsa_usecase():
    vuln_repo = FakeVulnRepo()
    uc = ListGHSAUseCase(vuln_repo=vuln_repo, limit=500)
    
    result = uc.execute()
    
    assert result == ["GHSA-1111-2222-3333", "GHSA-4444-5555-6666"]
    assert vuln_repo.listed == [500]


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

