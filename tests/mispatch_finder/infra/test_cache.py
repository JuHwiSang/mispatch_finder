from pathlib import Path

from mispatch_finder.infra.cache import Cache


def test_cache_clear_all_removes_directory(tmp_path):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    
    # Create some files
    (cache_dir / "file1.txt").write_text("test", encoding="utf-8")
    (cache_dir / "subdir").mkdir()
    (cache_dir / "subdir" / "file2.txt").write_text("test2", encoding="utf-8")
    
    cache = Cache(cache_dir=cache_dir)
    cache.clear_all()
    
    # Directory should be removed
    assert not cache_dir.exists()


def test_cache_clear_all_handles_nonexistent(tmp_path):
    cache_dir = tmp_path / "nonexistent"
    
    cache = Cache(cache_dir=cache_dir)
    # Should not raise even if directory doesn't exist
    cache.clear_all()
    
    assert not cache_dir.exists()


def test_cache_clear_all_handles_readonly_files(tmp_path):
    """Test that cache clearing works even with readonly files."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    
    test_file = cache_dir / "readonly.txt"
    test_file.write_text("test", encoding="utf-8")
    
    # Make file readonly on Windows/Unix
    import os
    import stat
    os.chmod(test_file, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    
    cache = Cache(cache_dir=cache_dir)
    cache.clear_all()
    
    # Should successfully remove despite readonly
    assert not cache_dir.exists()

