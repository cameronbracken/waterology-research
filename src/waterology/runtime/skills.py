import re
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

from waterology.runtime.assets import AssetCatalog

FRONTMATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n(.*)\Z", re.DOTALL)


class ClaudeCommand(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    name: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    argument_hint: str = Field(alias="argument-hint", min_length=1, max_length=1024)


class SkillDefinition(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    description: str = Field(min_length=1, max_length=1024)
    body: str = Field(min_length=1)
    source_path: Path
    claude_command: ClaudeCommand | None = None


def parse_skill(path: Path) -> SkillDefinition:
    match = FRONTMATTER.match(path.read_text(encoding="utf-8"))
    if match is None:
        raise ValueError(f"Skill lacks YAML frontmatter: {path}")
    metadata = yaml.safe_load(match.group(1))
    if not isinstance(metadata, dict):
        raise ValueError(f"Skill frontmatter must be a mapping: {path}")  # noqa: TRY004

    optional_metadata = metadata.get("metadata", {})
    if optional_metadata is None:
        optional_metadata = {}
    if not isinstance(optional_metadata, dict):
        raise ValueError(f"Skill metadata must be a mapping: {path}")  # noqa: TRY004

    return SkillDefinition.model_validate(
        {
            "name": metadata.get("name"),
            "description": str(metadata.get("description", "")).strip(),
            "body": match.group(2).lstrip("\n"),
            "source_path": path,
            "claude_command": optional_metadata.get("claude-command"),
        }
    )


def load_skills(catalog: AssetCatalog) -> tuple[SkillDefinition, ...]:
    return tuple(parse_skill(directory / "SKILL.md") for directory in catalog.skill_directories())
