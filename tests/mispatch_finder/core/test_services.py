"""Tests for core domain services."""
import pytest
from pathlib import Path
from typing import Optional

from mispatch_finder.core.services import DiffService, JsonExtractor, AnalysisOrchestrator
from mispatch_finder.core.ports import (
    VulnerabilityDataPort,
    RepositoryPort,
    MCPServerPort,
    LLMPort,
    TokenGeneratorPort,
    MCPServerContext,
)
from mispatch_finder.core.domain.models import Vulnerability, Repository
from mispatch_finder.core.ports import LoggerPort


class FakeRepo:
    """Fake repository for testing diff service."""
    def __init__(self, diff_content: str = "test diff"):
        self._diff_content = diff_content

    def prepare_workdirs(self, *, repo_url: str, commit: str, force_reclone: bool) -> tuple[Optional[Path], Optional[Path]]:
        return Path("/fake/current"), Path("/fake/previous")

    def get_diff(self, *, workdir: Path, commit: str) -> str:
        return self._diff_content


class TestDiffService:
    """Tests for DiffService."""

    def test_generate_diff_no_truncation(self):
        """Test diff generation without truncation."""
        repo = FakeRepo(diff_content="short diff")
        service = DiffService(repo=repo, max_chars=1000)

        result = service.generate_diff(workdir=Path("/test"), commit="abc123")

        assert result.full_text == "short diff"
        assert result.truncated_text == "short diff"
        assert result.full_len == 10
        assert result.included_len == 10
        assert result.was_truncated is False

    def test_generate_diff_with_truncation(self):
        """Test diff generation with middle truncation."""
        long_diff = "a" * 1000
        repo = FakeRepo(diff_content=long_diff)
        service = DiffService(repo=repo, max_chars=100)

        result = service.generate_diff(workdir=Path("/test"), commit="abc123")

        assert result.full_len == 1000
        assert result.was_truncated is True
        assert result.included_len < result.full_len
        assert "..." in result.truncated_text

    def test_generate_diff_with_none_workdir(self):
        """Test diff generation with None workdir."""
        repo = FakeRepo()
        service = DiffService(repo=repo, max_chars=1000)

        result = service.generate_diff(workdir=None, commit="abc123")

        assert result.full_text == ""
        assert result.truncated_text == ""
        assert result.full_len == 0
        assert result.was_truncated is False


class TestJsonExtractor:
    """Tests for JsonExtractor."""

    def test_extract_json_from_text(self):
        """Test extracting JSON from text."""
        extractor = JsonExtractor()
        text = 'Here is the result: {"status": "ok", "value": 123}'

        result = extractor.extract(text)

        assert result == '{"status": "ok", "value": 123}'

    def test_extract_json_from_markdown(self):
        """Test extracting JSON from markdown code block."""
        extractor = JsonExtractor()
        text = """```json
{"status": "ok", "value": 123}
```"""

        result = extractor.extract(text)

        # Should find and format the JSON
        assert "status" in result
        assert "ok" in result

    def test_extract_no_json(self):
        """Test extraction when no JSON is present."""
        extractor = JsonExtractor()
        text = "This is just plain text without JSON"

        result = extractor.extract(text)

        # Should return original text
        assert result == text

    def test_extract_invalid_json(self):
        """Test extraction with malformed JSON."""
        extractor = JsonExtractor()
        text = 'Result: {invalid json here}'

        result = extractor.extract(text)

        # Should return original text when parsing fails
        assert result == text


class FakeVulnRepo:
    """Fake vulnerability repository."""
    def fetch_metadata(self, ghsa: str) -> Vulnerability:
        return Vulnerability(
            ghsa_id=ghsa,
            repository=Repository(owner="test", name="repo"),
            commit_hash="abc123",
            severity="HIGH",
        )


class FakeMCP:
    """Fake MCP server."""
    def __init__(self):
        self.cleanup_called = False
        self.last_use_tunnel = None

    def start_servers(self, *, current_workdir, previous_workdir, auth_token, use_tunnel: bool = True) -> MCPServerContext:
        self.last_use_tunnel = use_tunnel
        ctx = MCPServerContext(
            local_url="http://127.0.0.1:18080",
            public_url="https://test.example.com" if use_tunnel else None,
            has_current=current_workdir is not None,
            has_previous=previous_workdir is not None,
        )
        ctx.cleanup = lambda: setattr(self, "cleanup_called", True)
        return ctx


class FakeLLM:
    """Fake LLM."""
    def call(self, *, prompt: str, mcp_url: str, mcp_token: str) -> str:
        return '{"current_risk": "good", "patch_risk": "good", "reason": "test"}'


class FakeTokenGen:
    """Fake token generator."""
    def generate(self) -> str:
        return "fake-token-xyz"


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


class TestAnalysisOrchestrator:
    """Tests for AnalysisOrchestrator."""

    def test_orchestrator_full_flow(self):
        """Test full orchestration flow."""
        vuln_data = FakeVulnRepo()
        repo = FakeRepo()
        mcp = FakeMCP()
        llm = FakeLLM()
        token_gen = FakeTokenGen()
        logger = FakeLogger()
        diff_service = DiffService(repo=repo, max_chars=1000)
        json_extractor = JsonExtractor()

        orchestrator = AnalysisOrchestrator(
            vuln_data=vuln_data,
            repo=repo,
            mcp=mcp,
            llm=llm,
            token_gen=token_gen,
            logger=logger,
            diff_service=diff_service,
            json_extractor=json_extractor,
        )

        result = orchestrator.analyze(ghsa="GHSA-TEST-1234", force_reclone=False)

        # Check AnalysisResult fields
        assert result.ghsa == "GHSA-TEST-1234"
        assert result.verdict == "good"  # current_risk
        assert result.severity == "good"  # patch_risk
        assert result.rationale == "test"  # reason
        assert result.raw_text is not None
        assert mcp.cleanup_called

    def test_orchestrator_cleanup_on_error(self):
        """Test that cleanup is called even on error."""
        class ErrorLLM:
            def call(self, *, prompt: str, mcp_url: str, mcp_token: str) -> str:
                raise RuntimeError("LLM error")

        vuln_data = FakeVulnRepo()
        repo = FakeRepo()
        mcp = FakeMCP()
        llm = ErrorLLM()
        token_gen = FakeTokenGen()
        logger = FakeLogger()
        diff_service = DiffService(repo=repo, max_chars=1000)
        json_extractor = JsonExtractor()

        orchestrator = AnalysisOrchestrator(
            vuln_data=vuln_data,
            repo=repo,
            mcp=mcp,
            llm=llm,
            token_gen=token_gen,
            logger=logger,
            diff_service=diff_service,
            json_extractor=json_extractor,
        )

        with pytest.raises(RuntimeError, match="LLM error"):
            orchestrator.analyze(ghsa="GHSA-TEST-1234", force_reclone=False)

        # Cleanup should still be called
        assert mcp.cleanup_called
