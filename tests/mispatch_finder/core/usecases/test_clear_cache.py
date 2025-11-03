"""Tests for ClearCacheUseCase."""
import pytest

from mispatch_finder.core.usecases.clear_cache import ClearCacheUseCase

from tests.mispatch_finder.core.usecases.conftest import FakeVulnRepo


@pytest.mark.skip(reason="clear command disabled - TODO: fix resource conflicts and define clear semantics")
def test_clear_cache_usecase():
    from mispatch_finder.core.ports import CachePort

    class FakeCache:
        def __init__(self):
            self.cleared = False

        def clear_all(self) -> None:
            self.cleared = True

    cache = FakeCache()
    vuln_data = FakeVulnRepo()

    uc = ClearCacheUseCase(cache=cache, vuln_data=vuln_data)
    uc.execute()

    assert cache.cleared
    assert vuln_data.cache_cleared_with == [None]


@pytest.mark.skip(reason="clear command disabled - TODO: fix resource conflicts and define clear semantics")
def test_clear_cache_usecase_with_prefix():
    from mispatch_finder.core.ports import CachePort

    class FakeCache:
        def __init__(self):
            self.cleared = False

        def clear_all(self) -> None:
            self.cleared = True

    cache = FakeCache()
    vuln_data = FakeVulnRepo()

    uc = ClearCacheUseCase(cache=cache, vuln_data=vuln_data)
    uc.execute(vuln_cache_prefix="osv")

    assert cache.cleared
    assert vuln_data.cache_cleared_with == ["osv"]
