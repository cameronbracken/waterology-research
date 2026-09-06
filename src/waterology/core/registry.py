"""Project discovery and atomic, comment-preserving workflow registration."""

import hashlib
import json
import tomllib
from pathlib import Path

import tomlkit
import yaml

from waterology.core.atomic import write_text
from waterology.core.config import ProjectConfig, WorkflowConfig, load_project_config
from waterology.core.project import discover_project, project_state_lock


def _name(name: str) -> str:
    import re

    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]{0,95}", name):
        raise ValueError("Names must start with a letter and use letters, numbers, _, . or -")
    return name


def project_file(root: Path, relative: str) -> Path:
    from waterology.core.config import _portable_project_path

    _portable_project_path(relative)
    path = root / relative
    if not path.resolve().is_relative_to(root.resolve()) or path.is_symlink():
        raise ValueError(f"Project reference escapes project or is a symlink: {relative}")
    return path


def discover_configuration(root: Path) -> dict:
    files = []
    workflows = {}
    notes = []
    managers = []
    pixi = root / "pixi.toml"
    pyproject = root / "pyproject.toml"
    data = {}
    if pixi.is_file():
        data = tomllib.loads(project_file(root, "pixi.toml").read_text())
        files.append("pixi.toml")
    elif pyproject.is_file():
        data = (
            tomllib.loads(project_file(root, "pyproject.toml").read_text())
            .get("tool", {})
            .get("pixi", {})
        )
        files.append("pyproject.toml")
    if data:
        managers.append("pixi")
        if (root / "pixi.lock").is_file():
            files.append("pixi.lock")
        else:
            notes.append("Pixi lockfile is missing; reproduction requires a lock")
        for name, task in data.get("tasks", {}).items():
            try:
                _name(name)
            except ValueError:
                notes.append(f"Task requires an explicit Waterology alias: {name}")
                continue
            outputs = task.get("outputs", []) if isinstance(task, dict) else []
            # Native globs remain native; only literal output declarations can be archived here.
            outputs = [p for p in outputs if not any(c in p for c in "*?[")]
            workflows[name] = WorkflowConfig(
                command=("pixi", "run", "--locked", name),
                environment_files=tuple(files),
                outputs=tuple(outputs),
                restore=(("pixi", "install", "--locked"),),
                environment_probe=("pixi", "info", "--json"),
                description=f"Discovered Pixi task {name}",
            ).model_dump(mode="json", exclude_none=True)
    if (root / "uv.lock").is_file():
        managers.append("uv")
        files.extend(p for p in ("pyproject.toml", "uv.lock") if (root / p).is_file())
        notes.append("uv environment detected; register an explicit execution command")
    if (root / "rproject.toml").is_file() or (root / "rv.lock").is_file():
        managers.append("rv")
        files.extend(p for p in ("rproject.toml", "rv.lock", ".Rprofile") if (root / p).is_file())
        notes.append("rv environment detected; register execution and restore commands explicitly")
    if len(managers) > 1:
        notes.append(
            "Multiple environment managers detected; select environment files for each workflow"
        )
    native_files = set((root / "workflows").glob("*.yaml")) | set(
        (root / "workflows").glob("*.yml")
    )
    native_files.update(
        root / name
        for name in ("torc.yaml", "workflow.yaml", "torc.yml", "workflow.yml")
        if (root / name).is_file()
    )
    for path in sorted(native_files):
        relative = path.relative_to(root).as_posix()
        document = yaml.safe_load(project_file(root, relative).read_text())
        if isinstance(document, dict) and isinstance(document.get("jobs"), list):
            name = _name(path.stem)
            if name in workflows:
                notes.append(f"Ambiguous workflow {name}: Pixi task and TORC file {relative}")
                workflows.pop(name)
                continue
            workflows[name] = WorkflowConfig(torc_file=relative).model_dump(
                mode="json", exclude_none=True
            )
    return {"environment_files": sorted(set(files)), "workflows": workflows, "notes": notes}


def register_entry(start: Path, group: str, name: str, value: object) -> dict:
    project = discover_project(start)
    _name(name)
    with project_state_lock(project.root):
        document = tomlkit.parse(project.paths.config_file.read_text())
        entries = document.setdefault(group, {})
        if name in entries:
            existing = entries[name].unwrap() if hasattr(entries[name], "unwrap") else entries[name]
            if group == "workflows":
                existing = WorkflowConfig.model_validate(existing).model_dump(
                    mode="json", exclude_none=True
                )
            if existing != value:
                raise ValueError(
                    f"{group}.{name} is already registered with a different definition"
                )
            return {"name": name, "changed": False}
        entries[name] = value
        if group == "workflows":
            roots = list(document.get("artifact_roots", ["artifacts"]))
            for output in value.get("outputs", []):
                parent = str(Path(output).parent)
                parent = output if parent == "." else parent
                if not any(output == r or output.startswith(r + "/") for r in roots):
                    roots.append(parent)
            document["artifact_roots"] = roots
        ProjectConfig.model_validate(document.unwrap())
        write_text(project.paths.config_file, tomlkit.dumps(document))
    return {"name": name, "changed": True}


def register_workflow(start: Path, name: str, workflow: WorkflowConfig) -> dict:
    return register_entry(
        start, "workflows", name, workflow.model_dump(mode="json", exclude_none=True)
    )


def refresh_configuration(start: Path, *, check: bool = False) -> dict:
    project = discover_project(start)
    with project_state_lock(project.root):
        document = tomlkit.parse(project.paths.config_file.read_text())
        before = tomlkit.dumps(document)
        detected = discover_configuration(project.root)
        prior = document.get("discovery", {}).get("workflows", {})
        entries = document.setdefault("workflows", {})
        drift = []
        owned = {}
        for name, value in detected["workflows"].items():
            old = prior.get(name)
            current = entries.get(name)
            current_hash = hashlib.sha256(
                json.dumps(
                    current.unwrap() if hasattr(current, "unwrap") else current, sort_keys=True
                ).encode()
            ).hexdigest()
            if current is None or current_hash == old or current == old:
                entries[name] = value
                owned[name] = hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
            elif current != value:
                drift.append(f"Preserved manual workflow: {name}")
        for name in prior:
            if name not in detected["workflows"]:
                drift.append(f"Discovered workflow removed or renamed: {name}")
                owned[name] = prior[name]
        old_env = document.get("discovery", {}).get("environment_files", [])
        if not document.get("environment_files") or document["environment_files"] == old_env:
            document["environment_files"] = detected["environment_files"]
        document["discovery"] = {
            "workflows": owned,
            "environment_files": detected["environment_files"],
        }
        roots = list(document.get("artifact_roots", ["artifacts"]))
        for value in detected["workflows"].values():
            for output in value.get("outputs", []):
                parent = str(Path(output).parent)
                if parent == ".":
                    parent = output
                if not any(output == r or output.startswith(r + "/") for r in roots):
                    roots.append(parent)
        document["artifact_roots"] = roots
        ProjectConfig.model_validate(document.unwrap())
        after = (
            before
            if document.unwrap() == tomlkit.parse(before).unwrap()
            else tomlkit.dumps(document)
        )
        if before != after and not check:
            write_text(project.paths.config_file, after)
        return {
            "changed": before != after,
            "drift": drift,
            "notes": detected["notes"],
            "check": check,
        }


def resolve_workflow(start: Path, name: str) -> ProjectConfig:
    root = Path(start).resolve()
    if not (root / "waterology.toml").is_file():
        root = discover_project(start).root
    config = load_project_config(root / "waterology.toml")
    if name not in config.workflows:
        raise ValueError(f"Unknown workflow {name}; use workflow register or config refresh")
    workflow = config.workflows[name]
    prior = config.discovery.get("workflows", {}).get(name)
    serialized = workflow.model_dump(mode="json", exclude_none=True)
    fingerprint = hashlib.sha256(json.dumps(serialized, sort_keys=True).encode()).hexdigest()
    if prior == fingerprint or prior == serialized:
        detected = discover_configuration(root)["workflows"].get(name)
        if detected != serialized:
            raise ValueError(
                f"Discovered workflow {name} changed or became ambiguous; run config refresh and inspect it"
            )
    for relative in workflow.environment_files or config.environment_files:
        if not project_file(root, relative).is_file():
            raise ValueError(f"Missing environment file: {relative}")
    if workflow.torc_file and not project_file(root, workflow.torc_file).is_file():
        raise ValueError(f"Missing TORC workflow: {workflow.torc_file}")
    for relative, expected in workflow.input_files.items():
        path = project_file(root, relative)
        if not path.is_file() or file_sha256(path) != expected:
            raise ValueError(
                f"Missing or changed input: {relative}; {workflow.input_instructions.get(relative, 'supply the pinned input')}"
            )
    return config.model_copy(
        update={
            "command": workflow.command or ("torc", "workflow", workflow.torc_file),
            "torc_file": workflow.torc_file,
            "restore": workflow.restore,
            "environment_probe": workflow.environment_probe,
            "outputs": workflow.outputs,
            "metrics": workflow.metrics,
            "environment_files": workflow.environment_files or config.environment_files,
        }
    )


def file_sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def materialize_inputs(origin: Path, destination: Path, identities: dict[str, str]) -> None:
    import shutil

    for relative, expected in identities.items():
        target = project_file(destination, relative)
        if target.is_file():
            if file_sha256(target) != expected:
                raise ValueError(f"Existing input has a different identity: {relative}")
            continue
        source = project_file(origin, relative)
        if not source.is_file() or file_sha256(source) != expected:
            raise ValueError(f"Input is missing or changed: {relative}")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        if file_sha256(target) != expected:
            raise ValueError(f"Input changed while copying: {relative}")
