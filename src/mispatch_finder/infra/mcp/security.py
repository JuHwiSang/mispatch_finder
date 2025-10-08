from __future__ import annotations

from typing import Callable


def build_auth_middleware(expected_token: str) -> Callable[[dict], bool]:
    """Very light middleware signature for fastMCP-like servers.

    For a real FastAPI app, you'd inspect request headers; here we keep a minimal signature.
    """

    def _middleware(scope: dict) -> bool:
        headers = dict(scope.get("headers", []))  # list[tuple[bytes, bytes]] expected
        auth = headers.get(b"authorization")
        if not auth:
            return False
        value = auth.decode("utf-8")
        return value.strip() == f"Bearer {expected_token}"

    return _middleware


