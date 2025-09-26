from __future__ import annotations

from typing import Dict


def describe_available_tools(has_previous: bool, has_current: bool) -> Dict[str, bool]:
    return {
        "previous/repo": has_previous,
        "current/repo": has_current,
    }


