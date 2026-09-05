"""Shared project learning and Zotero service adapters."""

from pathlib import Path


def register_knowledge_tools(server, bounded_tool):
    @bounded_tool(server)
    def research_access() -> dict:
        """Check Zotero/OpenAlex environment credential presence; never expose values."""
        from waterology.core.research_access import research_access as check

        return check()

    from waterology.core.learning import (
        assess_lesson,
        lesson_context,
        list_lessons,
        propose_improvement,
        remember,
    )
    from waterology.core.zotero import queue_reference, reference_status, sync_references

    @bounded_tool(server)
    def learning_remember(
        trigger: str,
        action: str,
        evidence: list[str],
        outcome: str,
        tags: list[str],
        project_path: str = ".",
    ) -> dict:
        """Record a project lesson with hashed evidence. It remains proposed until assessed."""
        return remember(
            Path(project_path),
            trigger=trigger,
            action=action,
            evidence=evidence,
            outcome=outcome,
            tags=tags,
        )

    @bounded_tool(server)
    def learning_assess(
        identifier: str, status: str, author: str, note: str, project_path: str = "."
    ) -> dict:
        """Append a lesson assessment without rewriting its evidence."""
        return assess_lesson(
            Path(project_path), identifier, status=status, author=author, note=note
        )

    @bounded_tool(server)
    def learning_context(query: str, project_path: str = ".") -> list[dict]:
        """Retrieve relevant verified project lessons with current evidence."""
        return lesson_context(Path(project_path), query)

    @bounded_tool(server)
    def learning_status(project_path: str = ".") -> list[dict]:
        """List lessons, stale evidence and assessment history."""
        return list_lessons(Path(project_path))

    @bounded_tool(server)
    def learning_improve(
        identifiers: list[str], change: str, validation: str, project_path: str = "."
    ) -> dict:
        """Create a reviewable shared improvement proposal. Does not edit shared skills."""
        return propose_improvement(
            Path(project_path), identifiers, change=change, validation=validation
        )

    @bounded_tool(server)
    def zotero_capture(source: dict, reason: str, project_path: str = ".") -> dict:
        """Queue a consulted citation and synchronize to the configured project collection."""
        return queue_reference(Path(project_path), source, reason=reason)

    @bounded_tool(server)
    def zotero_sync(limit: int = 20, project_path: str = ".") -> dict:
        """Retry bounded pending metadata and PDF work using saved library and object identities."""
        return sync_references(Path(project_path), limit=limit)

    @bounded_tool(server)
    def zotero_status(project_path: str = ".") -> list[dict]:
        """Inspect distinct citation and attachment states without exposing credentials."""
        return reference_status(Path(project_path))
