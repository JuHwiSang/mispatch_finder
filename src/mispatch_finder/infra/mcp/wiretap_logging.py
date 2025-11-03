from __future__ import annotations

import logging
from fastmcp.server.middleware import Middleware, MiddlewareContext
from mispatch_finder.shared.to_jsonable import to_jsonable

logger = logging.getLogger(__name__)


class WiretapLoggingMiddleware(Middleware):
    async def on_message(self, ctx: MiddlewareContext, call_next):
        # log incoming request fully (avoid 'message' - it's reserved by logging)
        logger.info("mcp_request", extra={
            "type": "request",
            "method": ctx.method,
            "mcp_message": to_jsonable(ctx.message),
        })
        result = await call_next(ctx)
        # log outgoing response fully
        logger.info("mcp_response", extra={
            "type": "response",
            "method": ctx.method,
            "mcp_result": to_jsonable(result),
        })
        return result


