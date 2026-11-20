"""Bounded MCP server for scholarly discovery, Zotero synchronization, and Hugging Face Hub inspection."""

import inspect
import logging
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import ParamSpec, TypeVar, cast

from mcp.server import MCPServer

from waterology import __version__
from waterology.core.errors import WaterologyError

P = ParamSpec("P")
R = TypeVar("R")
_LOGGER = logging.getLogger(__name__)


def _bounded_tool(server: MCPServer) -> Callable[[Callable[P, R]], object]:
    def register(operation: Callable[P, R]) -> object:
        @wraps(operation)
        def guarded(*args: P.args, **kwargs: P.kwargs) -> dict[str, object]:
            try:
                return {"ok": True, "result": operation(*args, **kwargs)}
            except WaterologyError as error:
                return {"ok": False, "error": error.payload()}
            except (TypeError, ValueError) as error:
                return {
                    "ok": False,
                    "error": {"code": "invalid_input", "details": {}, "message": str(error)},
                }
            except Exception:
                _LOGGER.exception("Unexpected MCP tool failure", extra={"tool": operation.__name__})
                return {
                    "ok": False,
                    "error": {
                        "code": "internal_error",
                        "details": {},
                        "message": "The operation failed unexpectedly.",
                    },
                }

        signature = inspect.signature(operation).replace(return_annotation=dict[str, object])
        guarded.__signature__ = signature  # type: ignore[attr-defined]
        return cast(object, server.tool()(guarded))

    return register


def create_server() -> MCPServer:
    server = MCPServer(
        "waterology",
        title="Waterology reference and dataset tools",
        description="Bounded scholarly search, Zotero reference sync, and Hugging Face Hub inspection.",
        instructions=(
            "Use these tools for multi-provider literature search, Zotero collection sync, "
            "and bounded Hugging Face Hub metadata and file inspection."
        ),
        version=__version__,
    )

    @_bounded_tool(server)
    def research_access() -> dict[str, object]:
        """Check Zotero, OpenAlex, Semantic Scholar, CORE, and Hugging Face credential presence; never expose values."""
        from waterology.core.research_access import research_access as check

        return check()

    @_bounded_tool(server)
    def literature_search(
        query: str,
        provider: str = "openalex",
        after: str | None = None,
        before: str | None = None,
        limit: int = 20,
        project_path: str = ".",
    ) -> dict[str, object]:
        """Query a scholarly provider (openalex, semantic-scholar, core, alphaxiv, alphaxiv-keyword, arxiv, pubmed, europepmc, biorxiv, medrxiv, or crossref). Records locally when .zotero.toml is configured and returns unrecorded results otherwise."""
        from waterology.core.literature import search_literature

        return search_literature(
            Path(project_path), query, after=after, before=before, limit=limit, provider=provider
        )

    @_bounded_tool(server)
    def literature_decision(
        search_id: str, source_id: str, decision: str, note: str, project_path: str = "."
    ) -> dict[str, object]:
        """Record an include, exclude, or unresolved decision for a recorded search hit and queue included papers to Zotero."""
        from waterology.core.literature import record_source_decision

        return record_source_decision(
            Path(project_path), search_id, source_id, decision=decision, note=note
        )

    @_bounded_tool(server)
    def literature_source_add(
        title: str, locator: str, note: str = "", project_path: str = "."
    ) -> dict[str, object]:
        """Record a local or agency source and queue it to the configured Zotero collection."""
        from waterology.core.literature import register_local_source

        return register_local_source(Path(project_path), title=title, locator=locator, note=note)

    @_bounded_tool(server)
    def zotero_capture(
        source: dict[str, object], reason: str, project_path: str = "."
    ) -> dict[str, object]:
        """Queue a consulted citation and synchronize to the configured .zotero.toml collection."""
        from waterology.core.zotero import queue_reference

        return queue_reference(Path(project_path), source, reason=reason)

    @_bounded_tool(server)
    def zotero_sync(limit: int = 20, project_path: str = ".") -> dict[str, object]:
        """Retry bounded pending Zotero metadata and local PDF caching."""
        from waterology.core.zotero import sync_references

        return sync_references(Path(project_path), limit=limit)

    @_bounded_tool(server)
    def zotero_status(project_path: str = ".") -> list[dict[str, object]]:
        """Inspect queued Zotero citations and local PDF download states."""
        from waterology.core.zotero import reference_status

        return reference_status(Path(project_path))

    @_bounded_tool(server)
    def hf_dataset_info(repo_id: str, revision: str = "main") -> dict[str, object]:
        """Inspect bounded Hugging Face Hub dataset metadata, configs, features, splits, and license."""
        from waterology.core import huggingface

        return huggingface.hf_dataset_info(repo_id, revision=revision)

    @_bounded_tool(server)
    def hf_repo_files(
        repo_id: str,
        repo_type: str = "dataset",
        revision: str = "main",
        path: str = "",
        limit: int = 200,
    ) -> dict[str, object]:
        """List files and directories at a path in a Hugging Face Hub dataset, model, or space repository."""
        from waterology.core import huggingface

        return huggingface.hf_repo_files(
            repo_id, repo_type=repo_type, revision=revision, path=path, limit=limit
        )

    @_bounded_tool(server)
    def hf_repo_read_file(
        repo_id: str,
        file_path: str,
        repo_type: str = "dataset",
        revision: str = "main",
        max_bytes: int = 65536,
    ) -> dict[str, object]:
        """Read a bounded small UTF-8 text file from a Hugging Face Hub repository without downloading binary blobs."""
        from waterology.core import huggingface

        return huggingface.hf_repo_read_file(
            repo_id, file_path, repo_type=repo_type, revision=revision, max_bytes=max_bytes
        )

    return server


mcp = create_server()


def main() -> None:
    from waterology.core.credentials import load_credentials

    load_credentials()
    mcp.run()


if __name__ == "__main__":
    main()
