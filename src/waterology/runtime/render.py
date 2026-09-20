import json
import re
from collections.abc import Callable
from pathlib import Path

import yaml

from waterology.runtime.agents import AgentDefinition, load_agents
from waterology.runtime.assets import AssetCatalog
from waterology.runtime.skills import SkillDefinition, load_skills

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


TRIGGER_CLAUSE = re.compile(r"(?<=\.)\s+Use\b")


# A shim and its skill are both offered to the model as callable units. Copying the
# skill description verbatim gives two entries with the same trigger text, so routing
# between them is arbitrary and the process varies by entry path. Dropping the
# "Use when ..." clause leaves the shim reachable by name while the skill keeps sole
# ownership of intent matching.
def command_description(skill: SkillDefinition) -> str:
    summary = " ".join(skill.description.split())
    trigger = TRIGGER_CLAUSE.search(summary)
    if trigger is not None:
        summary = summary[: trigger.start()]
    return f"Alias for the `{skill.name}` skill: {summary}"


def render_claude_command(skill: SkillDefinition) -> str:
    command = skill.claude_command
    if command is None:
        raise ValueError(f"Skill has no Claude command metadata: {skill.name}")
    frontmatter = yaml.safe_dump(
        {"description": command_description(skill), "argument-hint": command.argument_hint},
        sort_keys=False,
    ).rstrip()
    marker = f"<!-- Generated from skills/{skill.name}/SKILL.md. Do not edit. -->"
    body = (
        f"Load the `{skill.name}` skill with the Skill tool before any other work, then\n"
        f"follow it exactly. This file is a routing shim and holds no process of its own.\n"
        f"\nArguments: $ARGUMENTS\n"
    )
    return f"---\n{frontmatter}\n---\n\n{marker}\n\n{body}"


Renderer = Callable[[AgentDefinition], str]
DESTINATIONS: dict[str, tuple[str, str, Renderer]] = {
    "claude": ("agents", ".md", render_claude),
    "codex": (".codex/agents", ".toml", render_codex),
    "opencode": (".opencode/agents", ".md", render_opencode),
}


class GeneratedAssetsStaleError(RuntimeError):
    def __init__(self, paths: tuple[Path, ...]) -> None:
        self.paths = paths
        super().__init__("Generated files are stale")


def _render_expected(expected: dict[Path, str], check: bool) -> tuple[Path, ...]:
    changed: list[Path] = []
    for destination, content in expected.items():
        current = destination.read_text(encoding="utf-8") if destination.exists() else None
        if current == content:
            continue
        changed.append(destination)
        if not check:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(content, encoding="utf-8")
    paths = tuple(sorted(changed))
    if check and paths:
        raise GeneratedAssetsStaleError(paths)
    return paths


def _expected_agents(catalog: AssetCatalog, output_root: Path) -> dict[Path, str]:
    expected: dict[Path, str] = {}
    for agent in load_agents(catalog):
        for directory, suffix, renderer in DESTINATIONS.values():
            expected[output_root / directory / f"{agent.name}{suffix}"] = renderer(agent)
    return expected


def _expected_commands(catalog: AssetCatalog, output_root: Path) -> dict[Path, str]:
    return {
        output_root / "commands" / f"{skill.claude_command.name}.md": render_claude_command(skill)
        for skill in load_skills(catalog)
        if skill.claude_command is not None
    }


def render_agents(
    catalog: AssetCatalog,
    output_root: Path,
    check: bool = False,
) -> tuple[Path, ...]:
    return _render_expected(_expected_agents(catalog, output_root), check)


def render_commands(
    catalog: AssetCatalog,
    output_root: Path,
    check: bool = False,
) -> tuple[Path, ...]:
    return _render_expected(_expected_commands(catalog, output_root), check)


def render_assets(
    catalog: AssetCatalog,
    output_root: Path,
    check: bool = False,
) -> tuple[Path, ...]:
    expected = {
        **_expected_agents(catalog, output_root),
        **_expected_commands(catalog, output_root),
    }
    return _render_expected(expected, check)
