"""Agent adapters over the same named workflow services as the CLI."""

from pathlib import Path

from waterology.core.config import DeliverableConfig, WorkflowConfig
from waterology.core.project import discover_project
from waterology.core.registry import refresh_configuration, register_workflow
from waterology.core.reproduction import export_deliverable, register_deliverable
from waterology.core.workflows import run_workflow


def register_execution_tools(server, bounded_tool):
    @bounded_tool(server)
    def workflow_list(project_path: str = ".") -> dict:
        return {
            name: value.model_dump(mode="json")
            for name, value in discover_project(Path(project_path)).config.workflows.items()
        }

    @bounded_tool(server)
    def config_refresh(project_path: str = ".", check: bool = True) -> dict:
        """Inspect drift or apply safe discovered defaults without running compute."""
        return refresh_configuration(Path(project_path), check=check)

    @bounded_tool(server)
    def workflow_register(name: str, definition: dict, project_path: str = ".") -> dict:
        return register_workflow(
            Path(project_path), name, WorkflowConfig.model_validate(definition)
        )

    @bounded_tool(server)
    def workflow_run(name: str, project_path: str = ".", profile: str | None = None) -> dict:
        """Submit authorized computation to TORC; use run_status for collection and recovery."""
        return run_workflow(Path(project_path), name, profile=profile).model_dump(mode="json")

    @bounded_tool(server)
    def deliverable_register(name: str, definition: dict, project_path: str = ".") -> dict:
        return register_deliverable(
            Path(project_path), name, DeliverableConfig.model_validate(definition)
        )

    @bounded_tool(server)
    def deliverable_export(name: str, destination: str, project_path: str = ".") -> dict:
        return export_deliverable(Path(project_path), name, Path(destination))

    @bounded_tool(server)
    def study_register_create(
        contract_path: str, authorized_by: str, project_path: str = ".", profile: str | None = None
    ) -> dict:
        from waterology.core.workflows import create_registered_study

        return create_registered_study(
            Path(project_path), Path(contract_path), authorized_by=authorized_by, profile=profile
        ).model_dump(mode="json")

    @bounded_tool(server)
    def deliverable_reproduce(
        name: str,
        destination: str,
        project_path: str = ".",
        profile: str | None = None,
        bundle: bool = False,
        resume: bool = False,
        inputs: str | None = None,
    ) -> dict:
        """Advance one authorized reproduction; resume the same destination to collect evidence."""
        from waterology.core.reproduction import reproduce_deliverable

        return reproduce_deliverable(
            Path(project_path),
            name,
            Path(destination),
            profile=profile,
            bundle=bundle,
            resume=resume,
            inputs=Path(inputs) if inputs else None,
            wait=False,
        )
