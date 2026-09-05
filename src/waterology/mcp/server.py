import inspect
import logging
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import ParamSpec, TypeVar, cast

from mcp.server import MCPServer

from waterology import __version__, services
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
        title="Waterology research workflows",
        description="Bounded local research operations over durable Waterology project state.",
        instructions=(
            "Use these tools for experiments, runs, evidence, archives, and session notes. "
            "No shell or publication operation is available."
        ),
        version=__version__,
    )

    @_bounded_tool(server)
    def project_status(project_path: str = ".") -> dict[str, object]:
        """Inspect project counts and local index state without changing files."""
        return services.project_status(Path(project_path))

    @_bounded_tool(server)
    def create_experiment(
        hypothesis: str,
        project_path: str = ".",
        parent_ref: str = "HEAD",
        parent_experiment_id: str | None = None,
        owner: str | None = None,
        experiment_id: str | None = None,
    ) -> dict[str, object]:
        """Create a hypothesis branch and isolated worktree; this changes Git and local state."""
        return services.create_experiment_record(
            Path(project_path),
            hypothesis=hypothesis,
            parent_ref=parent_ref,
            parent_experiment_id=parent_experiment_id,
            owner=owner,
            experiment_id=experiment_id,
        )

    @_bounded_tool(server)
    def inspect_experiment(experiment_id: str, project_path: str = ".") -> dict[str, object]:
        """Read one experiment record and its derived scientific state."""
        return services.experiment_status(Path(project_path), experiment_id)

    @_bounded_tool(server)
    def experiment_tree(project_path: str = ".") -> list[dict[str, object]]:
        """List experiments with their parent identifiers and worktrees."""
        return services.experiment_tree(Path(project_path))

    @_bounded_tool(server)
    def start_run(
        experiment_id: str,
        project_path: str = ".",
        profile: str | None = None,
        confirm_remote: bool = False,
    ) -> dict[str, object]:
        """Start a validated run; this executes the committed project command."""
        return services.start_run(
            Path(project_path),
            experiment_id,
            profile=profile,
            confirm_remote=confirm_remote,
        )

    @_bounded_tool(server)
    def inspect_run(run_id: str, project_path: str = ".") -> dict[str, object]:
        """Inspect a terminal archive or reconcile a managed TORC run."""
        return services.run_status(Path(project_path), run_id)

    @_bounded_tool(server)
    def cancel_run(run_id: str, project_path: str = ".") -> dict[str, object]:
        """Request cancellation of a managed TORC run; this changes executor state."""
        return services.cancel_run(Path(project_path), run_id)

    @_bounded_tool(server)
    def assess_run(
        run_id: str,
        kind: str,
        conclusion: str,
        author: str,
        project_path: str = ".",
        evidence: list[str] | None = None,
        note: str | None = None,
    ) -> dict[str, object]:
        """Append a scientific assessment; an answer freezes the experiment."""
        return services.assess_run_record(
            Path(project_path),
            run_id,
            kind=kind,
            conclusion=conclusion,
            author=author,
            evidence=tuple(evidence or ()),
            note=note,
        )

    @_bounded_tool(server)
    def read_run_logs(run_id: str, project_path: str = ".") -> dict[str, str]:
        """Read stdout and stderr from a sealed run archive."""
        return services.run_logs(Path(project_path), run_id)

    @_bounded_tool(server)
    def read_run_metrics(run_id: str, project_path: str = ".") -> dict[str, object]:
        """Read normalized metrics from a sealed run archive."""
        return services.run_metrics(Path(project_path), run_id)

    @_bounded_tool(server)
    def list_archives(project_path: str = ".") -> list[dict[str, object]]:
        """List sealed immutable run archives."""
        return services.archives(Path(project_path))

    @_bounded_tool(server)
    def list_sessions(project_path: str = ".") -> list[dict[str, object]]:
        """List durable top level agent session records."""
        return services.sessions(Path(project_path))

    @_bounded_tool(server)
    def inspect_session(session_id: str, project_path: str = ".") -> dict[str, object]:
        """Read one durable top level agent session record."""
        return services.session_status(Path(project_path), session_id)

    @_bounded_tool(server)
    def read_session_logs(session_id: str, project_path: str = ".") -> list[dict[str, object]]:
        """Read native JSON events and stderr for every session attempt."""
        return services.session_logs(Path(project_path), session_id)

    @_bounded_tool(server)
    def register_evidence(
        experiment_id: str,
        claim: str,
        project_path: str = ".",
        kind: str = "note",
        path: str | None = None,
        run_id: str | None = None,
        session_id: str | None = None,
    ) -> dict[str, object]:
        """Register a claim and optional validated local evidence path; this appends a record."""
        return services.register_evidence_record(
            Path(project_path),
            experiment_id=experiment_id,
            claim=claim,
            kind=kind,
            path=path,
            run_id=run_id,
            session_id=session_id,
        )

    @_bounded_tool(server)
    def register_artifact(
        experiment_id: str,
        path: str,
        project_path: str = ".",
        label: str | None = None,
        run_id: str | None = None,
        session_id: str | None = None,
    ) -> dict[str, object]:
        """Register an existing artifact inside an owned worktree or sealed archive."""
        return services.register_artifact_record(
            Path(project_path),
            experiment_id=experiment_id,
            path=path,
            label=label,
            run_id=run_id,
            session_id=session_id,
        )

    @_bounded_tool(server)
    def record_session_note(
        session_id: str,
        text: str,
        project_path: str = ".",
        author: str | None = None,
    ) -> dict[str, object]:
        """Append a durable note to an agent session."""
        return services.record_session_note(Path(project_path), session_id, text, author)

    from waterology.mcp.workflows import register_workflow_tools
    register_workflow_tools(server, _bounded_tool)
    return server


mcp = create_server()


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
