import hashlib
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

from waterology.core.config import ProjectConfig


class TorcWorkflowRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str = Field(pattern=r"^run-[a-z0-9][a-z0-9-]{0,62}$")
    experiment_id: str = Field(pattern=r"^exp-[a-z0-9][a-z0-9-]{0,62}$")
    commit_sha: str = Field(pattern=r"^[0-9a-f]{40,64}$")
    mode: Literal["local", "remote", "slurm"]
    target_shell: Literal["posix", "windows"] = "posix"
    torc_profile: str | None = None


@dataclass(frozen=True)
class TorcWorkflowFile:
    path: Path
    sha256: str


def render_workflow(config: ProjectConfig, request: TorcWorkflowRequest) -> str:
    resource_requirements: dict[str, int | str] = {
        "name": "waterology-resources",
        "num_cpus": config.resources.cpus,
        "num_gpus": config.resources.gpus,
    }
    resource_requirements["memory"] = f"{config.resources.memory_mb}m"
    if config.resources.walltime_minutes is not None:
        resource_requirements["runtime"] = f"PT{config.resources.walltime_minutes}M"
    execution_config = {"mode": "slurm" if request.mode == "slurm" else "direct"}
    if request.target_shell == "windows":
        fixed_command = subprocess.list2cmdline(config.command)
        command = f'cd /d "%TORC_WORKFLOW_SUBMISSION_DIR%" && {fixed_command}'
    else:
        fixed_command = shlex.join(config.command)
        command = f'cd "$TORC_WORKFLOW_SUBMISSION_DIR" && exec {fixed_command}'
    document = {
        "name": f"waterology-{request.run_id}",
        "description": f"Waterology experiment {request.experiment_id}",
        "metadata": {
            "waterology_commit": request.commit_sha,
            "waterology_experiment_id": request.experiment_id,
            "waterology_run_id": request.run_id,
            "waterology_declared_outputs": list(config.outputs),
        },
        "resource_requirements": [resource_requirements],
        "execution_config": execution_config,
        "resource_monitor": {
            "sample_interval_seconds": 5,
            "jobs": {"enabled": True, "granularity": "time_series"},
        },
        "jobs": [
            {
                "name": request.run_id,
                "command": command,
                "resource_requirements": "waterology-resources",
            }
        ],
    }
    return yaml.safe_dump(document, sort_keys=False, allow_unicode=False)


def write_workflow(
    destination: Path,
    config: ProjectConfig,
    request: TorcWorkflowRequest,
) -> TorcWorkflowFile:
    content = render_workflow(config, request)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(destination)
    return TorcWorkflowFile(
        path=destination,
        sha256=hashlib.sha256(content.encode("utf-8")).hexdigest(),
    )
