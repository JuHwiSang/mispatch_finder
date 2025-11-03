"""Tests for AnalyzeUseCase."""
from mispatch_finder.core.usecases.analyze import AnalyzeUseCase
from mispatch_finder.core.services import AnalysisOrchestrator, DiffService, JsonExtractor

from tests.mispatch_finder.core.usecases.conftest import FakeVulnRepo, FakeRepo, FakeMCP, FakeLLM, FakeTokenGen, FakeLogger


def test_run_analysis_usecase_executes_full_flow():
    """Test that AnalyzeUseCase delegates to orchestrator."""
    vuln_data = FakeVulnRepo()
    repo = FakeRepo()
    mcp = FakeMCP()
    llm = FakeLLM()
    token_gen = FakeTokenGen()
    logger = FakeLogger()

    # Create services
    diff_service = DiffService(repo=repo, max_chars=100000)
    json_extractor = JsonExtractor()

    # Create orchestrator
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

    # Create use case (now much simpler)
    uc = AnalyzeUseCase(
        orchestrator=orchestrator,
    )

    result = uc.execute(ghsa="GHSA-TEST-1234-5678", force_reclone=False)

    assert vuln_data.fetched == ["GHSA-TEST-1234-5678"]
    assert result.ghsa == "GHSA-TEST-1234-5678"
    assert result.verdict == "good"
    assert result.rationale == "test"
    # provider/model are logged by LLM adapter, not in result
    assert mcp.cleanup_called
