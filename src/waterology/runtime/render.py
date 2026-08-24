import json
from collections.abc import Callable
from pathlib import Path

import yaml

from waterology.runtime.agents import AgentDefinition, load_agents
from waterology.runtime.assets import AssetCatalog

CLAUDE_TOOLS = {
    "read": ("Read", "Grep", "Glob"),
    "write": ("Write", "Edit"),
    "shell": ("Bash",),
    "web": (
        "WebSearch",
        "WebFetch",
        "mcp__kagi__kagi_search_fetch",
        "mcp__kagi__kagi_extract",
    ),
}


def render_claude(agent: AgentDefinition) -> str:
    tools = tuple(tool for capability in agent.capabilities for tool in CLAUDE_TOOLS[capability])
    frontmatter = yaml.safe_dump(
        {"name": agent.name, "description": agent.description, "tools": ", ".join(tools)},
        sort_keys=False,
    ).rstrip()
    marker = f"<!-- Generated from agent-definitions/{agent.name}.md. Do not edit. -->"
    return f"---\n{frontmatter}\n---\n\n{marker}\n\n{agent.body}"


def render_codex(agent: AgentDefinition) -> str:
    return (
        f"# Generated from agent-definitions/{agent.name}.md. Do not edit.\n"
        f"name = {json.dumps(agent.name)}\n"
        f"description = {json.dumps(agent.description)}\n"
        f"developer_instructions = {json.dumps(agent.body)}\n"
    )


def render_opencode(agent: AgentDefinition) -> str:
    frontmatter = yaml.safe_dump(
        {"description": agent.description, "mode": "subagent"},
        sort_keys=False,
    ).rstrip()
    marker = f"<!-- Generated from agent-definitions/{agent.name}.md. Do not edit. -->"
    return f"---\n{frontmatter}\n---\n\n{marker}\n\n{agent.body}"


Renderer = Callable[[AgentDefinition], str]
DESTINATIONS: dict[str, tuple[str, str, Renderer]] = {
    "claude": ("agents", ".md", render_claude),
    "codex": (".codex/agents", ".toml", render_codex),
    "opencode": (".opencode/agents", ".md", render_opencode),
}


class GeneratedAssetsStaleError(RuntimeError):
    def __init__(self, paths: tuple[Path, ...]) -> None:
        self.paths = paths
        super().__init__("Generated agent files are stale")


def render_agents(
    catalog: AssetCatalog,
    output_root: Path,
    check: bool = False,
) -> tuple[Path, ...]:
    changed: list[Path] = []
    for agent in load_agents(catalog):
        for directory, suffix, renderer in DESTINATIONS.values():
            destination = output_root / directory / f"{agent.name}{suffix}"
            expected = renderer(agent)
            current = destination.read_text(encoding="utf-8") if destination.exists() else None
            if current == expected:
                continue
            changed.append(destination)
            if not check:
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(expected, encoding="utf-8")
    paths = tuple(sorted(changed))
    if check and paths:
        raise GeneratedAssetsStaleError(paths)
    return paths
