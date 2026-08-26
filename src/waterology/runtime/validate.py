import json
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

import yaml
from pydantic import ValidationError

from waterology import __version__
from waterology.runtime.agents import parse_agent
from waterology.runtime.assets import AssetCatalog, AssetNotFoundError
from waterology.runtime.render import GeneratedAssetsStaleError, render_agents, render_commands
from waterology.runtime.skills import parse_skill

SKILL_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+[^)]*)?\)")
MANIFESTS = (".claude-plugin/plugin.json", ".codex-plugin/plugin.json")
GENERATED_AGENT_DIRECTORIES = (".codex/agents", "agents", ".opencode/agents")
GENERATED_AGENT_SUFFIXES = {
    ".codex/agents": ".toml",
    "agents": ".md",
    ".opencode/agents": ".md",
}
REQUIRED_AGENT_NAMES = (
    "r-reviewer",
    "reproducibility-auditor",
    "researcher",
    "reviewer",
    "sim-reviewer",
    "verifier",
    "writer",
)


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
            issues.append(
                ValidationIssue(relative, "missing-asset", "required manifest is missing")
            )
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            issues.append(ValidationIssue(relative, "invalid-json", str(error)))
            continue
        if not isinstance(data, dict):
            issues.append(
                ValidationIssue(relative, "invalid-manifest", "manifest must be a JSON object")
            )
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
        for reference_file in directory.rglob("*.md"):
            reference_relative = reference_file.relative_to(catalog.root).as_posix()
            for match in MARKDOWN_LINK.finditer(reference_file.read_text(encoding="utf-8")):
                reference = match.group(1).strip("<>")
                reference_path = reference.split("#", 1)[0]
                if (
                    not reference_path
                    or reference_path.startswith(("/", "{{", "${"))
                    or re.match(r"^[a-z][a-z0-9+.-]*:", reference_path, re.IGNORECASE)
                ):
                    continue
                if not (reference_file.parent / reference_path).exists():
                    issues.append(
                        ValidationIssue(
                            reference_relative,
                            "missing-skill-reference",
                            reference_path,
                        )
                    )
    return issues


def _validate_skill_commands(catalog: AssetCatalog) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    command_owners: dict[str, str] = {}
    expected_commands: set[str] = set()
    definitions_valid = True

    for directory in catalog.skill_directories():
        path = directory / "SKILL.md"
        relative = path.relative_to(catalog.root).as_posix()
        try:
            skill = parse_skill(path)
        except (ValueError, ValidationError, yaml.YAMLError) as error:
            definitions_valid = False
            issues.append(ValidationIssue(relative, "invalid-skill-definition", str(error)))
            continue
        command = skill.claude_command
        if command is None:
            continue
        if command.name in command_owners:
            definitions_valid = False
            issues.append(ValidationIssue(relative, "duplicate-claude-command", command.name))
            continue
        command_owners[command.name] = relative
        expected_commands.add(f"{command.name}.md")

    try:
        command_directory = catalog.path("commands")
    except AssetNotFoundError:
        if expected_commands:
            issues.append(
                ValidationIssue("commands", "missing-asset", "generated commands are missing")
            )
        return issues
    if not command_directory.is_dir():
        issues.append(
            ValidationIssue("commands", "invalid-asset-type", "commands must be a directory")
        )
        return issues

    entries = {path.name: path for path in command_directory.iterdir()}
    command_assets_valid = True
    for filename in sorted(expected_commands - entries.keys()):
        command_assets_valid = False
        issues.append(
            ValidationIssue(
                f"commands/{filename}", "missing-asset", "generated command is missing"
            )
        )
    for filename, path in sorted(entries.items()):
        if filename in expected_commands and not path.is_file():
            command_assets_valid = False
            issues.append(
                ValidationIssue(
                    f"commands/{filename}",
                    "invalid-asset-type",
                    "generated command must be a file",
                )
            )
            continue
        if not path.is_file() or path.suffix != ".md":
            continue
        text = path.read_text(encoding="utf-8")
        if "<!-- Generated from skills/" in text and filename not in expected_commands:
            issues.append(
                ValidationIssue(
                    f"commands/{filename}",
                    "orphaned-generated-command",
                    "generated command has no canonical skill metadata",
                )
            )

    if definitions_valid and command_assets_valid:
        try:
            render_commands(catalog, catalog.root, check=True)
        except GeneratedAssetsStaleError as error:
            for path in error.paths:
                issues.append(
                    ValidationIssue(
                        path.relative_to(catalog.root).as_posix(),
                        "stale-generated-command",
                        "rendered content differs",
                    )
                )
    return issues


def _validate_canonical_agents(
    catalog: AssetCatalog,
) -> tuple[list[ValidationIssue], set[str], bool]:
    issues: list[ValidationIssue] = []
    present_names: set[str] = set()
    relative_directory = "agent-definitions"
    try:
        directory = catalog.path(relative_directory)
    except AssetNotFoundError:
        issues.append(
            ValidationIssue(
                relative_directory,
                "missing-asset",
                "required canonical agent directory is missing",
            )
        )
        return issues, present_names, False
    if not directory.is_dir():
        issues.append(
            ValidationIssue(
                relative_directory,
                "invalid-asset-type",
                "canonical agent asset must be a directory",
            )
        )
        return issues, present_names, False

    entries = {path.name: path for path in directory.iterdir()}
    required_files = {f"{name}.md" for name in REQUIRED_AGENT_NAMES}
    for name in REQUIRED_AGENT_NAMES:
        filename = f"{name}.md"
        relative = f"{relative_directory}/{filename}"
        path = entries.get(filename)
        if path is None:
            issues.append(
                ValidationIssue(
                    relative,
                    "missing-asset",
                    "required canonical agent definition is missing",
                )
            )
            continue
        if path.is_file():
            present_names.add(name)

    for filename, path in sorted(entries.items()):
        relative = f"{relative_directory}/{filename}"
        if filename not in required_files:
            issues.append(
                ValidationIssue(
                    relative,
                    "unexpected-asset",
                    "canonical agent is not part of the required inventory",
                )
            )
        if path.suffix != ".md":
            continue
        if not path.is_file():
            issues.append(
                ValidationIssue(
                    relative,
                    "invalid-asset-type",
                    "canonical agent definition must be a file",
                )
            )
            continue
        try:
            agent = parse_agent(path)
        except ValidationError as error:
            issues.append(ValidationIssue(relative, "invalid-agent-definition", str(error)))
            continue
        except (ValueError, yaml.YAMLError) as error:
            issues.append(ValidationIssue(relative, "invalid-frontmatter", str(error)))
            continue
        if agent.name != path.stem:
            issues.append(
                ValidationIssue(
                    relative,
                    "invalid-name",
                    f"metadata name {agent.name!r} does not match filename {filename!r}",
                )
            )

    return issues, present_names, not issues


def _validate_generated_agents(
    catalog: AssetCatalog,
    canonical_names: set[str],
    canonical_valid: bool,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    directories: dict[str, Path] = {}
    unavailable: set[str] = set()
    missing_paths: set[str] = set()
    invalid_expected_path = False
    for relative in GENERATED_AGENT_DIRECTORIES:
        try:
            path = catalog.path(relative)
        except AssetNotFoundError:
            issues.append(
                ValidationIssue(
                    relative, "missing-asset", "required generated-agent directory is missing"
                )
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

        suffix = GENERATED_AGENT_SUFFIXES[relative]
        entries = {entry.name: entry for entry in path.iterdir()}
        required_files = {f"{name}{suffix}" for name in REQUIRED_AGENT_NAMES}
        for filename in sorted(required_files - entries.keys()):
            missing = f"{relative}/{filename}"
            missing_paths.add(missing)
            issues.append(
                ValidationIssue(missing, "missing-asset", "required generated agent is missing")
            )
        for filename in sorted(entries.keys() - required_files):
            issues.append(
                ValidationIssue(
                    f"{relative}/{filename}",
                    "orphaned-generated-agent",
                    "generated agent is not part of the required inventory",
                )
            )
        for name in REQUIRED_AGENT_NAMES:
            filename = f"{name}{suffix}"
            generated = entries.get(filename)
            if generated is None:
                continue
            generated_relative = f"{relative}/{filename}"
            if not generated.is_file():
                invalid_expected_path = True
                issues.append(
                    ValidationIssue(
                        generated_relative,
                        "invalid-asset-type",
                        "generated agent must be a file",
                    )
                )
                continue
            if name not in canonical_names:
                issues.append(
                    ValidationIssue(
                        generated_relative,
                        "orphaned-generated-agent",
                        "generated agent has no canonical definition",
                    )
                )

    if canonical_valid and not invalid_expected_path:
        try:
            render_agents(catalog, catalog.root, check=True)
        except GeneratedAssetsStaleError as error:
            for path in error.paths:
                relative = path.relative_to(catalog.root).as_posix()
                if relative in missing_paths:
                    continue
                if any(relative.startswith(f"{directory}/") for directory in unavailable):
                    continue
                issues.append(
                    ValidationIssue(
                        relative,
                        "stale-generated-agent",
                        "rendered content differs",
                    )
                )
    codex_directory = directories.get(".codex/agents")
    if codex_directory is not None:
        for path in sorted(codex_directory.glob("*.toml")):
            if not path.is_file():
                continue
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
            if not path.is_file():
                continue
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
    canonical_issues, canonical_names, canonical_valid = _validate_canonical_agents(catalog)
    issues = [
        *_validate_manifests(catalog),
        *_validate_skills(catalog),
        *_validate_skill_commands(catalog),
        *canonical_issues,
        *_validate_generated_agents(catalog, canonical_names, canonical_valid),
    ]
    return tuple(sorted(issues, key=lambda issue: (issue.path, issue.code)))
