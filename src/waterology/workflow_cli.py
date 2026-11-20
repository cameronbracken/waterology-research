"""CLI commands for scholarly discovery, Zotero reference sync, and Hugging Face Hub inspection."""

import json
from contextvars import ContextVar
from pathlib import Path

import typer

from waterology.core.formats import load_document, readable
from waterology.core.zotero import (
    configure_zotero,
    initialize_zotero,
    queue_reference,
    reference_status,
    settings_for,
    sync_references,
)

_PATH_OPTION = typer.Option(Path("."))
OUTPUT_FORMAT = ContextVar("waterology_output_format", default="yaml")

zotero_app = typer.Typer(help="Manage a project .zotero.toml collection and local PDF cache.")


def emit(value):
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    output_format = OUTPUT_FORMAT.get()
    typer.echo(
        json.dumps(value, indent=2, allow_nan=False)
        if output_format == "json"
        else readable(value),
        nl=output_format == "json",
    )


@zotero_app.command("init")
def init_zotero(
    collection_name: str,
    group_id: str | None = typer.Option(None),
    api_key_env: str = typer.Option("ZOTERO_API_KEY"),
    path: Path = _PATH_OPTION,
):
    """Create standalone .zotero.toml settings using the library associated with the API key."""
    try:
        emit(initialize_zotero(path, collection_name, group_id=group_id, api_key_env=api_key_env))
    except ValueError as error:
        raise typer.BadParameter(str(error)) from None


@zotero_app.command("configure")
def configure(document: Path, path: Path = _PATH_OPTION):
    """Write .zotero.toml from an explicit TOML or YAML document."""
    emit(configure_zotero(path, load_document(document)))


@zotero_app.command("status")
def status(path: Path = _PATH_OPTION):
    """Inspect queued references and PDF download status."""
    config = settings_for(path)
    emit({"configured": config is not None, "references": reference_status(path)})


@zotero_app.command("sync")
def sync(limit: int = typer.Option(20, min=1, max=100), path: Path = _PATH_OPTION):
    """Synchronize pending Zotero metadata and local PDF cache entries."""
    emit(sync_references(path, limit=limit))


@zotero_app.command("capture")
def capture(
    document: Path,
    reason: str = typer.Option("Consulted during research"),
    path: Path = _PATH_OPTION,
):
    """Queue and sync a consulted citation from a YAML or TOML file."""
    emit(queue_reference(path, load_document(document), reason=reason))


def register_reference_commands(app: typer.Typer) -> None:
    app.add_typer(zotero_app, name="zotero")

    @app.command("research-access")
    def access():
        """Check research API key availability without printing secrets or making requests."""
        from waterology.core.research_access import research_access

        emit(research_access())

    @app.command("discover")
    def discover(
        query: str,
        provider: str = typer.Option(
            "openalex",
            help=(
                "Scholarly provider: openalex, semantic-scholar, core, alphaxiv, "
                "alphaxiv-keyword, arxiv, pubmed, europepmc, biorxiv, medrxiv, or crossref."
            ),
        ),
        after: str | None = typer.Option(None),
        before: str | None = typer.Option(None),
        limit: int = typer.Option(20, min=1, max=100),
        path: Path = _PATH_OPTION,
    ):
        """Search a scholarly provider, recording locally when .zotero.toml is configured."""
        from waterology.core.literature import search_literature

        emit(
            search_literature(
                path, query, after=after, before=before, limit=limit, provider=provider
            )
        )

    @app.command("source-decision")
    def decision(
        search_id: str, source_id: str, decision: str, note: str, path: Path = _PATH_OPTION
    ):
        """Record an include, exclude, or unresolved decision for a recorded search hit."""
        from waterology.core.literature import record_source_decision

        emit(record_source_decision(path, search_id, source_id, decision=decision, note=note))

    @app.command("source-add")
    def source_add(title: str, locator: str, note: str = "", path: Path = _PATH_OPTION):
        """Register a local or agency source and queue it to Zotero when configured."""
        from waterology.core.literature import register_local_source

        emit(register_local_source(path, title=title, locator=locator, note=note))

    @app.command("hf-dataset-info")
    def hf_dataset_info_command(
        repo_id: str,
        revision: str = typer.Option("main"),
    ):
        """Inspect bounded Hugging Face Hub dataset metadata, splits, and license."""
        from waterology.core import huggingface

        emit(huggingface.hf_dataset_info(repo_id, revision=revision))

    @app.command("hf-repo-files")
    def hf_repo_files_command(
        repo_id: str,
        repo_type: str = typer.Option("dataset"),
        revision: str = typer.Option("main"),
        subpath: str = typer.Option("", "--subpath"),
        limit: int = typer.Option(200, min=1, max=1000),
    ):
        """List files and directories inside a Hugging Face Hub repository."""
        from waterology.core import huggingface

        emit(
            huggingface.hf_repo_files(
                repo_id, repo_type=repo_type, revision=revision, path=subpath, limit=limit
            )
        )

    @app.command("hf-repo-read-file")
    def hf_repo_read_file_command(
        repo_id: str,
        file_path: str,
        repo_type: str = typer.Option("dataset"),
        revision: str = typer.Option("main"),
        max_bytes: int = typer.Option(65536, min=1, max=262144),
    ):
        """Read a bounded UTF-8 text file from a Hugging Face Hub repository."""
        from waterology.core import huggingface

        emit(
            huggingface.hf_repo_read_file(
                repo_id,
                file_path,
                repo_type=repo_type,
                revision=revision,
                max_bytes=max_bytes,
            )
        )
