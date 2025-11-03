"""Tests for LogsUseCase."""
from mispatch_finder.core.usecases.logs import LogsUseCase

from tests.mispatch_finder.core.usecases.conftest import FakeAnalysisStore


def test_logs_with_ghsa_verbose():
    store = FakeAnalysisStore()
    uc = LogsUseCase(analysis_store=store)

    result = uc.execute(ghsa="GHSA-TEST", verbose=True)

    assert store.read_calls == [("GHSA-TEST", True)]
    assert len(result) == 2
    assert "GHSA-TEST" in result[0]


def test_logs_with_ghsa_non_verbose():
    store = FakeAnalysisStore()
    uc = LogsUseCase(analysis_store=store)

    result = uc.execute(ghsa="GHSA-TEST", verbose=False)

    assert store.read_calls == [("GHSA-TEST", False)]
    assert len(result) == 1
    assert "GHSA-TEST" in result[0]


def test_logs_without_ghsa_verbose():
    store = FakeAnalysisStore()
    uc = LogsUseCase(analysis_store=store)

    result = uc.execute(ghsa=None, verbose=True)

    assert store.summarize_calls == [True]
    assert len(result) == 2
    assert "MCP: 10 calls" in result[0]


def test_logs_without_ghsa_non_verbose():
    store = FakeAnalysisStore()
    uc = LogsUseCase(analysis_store=store)

    result = uc.execute(ghsa=None, verbose=False)

    assert store.summarize_calls == [False]
    assert len(result) == 2
    assert "GHSA-1111" in result[0]
