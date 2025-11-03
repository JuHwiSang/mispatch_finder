"""Tests for ListUseCase."""
from typing import cast

from mispatch_finder.core.usecases.list import ListUseCase
from mispatch_finder.core.domain.models import Vulnerability

from tests.mispatch_finder.core.usecases.conftest import FakeVulnRepo, FakeAnalysisStore


def test_list_usecase_ids_only():
    """Test listing vulnerabilities with detailed=False (IDs only)."""
    vuln_data = FakeVulnRepo()
    analysis_store = FakeAnalysisStore()

    uc = ListUseCase(vuln_data=vuln_data, analysis_store=analysis_store)

    result = uc.execute(limit=500, ecosystem="npm", detailed=False, include_analyzed=True)

    assert result == ["GHSA-1111-2222-3333", "GHSA-4444-5555-6666"]
    # Now uses iterator (listed_iter instead of listed)
    assert len(vuln_data.listed_iter) == 1
    assert vuln_data.listed_iter[0][0] == "npm"  # ecosystem
    assert vuln_data.listed_iter[0][1] == False  # detailed


def test_list_usecase_custom_ecosystem():
    """Test listing with custom ecosystem."""
    vuln_data = FakeVulnRepo()
    analysis_store = FakeAnalysisStore()

    uc = ListUseCase(vuln_data=vuln_data, analysis_store=analysis_store)

    result = uc.execute(limit=100, ecosystem="pypi", detailed=False, include_analyzed=True)

    assert result == ["GHSA-1111-2222-3333", "GHSA-4444-5555-6666"]
    assert len(vuln_data.listed_iter) == 1
    assert vuln_data.listed_iter[0][0] == "pypi"  # ecosystem


def test_list_usecase_detailed():
    """Test listing vulnerabilities with detailed=True (full metadata)."""
    vuln_data = FakeVulnRepo()
    analysis_store = FakeAnalysisStore()

    uc = ListUseCase(vuln_data=vuln_data, analysis_store=analysis_store)

    result = cast(list[Vulnerability], uc.execute(limit=10, ecosystem="npm", detailed=True, include_analyzed=True))

    assert isinstance(result, list)
    assert len(result) == 2
    assert all(isinstance(v, Vulnerability) for v in result)
    assert result[0].ghsa_id == "GHSA-1111-2222-3333"
    assert result[0].repository.owner == "test"
    assert result[0].repository.name == "repo1"
    assert result[0].severity == "HIGH"
    assert result[1].ghsa_id == "GHSA-4444-5555-6666"
    assert result[1].severity == "CRITICAL"
    assert len(vuln_data.listed_iter) == 1
    assert vuln_data.listed_iter[0][1] == True  # detailed


def test_list_usecase_with_filter():
    """Test listing with filter expression."""
    vuln_data = FakeVulnRepo()
    analysis_store = FakeAnalysisStore()

    uc = ListUseCase(vuln_data=vuln_data, analysis_store=analysis_store)

    result = uc.execute(limit=10, ecosystem="npm", detailed=True, filter_expr="stars > 1000", include_analyzed=True)

    assert isinstance(result, list)
    assert len(vuln_data.listed_iter) == 1
    assert vuln_data.listed_iter[0][2] == "stars > 1000"  # filter_expr


def test_list_usecase_excludes_analyzed():
    """Test that analyzed vulnerabilities are excluded when include_analyzed=False."""
    vuln_data = FakeVulnRepo()
    # Mark GHSA-1111-2222-3333 as analyzed
    analysis_store = FakeAnalysisStore(analyzed_ids={"GHSA-1111-2222-3333"})

    uc = ListUseCase(vuln_data=vuln_data, analysis_store=analysis_store)

    result = uc.execute(limit=10, ecosystem="npm", detailed=False, include_analyzed=False)

    # Should only return GHSA-4444-5555-6666 (not analyzed)
    assert result == ["GHSA-4444-5555-6666"]
    assert len(vuln_data.listed_iter) == 1
