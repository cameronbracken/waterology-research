"""MCP adapters share the same deterministic services as the CLI."""

from pathlib import Path


def register_workflow_tools(server, bounded_tool):
    from waterology.mcp.knowledge import register_knowledge_tools

    register_knowledge_tools(server, bounded_tool)
    from waterology.core.claims import list_claims, register_claim, verify_claim
    from waterology.core.comparison import compare_runs
    from waterology.core.literature import record_source_decision, search_literature
    from waterology.core.reports import export_report
    from waterology.core.studies import (
        StudyContract,
        advance_study,
        create_study,
        enqueue_candidate,
        list_studies,
        load_study,
        stop_study,
    )

    @bounded_tool(server)
    def study_create(
        contract: dict, authorized_by: str, profile: str | None = None, project_path: str = "."
    ) -> dict:
        """Record existing user authorization and pin bounded TORC evaluation settings."""
        return create_study(
            Path(project_path),
            StudyContract.model_validate(contract),
            profile=profile,
            authorized_by=authorized_by,
        ).model_dump(mode="json")

    @bounded_tool(server)
    def study_status(study_id: str, project_path: str = ".") -> dict:
        """Read durable authorization, queue, attempts and stopping state."""
        return load_study(Path(project_path), study_id).model_dump(mode="json")

    @bounded_tool(server)
    def study_list(project_path: str = ".") -> list[dict]:
        """List durable managed studies."""
        return [r.model_dump(mode="json") for r in list_studies(Path(project_path))]

    @bounded_tool(server)
    def study_enqueue(study_id: str, experiment_id: str, project_path: str = ".") -> dict:
        """Validate and queue a committed candidate within existing study authority."""
        return enqueue_candidate(Path(project_path), study_id, experiment_id).model_dump(
            mode="json"
        )

    @bounded_tool(server)
    def study_advance(study_id: str, project_path: str = ".") -> dict:
        """Reconcile attempts and submit queued evaluations through the pinned TORC profile."""
        return advance_study(Path(project_path), study_id).model_dump(mode="json")

    @bounded_tool(server)
    def study_stop(study_id: str, project_path: str = ".") -> dict:
        """Stop new work and drain or cancel active jobs according to the saved contract."""
        return stop_study(Path(project_path), study_id).model_dump(mode="json")

    @bounded_tool(server)
    def compare_archived_runs(run_ids: list[str], baseline: str, project_path: str = ".") -> dict:
        """Compare verified archived measurements only under compatible evaluation contracts."""
        return compare_runs(Path(project_path), run_ids, baseline=baseline)

    @bounded_tool(server)
    def claim_register(
        claim: str,
        run_id: str,
        member: str = "metrics.json",
        selector: str = "",
        kind: str = "observation",
        relation: str = "supports",
        related_claim: str | None = None,
        project_path: str = ".",
    ) -> dict:
        """Append a claim with a hashed archive member and exact JSON pointer."""
        return register_claim(
            Path(project_path),
            claim=claim,
            run_id=run_id,
            member=member,
            selector=selector,
            kind=kind,
            relation=relation,
            related_claim=related_claim,
        ).model_dump(mode="json")

    @bounded_tool(server)
    def claim_verify(project_path: str = ".") -> list[dict]:
        """Check archive evidence with passport dispositions; inferences stay unverified."""
        return [verify_claim(Path(project_path), c) for c in list_claims(Path(project_path))]

    @bounded_tool(server)
    def literature_search(
        query: str,
        after: str | None = None,
        before: str | None = None,
        limit: int = 20,
        project_path: str = ".",
    ) -> dict:
        """Query OpenAlex once and retain queries, source identities and provider failures."""
        return search_literature(Path(project_path), query, after=after, before=before, limit=limit)

    @bounded_tool(server)
    def literature_decision(
        search_id: str, source_id: str, decision: str, note: str, project_path: str = "."
    ) -> dict:
        """Append an inclusion or exclusion decision without replacing retrieval history."""
        return record_source_decision(
            Path(project_path), search_id, source_id, decision=decision, note=note
        )

    @bounded_tool(server)
    def literature_source_add(title: str, locator: str, note: str, project_path: str = ".") -> dict:
        """Record a local or agency source with its version and access notes."""
        from waterology.core.literature import register_local_source

        return register_local_source(Path(project_path), title=title, locator=locator, note=note)

    @bounded_tool(server)
    def report_export(
        run_ids: list[str], baseline: str, destination: str, project_path: str = "."
    ) -> dict:
        """Create a new Quarto bundle from selected archived runs without publishing it."""
        return export_report(
            Path(project_path), run_ids, baseline=baseline, destination=destination
        )

    @bounded_tool(server)
    def study_driver_configure(
        study_id: str, runtime: str, max_proposals: int, project_path: str = "."
    ) -> dict:
        """Record explicitly authorized bounded candidate generation with an existing runtime."""
        from waterology.core.study_driver import configure_driver

        return configure_driver(
            Path(project_path), study_id, runtime=runtime, max_proposals=max_proposals
        )

    @bounded_tool(server)
    def study_drive(study_id: str, project_path: str = ".") -> dict:
        """Advance the saved candidate driver and TORC controller without changing authority."""
        from waterology.core.study_driver import drive_study

        return drive_study(Path(project_path), study_id)

    @bounded_tool(server)
    def claim_assess(
        claim_id: str, status: str, author: str, note: str, project_path: str = "."
    ) -> dict:
        """Append an explicit claim-support assessment; byte verification alone is insufficient."""
        from waterology.core.claims import assess_claim

        return assess_claim(Path(project_path), claim_id, status=status, author=author, note=note)

    @bounded_tool(server)
    def study_conclude(
        study_id: str, conclusion: str, evidence: list[str], author: str, project_path: str = "."
    ) -> dict:
        """Stop a research study with an explicit conclusion tied to assessed study claims."""
        from waterology.core.studies import conclude_study

        return conclude_study(
            Path(project_path), study_id, conclusion=conclusion, evidence=evidence, author=author
        ).model_dump(mode="json")
