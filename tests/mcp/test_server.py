import asyncio
from pathlib import Path

from mcp import Client

import waterology.mcp.server as server_module

EXPECTED_TOOLS = {
    "research_access",
    "literature_search",
    "literature_decision",
    "literature_source_add",
    "zotero_capture",
    "zotero_sync",
    "zotero_status",
    "hf_dataset_info",
    "hf_repo_files",
    "hf_repo_read_file",
}


def test_server_exposes_exact_ten_reference_and_dataset_tools() -> None:
    async def exercise() -> None:
        server = server_module.create_server()
        async with Client(server, raise_exceptions=True) as client:
            listed = await client.list_tools()
        names = {tool.name for tool in listed.tools}
        assert names == EXPECTED_TOOLS
        assert not any("shell" in name or "command" in name for name in names)

    asyncio.run(exercise())


def test_literature_search_runs_unrecorded_by_default(monkeypatch, tmp_path: Path) -> None:
    from waterology.core import literature

    monkeypatch.setattr(
        literature,
        "fetch_openalex",
        lambda *a, **kw: {"results": [{"id": "W1", "display_name": "Streamflow benchmark"}]},
    )

    async def exercise() -> None:
        server = server_module.create_server()
        async with Client(server, raise_exceptions=True) as client:
            result = await client.call_tool(
                "literature_search",
                {"query": "streamflow", "project_path": str(tmp_path)},
            )
        assert result.is_error is False
        payload = result.structured_content
        assert payload["ok"] is True
        assert payload["result"]["recorded"] is False
        assert payload["result"]["sources"][0]["title"] == "Streamflow benchmark"
        assert not (tmp_path / ".waterology").exists()

    asyncio.run(exercise())


def test_tool_errors_return_stable_structured_codes(tmp_path: Path) -> None:
    async def exercise() -> None:
        server = server_module.create_server()
        async with Client(server, raise_exceptions=True) as client:
            result = await client.call_tool(
                "literature_decision",
                {
                    "search_id": "invalid-id",
                    "source_id": "W1",
                    "decision": "include",
                    "note": "Relevant",
                    "project_path": str(tmp_path),
                },
            )
        assert result.is_error is False
        assert result.structured_content == {
            "ok": False,
            "error": {
                "code": "invalid_input",
                "details": {},
                "message": "Invalid search identifier",
            },
        }

    asyncio.run(exercise())
