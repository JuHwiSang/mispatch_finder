import os
import stat
from pathlib import Path

from mispatch_finder.shared.rmtree_force import rmtree_force


def test_rmtree_force_removes_directory(tmp_path):
    target = tmp_path / "test_dir"
    target.mkdir()
    (target / "file.txt").write_text("test", encoding="utf-8")
    
    rmtree_force(target)
    
    assert not target.exists()


def test_rmtree_force_handles_nested_dirs(tmp_path):
    target = tmp_path / "parent"
    target.mkdir()
    child = target / "child"
    child.mkdir()
    (child / "file.txt").write_text("test", encoding="utf-8")
    
    rmtree_force(target)
    
    assert not target.exists()


def test_rmtree_force_handles_readonly_files(tmp_path):
    target = tmp_path / "readonly_dir"
    target.mkdir()
    
    test_file = target / "readonly.txt"
    test_file.write_text("test", encoding="utf-8")
    
    # Make file readonly
    os.chmod(test_file, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    
    rmtree_force(target)
    
    assert not target.exists()


def test_rmtree_force_handles_nonexistent(tmp_path):
    target = tmp_path / "nonexistent"
    
    # Should not raise
    rmtree_force(target)
    
    assert not target.exists()


def test_rmtree_force_with_symlinks(tmp_path):
    """Test that rmtree_force handles symlinks correctly."""
    target = tmp_path / "with_symlink"
    target.mkdir()
    
    real_file = tmp_path / "real_file.txt"
    real_file.write_text("real content", encoding="utf-8")
    
    link = target / "link.txt"
    try:
        link.symlink_to(real_file)
    except OSError:
        # Symlinks may not be supported on all systems
        import pytest
        pytest.skip("Symlinks not supported")
    
    rmtree_force(target)
    
    assert not target.exists()
    # Real file should still exist
    assert real_file.exists()

