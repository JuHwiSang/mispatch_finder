from typing import Callable
import os
import stat
from pathlib import Path
import shutil

def _remove_readonly(func: Callable[[str], None], path: str, excinfo) -> None:
    """Helper for shutil.rmtree to clear read-only bits on Windows.

    Mirrors the logic previously duplicated across multiple test files.
    """
    try:
        os.chmod(path, stat.S_IWUSR)
    except OSError:
        pass
    func(path)

def rmtree_force(path: Path):
    if not path.exists():
        return
    try:
        shutil.rmtree(path)
    except PermissionError:
        shutil.rmtree(path, onexc=_remove_readonly)