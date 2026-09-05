"""Capture managed run settings and reject stale output collection."""

import hashlib
import json
from pathlib import Path

from waterology.core.atomic import write_json
from waterology.core.config import ProjectConfig
from waterology.core.git import current_commit, is_clean
from waterology.core.profiles import ComputeProfile


def output_signatures(worktree: Path, config: ProjectConfig) -> dict:
    signatures = {}
    for relative in config.outputs:
        root = worktree / relative
        files = [root] if root.is_file() else sorted(root.rglob("*")) if root.is_dir() else []
        for path in files:
            if path.is_symlink() or not path.resolve().is_relative_to(worktree.resolve()):
                raise ValueError("Managed outputs must remain inside the candidate worktree")
            if path.is_file():
                stat = path.stat()
                signatures[path.relative_to(worktree).as_posix()] = {
                    "mtime_ns": stat.st_mtime_ns,
                    "size": stat.st_size,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
    return signatures


def save_snapshot(
    staging: Path, worktree: Path, config: ProjectConfig, profile: ComputeProfile, commit: str
) -> None:
    write_json(
        staging / "execution-config.json",
        {
            "config": config.model_dump(mode="json"),
            "profile": profile.model_dump(mode="json", exclude={"trusted"}),
            "commit_sha": commit,
            "outputs_before": output_signatures(worktree, config),
        },
    )


def load_snapshot(staging: Path) -> tuple[ProjectConfig, ComputeProfile] | None:
    path = staging / "execution-config.json"
    if not path.exists():
        return None
    if path.is_symlink():
        raise ValueError("Execution snapshot must not be a symlink")
    saved = json.loads(path.read_text())
    return ProjectConfig.model_validate(saved["config"]), ComputeProfile.model_validate(
        saved["profile"]
    )


def verify_fresh_outputs(staging: Path, worktree: Path, config: ProjectConfig) -> None:
    path = staging / "execution-config.json"
    if not path.exists():
        return
    saved = json.loads(path.read_text())
    if current_commit(worktree) != saved["commit_sha"] or not is_clean(worktree):
        raise ValueError("Candidate commit changed during execution")
    before = saved["outputs_before"]
    after = output_signatures(worktree, config)
    stale = [relative for relative, signature in after.items() if before.get(relative) == signature]
    if stale:
        raise ValueError("Managed run left unchanged prior outputs: " + ", ".join(stale))
