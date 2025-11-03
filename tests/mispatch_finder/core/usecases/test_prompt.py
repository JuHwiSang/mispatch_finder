"""Tests for PromptUseCase."""
from mispatch_finder.core.usecases.prompt import PromptUseCase

from tests.mispatch_finder.core.usecases.conftest import FakeVulnRepo, FakeRepo, FakeDiffService


def test_prompt_usecase_generates_prompt():
    """Test that PromptUseCase generates the prompt correctly."""
    vuln_data = FakeVulnRepo()
    repo = FakeRepo()
    diff_service = FakeDiffService()

    uc = PromptUseCase(
        vuln_data=vuln_data,
        repo=repo,
        diff_service=diff_service,
    )

    result = uc.execute(ghsa="GHSA-TEST-1234-5678", force_reclone=False)

    # Verify dependencies were called
    assert vuln_data.fetched == ["GHSA-TEST-1234-5678"]

    # Verify result is a string (the prompt)
    assert isinstance(result, str)
    assert "GHSA-TEST-1234-5678" in result
    assert "You are a security reviewer" in result
    assert "test/repo" in result  # Repository name from FakeVulnRepo
    assert "abc123" in result  # Commit hash from FakeVulnRepo
    assert "diff --git a/test.py b/test.py" in result  # Diff from FakeDiffService


def test_prompt_usecase_includes_diff():
    """Test that the prompt includes the diff text."""
    vuln_data = FakeVulnRepo()
    repo = FakeRepo()
    diff_service = FakeDiffService()

    uc = PromptUseCase(
        vuln_data=vuln_data,
        repo=repo,
        diff_service=diff_service,
    )

    result = uc.execute(ghsa="GHSA-9999-8888-7777")

    # Verify diff is included
    assert "--- DIFF (unified) ---" in result
    assert "+added line" in result
