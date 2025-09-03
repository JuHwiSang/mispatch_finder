from typing import Any
import os
import stat
from pathlib import Path
import shutil

def _remove_readonly(func: Any, path: str, excinfo: Any) -> None:
    """Helper for shutil.rmtree to clear read-only bits on Windows.

    Mirrors the logic previously duplicated across multiple test files.
    """
    try:
        os.chmod(path, stat.S_IWUSR)
    except OSError:
        pass
    func(path)

def rmtree_force(path: Path):
    try:
        shutil.rmtree(path)
    except PermissionError:
        shutil.rmtree(path, onexc=_remove_readonly)