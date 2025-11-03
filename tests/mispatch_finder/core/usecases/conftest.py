"""Shared test fixtures and fakes for UseCase tests."""
from pathlib import Path
from typing import Union, overload, Iterator

from mispatch_finder.core.domain.models import Vulnerability, Repository
from mispatch_finder.core.ports import MCPServerContext


class FakeVulnRepo:
    def __init__(self):
        self.fetched = []
        self.listed = []
        self.listed_iter = []
        self.cache_cleared_with = []

    def fetch_metadata(self, ghsa: str) -> Vulnerability:
        self.fetched.append(ghsa)
        return Vulnerability(
            ghsa_id=ghsa,
            repository=Repository(owner="test", name="repo"),
            commit_hash="abc123",
        )

    @overload
    def list_vulnerabilities(
        self,
        limit: int,
        ecosystem: str = "npm",
        detailed: bool = False,
        filter_expr: str | None = None
    ) -> list[str]: ...

    @overload
    def list_vulnerabilities(
        self,
        limit: int,
        ecosystem: str = "npm",
        detailed: bool = True,
        filter_expr: str | None = None
    ) -> list[Vulnerability]: ...

    def list_vulnerabilities(
        self,
        limit: int,
        ecosystem: str = "npm",
        detailed: bool = False,
        filter_expr: str | None = None
    ) -> Union[list[str], list[Vulnerability]]:
        self.listed.append((limit, ecosystem, detailed, filter_expr))
        if not detailed:
            return ["GHSA-1111-2222-3333", "GHSA-4444-5555-6666"]
        else:
            return [
                Vulnerability(
                    ghsa_id="GHSA-1111-2222-3333",
                    repository=Repository(owner="test", name="repo1", ecosystem="npm", star_count=100, size_kb=500),
                    commit_hash="abc123",
                    cve_id="CVE-2023-1111",
                    summary="Test vulnerability 1",
                    severity="HIGH",
                ),
                Vulnerability(
                    ghsa_id="GHSA-4444-5555-6666",
                    repository=Repository(owner="test", name="repo2", ecosystem="npm", star_count=200, size_kb=1000),
                    commit_hash="def456",
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
        """Iterate over vulnerabilities lazily."""
        self.listed_iter.append((ecosystem, detailed, filter_expr))
        if not detailed:
            yield "GHSA-1111-2222-3333"
            yield "GHSA-4444-5555-6666"
        else:
            yield Vulnerability(
                ghsa_id="GHSA-1111-2222-3333",
                repository=Repository(owner="test", name="repo1", ecosystem="npm", star_count=100, size_kb=500),
                commit_hash="abc123",
                cve_id="CVE-2023-1111",
                summary="Test vulnerability 1",
                severity="HIGH",
            )
            yield Vulnerability(
                ghsa_id="GHSA-4444-5555-6666",
                repository=Repository(owner="test", name="repo2", ecosystem="npm", star_count=200, size_kb=1000),
                commit_hash="def456",
                cve_id="CVE-2023-4444",
                summary="Test vulnerability 2",
                severity="CRITICAL",
            )

    def clear_cache(self, prefix: str | None = None) -> None:
        self.cache_cleared_with.append(prefix)


class FakeRepo:
    def prepare_workdirs(self, *, repo_url: str, commit: str, force_reclone: bool) -> tuple[Path | None, Path | None]:
        return Path("/fake/current"), Path("/fake/previous")

    def get_diff(self, *, workdir: Path, commit: str) -> str:
        return "diff --git a/test.py b/test.py\n+added line"


class FakeMCP:
    def __init__(self):
        self.cleanup_called = False
        self.last_use_tunnel = None
        self.last_current_workdir = None
        self.last_previous_workdir = None
        self.last_auth_token = None
        self.start_servers_calls = []

    def start_servers(self, *, current_workdir, previous_workdir, auth_token, port: int, use_tunnel: bool = True) -> MCPServerContext:
        self.last_use_tunnel = use_tunnel
        self.last_current_workdir = current_workdir
        self.last_previous_workdir = previous_workdir
        self.last_auth_token = auth_token
        self.start_servers_calls.append({
            "current_workdir": current_workdir,
            "previous_workdir": previous_workdir,
            "auth_token": auth_token,
            "port": port,
            "use_tunnel": use_tunnel,
        })
        ctx = MCPServerContext(
            local_url="http://127.0.0.1:18080",
            public_url="https://test.lhr.life" if use_tunnel else None,
            has_current=current_workdir is not None,
            has_previous=previous_workdir is not None,
        )
        ctx.cleanup = lambda: setattr(self, "cleanup_called", True)
        return ctx


class FakeAnalysisStore:
    """Fake analysis store for reading logs."""

    def __init__(self, analyzed_ids: set[str] | None = None):
        self.analyzed_ids = analyzed_ids or set()
        self.read_calls = []
        self.summarize_calls = []

    def read_log(self, ghsa: str, verbose: bool) -> list[str]:
        self.read_calls.append((ghsa, verbose))
        if verbose:
            return [
                '{"message":"run_started","ghsa":"GHSA-TEST"}',
                '{"message":"final_result","payload":{"type":"final_result"}}',
            ]
        return [
            "GHSA-TEST | good/good | test reason",
        ]

    def summarize_all(self, verbose: bool) -> list[str]:
        self.summarize_calls.append(verbose)
        if verbose:
            return [
                "GHSA-1111 | good/good | reason1 | MCP: 10 calls",
                "GHSA-2222 | low/low | reason2 | MCP: 5 calls",
            ]
        return [
            "GHSA-1111 | good/good | reason1",
            "GHSA-2222 | low/low | reason2",
        ]

    def get_analyzed_ids(self) -> set[str]:
        return self.analyzed_ids


class FakeLLM:
    def call(self, *, prompt: str, mcp_url: str, mcp_token: str) -> str:
        return '{"patch_risk":"good","current_risk":"good","reason":"test","poc":"test poc"}'


class FakeTokenGen:
    def generate(self) -> str:
        return "fake-token-12345"


class FakeLogger:
    """Fake logger for testing."""
    def debug(self, message: str, **kwargs) -> None:
        pass

    def info(self, message: str, **kwargs) -> None:
        pass

    def warning(self, message: str, **kwargs) -> None:
        pass

    def error(self, message: str, exc_info: bool = False, **kwargs) -> None:
        pass

    def exception(self, message: str, **kwargs) -> None:
        pass
