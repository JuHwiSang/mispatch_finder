# mcp_wiretap.py
import json
from fastmcp.server.middleware import Middleware, MiddlewareContext

def _to_jsonable(x):
    return x

class MCPWiretap(Middleware):
    async def on_message(self, ctx: MiddlewareContext, call_next):
        # no-op; left as placeholder to be optionally enabled elsewhere
        result = await call_next(ctx)
        return result
