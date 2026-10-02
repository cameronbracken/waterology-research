"""Human-readable project learning and reference library commands."""

from pathlib import Path

import typer

from waterology.core.formats import load_document
from waterology.core.learning import (
    assess_lesson,
    lesson_context,
    list_lessons,
    propose_improvement,
    remember,
)
from waterology.core.zotero import (
    configure_zotero,
    initialize_zotero,
    queue_reference,
    reference_status,
    settings_for,
    sync_references,
)
from waterology.workflow_cli import emit

_PATH = typer.Option(Path("."))
learning = typer.Typer(help="Remember project lessons, verify evidence and propose improvements.")
zotero = typer.Typer(help="Build a project Zotero collection and retain PDF sync status.")


@learning.command("remember")
def remember_command(document: Path, path: Path = _PATH):
    emit(remember(path, **load_document(document)))


@learning.command("list")
def list_command(path: Path = _PATH):
    emit(list_lessons(path))


@learning.command("assess")
def assess(
    identifier: str,
    status: str,
    author: str = typer.Option(...),
    note: str = typer.Option(...),
    path: Path = _PATH,
):
    emit(assess_lesson(path, identifier, status=status, author=author, note=note))


@learning.command("context")
def context(query: str, path: Path = _PATH):
    emit(lesson_context(path, query))


@learning.command("improve")
def improve(document: Path, path: Path = _PATH):
    emit(propose_improvement(path, **load_document(document)))


@zotero.command("init")
def init_zotero(
    collection_name: str,
    group_id: str | None = typer.Option(None),
    api_key_env: str = typer.Option("ZOTERO_API_KEY"),
    path: Path = _PATH,
):
    """Create project TOML settings using the library associated with the API key."""
    try:
        emit(initialize_zotero(path, collection_name, group_id=group_id, api_key_env=api_key_env))
    except ValueError as error:
        raise typer.BadParameter(str(error)) from None


@zotero.command("configure")
def configure(document: Path, path: Path = _PATH):
    emit(configure_zotero(path, load_document(document)))


@zotero.command("status")
def status(path: Path = _PATH):
    config = settings_for(path)
    emit({"configured": config is not None, "references": reference_status(path)})


@zotero.command("sync")
def sync(limit: int = typer.Option(20, min=1, max=100), path: Path = _PATH):
    emit(sync_references(path, limit=limit))


@zotero.command("capture")
def capture(
    document: Path, reason: str = typer.Option("Consulted during research"), path: Path = _PATH
):
    emit(queue_reference(path, load_document(document), reason=reason))


def register_knowledge_commands(app):
    app.add_typer(learning, name="learning")
    app.add_typer(zotero, name="zotero")

    @app.command("research-access")
    def access():
        """Check Zotero/OpenAlex credential availability without printing secrets or making requests."""
        from waterology.core.research_access import research_access

        emit(research_access())
