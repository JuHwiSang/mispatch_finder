from pathlib import Path

from mispatch_finder.core.domain.models import RepoContext, AnalysisResult


def test_repo_context_creation():
    ctx = RepoContext(
        repo_url="https://github.com/test/repo",
        workdir_current=Path("/tmp/current"),
        workdir_previous=Path("/tmp/previous"),
        commit="abc123",
        parent_commit="parent123",
    )

    assert ctx.repo_url == "https://github.com/test/repo"
    assert ctx.commit == "abc123"
    assert ctx.parent_commit == "parent123"
    assert ctx.workdir_current == Path("/tmp/current")
    assert ctx.workdir_previous == Path("/tmp/previous")


def test_repo_context_no_workdirs():
    ctx = RepoContext(
        repo_url="https://github.com/test/repo",
        workdir_current=None,
        workdir_previous=None,
        commit="abc123",
        parent_commit=None,
    )

    assert ctx.workdir_current is None
    assert ctx.workdir_previous is None


def test_analysis_result_creation():
    result = AnalysisResult(
        ghsa="GHSA-TEST-1234-5678",
        provider="openai",
        model="gpt-4",
        verdict="good",
        severity="low",
        rationale="Test rationale",
        evidence=[{"type": "test", "data": "value"}],
        poc_idea="echo 'test'",
        raw_text='{"test": "data"}',
    )

    assert result.ghsa == "GHSA-TEST-1234-5678"
    assert result.verdict == "good"
    assert result.severity == "low"
    assert result.rationale == "Test rationale"
    assert result.evidence is not None and len(result.evidence) == 1
    assert result.poc_idea == "echo 'test'"
    assert result.raw_text == '{"test": "data"}'


def test_analysis_result_with_none_fields():
    result = AnalysisResult(
        ghsa="GHSA-TEST-1234-5678",
        provider="openai",
        model="gpt-4",
        verdict=None,
        severity=None,
        rationale=None,
        evidence=None,
        poc_idea=None,
        raw_text=None,
    )

    assert result.verdict is None
    assert result.severity is None
    assert result.rationale is None
    assert result.evidence is None
    assert result.poc_idea is None
    assert result.raw_text is None

