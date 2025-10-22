from __future__ import annotations

from pathlib import Path

from ..core.ports import CachePort
from ..shared.rmtree_force import rmtree_force


class Cache:
    def __init__(self, *, cache_dir: Path) -> None:
        self._cache_dir = cache_dir

    def clear_all(self) -> None:
        rmtree_force(self._cache_dir)

