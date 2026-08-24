import json
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

import yaml

from waterology import __version__
from waterology.runtime.assets import AssetCatalog, AssetNotFoundError
from waterology.runtime.render import GeneratedAssetsStaleError, render_agents

SKILL_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MANIFESTS = (".claude-plugin/plugin.json", ".codex-plugin/plugin.json")
GENERATED_AGENT_DIRECTORIES = (".codex/agents", "agents", ".opencode/agents")


@dataclass(frozen=True)
class ValidationIssue:
    path: str
    code: str
    message: str


def _validate_manifests(catalog: AssetCatalog) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for relative in MANIFESTS:
        try:
            path = catalog.path(relative)
        except AssetNotFoundError:
            issues.append(ValidationIssue(relative, "missing-asset", "required manifest is missing"))
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            issues.append(ValidationIssue(relative, "invalid-json", str(error)))
            continue
        if not isinstance(data, dict):
            issues.append(ValidationIssue(relative, "invalid-manifest", "manifest must be a JSON object"))
            continue
        for field in ("name", "version", "description", "author", "license"):
            if not data.get(field):
                issues.append(ValidationIssue(relative, "missing-field", field))
        if data.get("name") != "waterology":
            issues.append(ValidationIssue(relative, "wrong-name", str(data.get("name"))))
        if data.get("version") != __version__:
            issues.append(ValidationIssue(relative, "wrong-version", str(data.get("version"))))
    return issues


def _frontmatter(path: Path) -> dict[str, object]:
    parts = path.read_text(encoding="utf-8").split("---", 2)
    if len(parts) != 3:
        raise ValueError("missing YAML frontmatter")
    data = yaml.safe_load(parts[1])
    if not isinstance(data, dict):
        raise ValueError("frontmatter must be a mapping")  # noqa: TRY004
    return data


def _validate_skills(catalog: AssetCatalog) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    seen: set[str] = set()
    for directory in catalog.skill_directories():
        path = directory / "SKILL.md"
        relative = path.relative_to(catalog.root).as_posix()
        try:
            data = _frontmatter(path)
        except (ValueError, yaml.YAMLError) as error:
            issues.append(ValidationIssue(relative, "invalid-frontmatter", str(error)))
            continue
        name = str(data.get("name", ""))
        description = str(data.get("description", ""))
        if not SKILL_NAME.fullmatch(name) or name != directory.name:
            issues.append(ValidationIssue(relative, "invalid-name", name))
        if name in seen:
            issues.append(ValidationIssue(relative, "duplicate-name", name))
        seen.add(name)
        if not 1 <= len(description) <= 1024:
            issues.append(ValidationIssue(relative, "invalid-description", str(len(description))))
    return issues


def _validate_generated_agents(catalog: AssetCatalog) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    directories: dict[str, Path] = {}
    unavailable: set[str] = set()
    for relative in GENERATED_AGENT_DIRECTORIES:
        try:
            path = catalog.path(relative)
        except AssetNotFoundError:
            issues.append(
                ValidationIssue(relative, "missing-asset", "required generated-agent directory is missing")
            )
            unavailable.add(relative)
            continue
        if not path.is_dir():
            issues.append(
                ValidationIssue(
                    relative,
                    "invalid-asset-type",
                    "generated-agent asset must be a directory",
                )
            )
            unavailable.add(relative)
            continue
        directories[relative] = path
    try:
        render_agents(catalog, catalog.root, check=True)
    except GeneratedAssetsStaleError as error:
        for path in error.paths:
            relative = path.relative_to(catalog.root).as_posix()
            if any(relative.startswith(f"{directory}/") for directory in unavailable):
                continue
            issues.append(
                ValidationIssue(relative, "stale-generated-agent", "rendered content differs")
            )
    codex_directory = directories.get(".codex/agents")
    if codex_directory is not None:
        for path in sorted(codex_directory.glob("*.toml")):
            try:
                tomllib.loads(path.read_text(encoding="utf-8"))
            except tomllib.TOMLDecodeError as error:
                issues.append(
                    ValidationIssue(
                        path.relative_to(catalog.root).as_posix(), "invalid-toml", str(error)
                    )
                )
    for directory in ("agents", ".opencode/agents"):
        if directory not in directories:
            continue
        for path in sorted(directories[directory].glob("*.md")):
            try:
                _frontmatter(path)
            except (ValueError, yaml.YAMLError) as error:
                issues.append(
                    ValidationIssue(
                        path.relative_to(catalog.root).as_posix(),
                        "invalid-frontmatter",
                        str(error),
                    )
                )
    return issues


def validate_assets(catalog: AssetCatalog) -> tuple[ValidationIssue, ...]:
    issues = [
        *_validate_manifests(catalog),
        *_validate_skills(catalog),
        *_validate_generated_agents(catalog),
    ]
    return tuple(sorted(issues, key=lambda issue: (issue.path, issue.code)))
