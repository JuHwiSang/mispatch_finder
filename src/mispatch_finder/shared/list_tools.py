from fastmcp import FastMCP
from fastmcp.client import Client   
import asyncio


def list_tools(mcp: FastMCP):
    async def list_tools():
        async with Client(mcp) as client:
            tools = await client.list_tools()
            return tools
    return asyncio.run(list_tools())