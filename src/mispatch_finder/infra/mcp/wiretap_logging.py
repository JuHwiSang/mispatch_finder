from __future__ import annotations

import logging
from fastmcp.server.middleware import Middleware, MiddlewareContext
from mispatch_finder.shared.to_jsonable import to_jsonable


class WiretapLoggingMiddleware(Middleware):
    def __init__(self, logger_name: str = __name__) -> None:
        self._logger = logging.getLogger(logger_name)

    async def on_message(self, ctx: MiddlewareContext, call_next):
        # log incoming request fully as payload
        self._logger.info("mcp_request", extra={
            "payload": {
                "type": "request",
                "method": ctx.method,
                "message": to_jsonable(ctx.message),
            }
        })
        result = await call_next(ctx)
        # log outgoing response fully as payload
        self._logger.info("mcp_response", extra={
            "payload": {
                "type": "response",
                "method": ctx.method,
                "result": to_jsonable(result),
            }
        })
        return result


