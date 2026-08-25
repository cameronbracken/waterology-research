import asyncio
import sys
from pathlib import Path

from mcp import Client, StdioServerParameters


def test_stdio_entry_point_completes_protocol_handshake(tmp_path: Path) -> None:
    async def exercise() -> None:
        parameters = StdioServerParameters(
            command=sys.executable,
            args=["-m", "waterology.mcp.server"],
            cwd=str(tmp_path),
        )
        async with Client(parameters) as client:
            tools = await client.list_tools()
        assert any(tool.name == "project_status" for tool in tools.tools)

    asyncio.run(exercise())
