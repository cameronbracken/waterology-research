import re
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

from waterology.runtime.assets import AssetCatalog

Capability = Literal["read", "write", "shell", "web"]
FRONTMATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n(.*)\Z", re.DOTALL)


class AgentDefinition(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    description: str = Field(min_length=1, max_length=1024)
    capabilities: tuple[Capability, ...]
    body: str = Field(min_length=1)
    source_path: Path


def parse_agent(path: Path) -> AgentDefinition:
    match = FRONTMATTER.match(path.read_text(encoding="utf-8"))
    if match is None:
        raise ValueError(f"Agent lacks YAML frontmatter: {path}")
    metadata = yaml.safe_load(match.group(1))
    return AgentDefinition.model_validate(
        {**metadata, "body": match.group(2).lstrip("\n"), "source_path": path}
    )


def load_agents(catalog: AssetCatalog) -> tuple[AgentDefinition, ...]:
    source_dir = catalog.path("agent-definitions")
    return tuple(parse_agent(path) for path in sorted(source_dir.glob("*.md")))
