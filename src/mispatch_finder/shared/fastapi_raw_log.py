# mcp_wiretap.py
import json
from fastmcp.server.middleware import Middleware, MiddlewareContext

def _to_jsonable(x):
    if hasattr(x, "model_dump"):
        return x.model_dump()
    if hasattr(x, "__dict__"):
        return x.__dict__
    return x

class MCPWiretap(Middleware):
    async def on_message(self, ctx: MiddlewareContext, call_next):
        # 들어오는 MCP JSON-RPC 요청
        try:
            breakpoint()
            print(">>>", ctx.method, json.dumps(_to_jsonable(ctx.message), ensure_ascii=False, default=str))
        except Exception:
            print(">>>", ctx.method, repr(ctx.message))

        result = await call_next(ctx)

        # 나가는 MCP 응답
        try:
            print("<<<", ctx.method, json.dumps(_to_jsonable(result), ensure_ascii=False, default=str))
        except Exception:
            print("<<<", ctx.method, repr(result))

        return result
