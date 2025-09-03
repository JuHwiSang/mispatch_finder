from __future__ import annotations

from typing import Dict


def describe_available_tools(has_pre: bool, has_post: bool) -> Dict[str, bool]:
    return {
        "pre/repo": has_pre,
        "pre/debug": has_pre,
        "post/repo": has_post,
        "post/debug": has_post,
    }


