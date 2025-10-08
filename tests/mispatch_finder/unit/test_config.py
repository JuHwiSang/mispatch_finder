import os
from mispatch_finder.app import config as cfg


def test_get_prompt_diff_max_chars_default(monkeypatch):
    monkeypatch.delenv("MISPATCH_DIFF_MAX_CHARS", raising=False)
    assert cfg.get_prompt_diff_max_chars() == 200_000


def test_get_prompt_diff_max_chars_env(monkeypatch):
    monkeypatch.setenv("MISPATCH_DIFF_MAX_CHARS", "12345")
    assert cfg.get_prompt_diff_max_chars() == 12345


# def test_get_prompt_diff_max_chars_bad(monkeypatch):
#     monkeypatch.setenv("MISPATCH_DIFF_MAX_CHARS", "not-an-int")
#     assert cfg.get_prompt_diff_max_chars() == 200_000


def test_cache_and_results_dirs(tmp_path, monkeypatch):
    # Overwrite platformdirs by patching cfg._dirs to a dummy returning path under tmp
    class DummyDirs:
        def __init__(self, base):
            self.user_cache_dir = str(base / "cache")

    monkeypatch.setattr(cfg, "_dirs", lambda: DummyDirs(tmp_path))

    cache = cfg.get_cache_dir()
    assert cache.exists()
    results = cfg.get_results_dir()
    assert results.exists()

