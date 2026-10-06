import json
import os
import re
import stat
from collections.abc import Callable
from pathlib import Path

import yaml

from waterology.runtime.agents import AgentDefinition, load_agents
from waterology.runtime.assets import (
    PI_PROMPT_DIRECTORY,
    PI_SKILL_DIRECTORY,
    PI_SKILL_PREFIX,
    AssetCatalog,
)
from waterology.runtime.skills import FRONTMATTER, SkillDefinition, load_skills

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
PI_TOOLS = {
    "read": ("read", "grep", "find", "ls"),
    "write": ("write", "edit"),
    "shell": ("bash",),
    "web": ("web_search", "fetch_content", "get_search_content", "source_check"),
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


def render_pi(agent: AgentDefinition) -> str:
    tools = tuple(tool for capability in agent.capabilities for tool in PI_TOOLS[capability])
    frontmatter = yaml.safe_dump(
        {
            "name": agent.name,
            "package": "waterology",
            "description": agent.description,
            "advertise": True,
            "tools": ", ".join(tools),
            "systemPromptMode": "replace",
            "inheritProjectContext": True,
            "inheritGlobalContext": False,
            "inheritSkills": True,
        },
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
def command_description(skill: SkillDefinition, skill_name: str | None = None) -> str:
    summary = " ".join(skill.description.split())
    trigger = TRIGGER_CLAUSE.search(summary)
    if trigger is not None:
        summary = summary[: trigger.start()]
    return f"Alias for the `{skill_name or skill.name}` skill: {summary}"


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


# Pi has no package namespaces, and skill names that collide with another package
# (Feynman ships several of the same names) keep only the first one loaded. Pi gets
# prefixed copies, and exact `skill-name` references in the text follow the rename.
SKILL_REFERENCE = re.compile(r"`([a-z0-9]+(?:-[a-z0-9]+)*)`")


def pi_name(name: str) -> str:
    return f"{PI_SKILL_PREFIX}{name}"


def _pi_references(text: str, names: frozenset[str]) -> str:
    return SKILL_REFERENCE.sub(
        lambda match: f"`{pi_name(match[1])}`" if match[1] in names else match[0], text
    )


def render_pi_skill(skill: SkillDefinition, names: frozenset[str]) -> str:
    match = FRONTMATTER.match(skill.source_path.read_text(encoding="utf-8"))
    if match is None:
        raise ValueError(f"Skill lacks YAML frontmatter: {skill.source_path}")
    frontmatter = re.sub(
        rf"^name:[ \t]*{re.escape(skill.name)}[ \t]*$",
        f"name: {pi_name(skill.name)}",
        match.group(1),
        count=1,
        flags=re.MULTILINE,
    )
    marker = f"<!-- Generated from skills/{skill.name}/SKILL.md. Do not edit. -->"
    body = _pi_references(match.group(2).lstrip("\n"), names)
    return f"---\n{_pi_references(frontmatter, names)}\n---\n\n{marker}\n\n{body}"


def render_pi_prompt(skill: SkillDefinition) -> str:
    command = skill.claude_command
    if command is None:
        raise ValueError(f"Skill has no command metadata: {skill.name}")
    name = pi_name(skill.name)
    frontmatter = yaml.safe_dump(
        {"description": command_description(skill, name), "argument-hint": command.argument_hint},
        sort_keys=False,
    ).rstrip()
    marker = f"<!-- Generated from skills/{skill.name}/SKILL.md. Do not edit. -->"
    body = (
        f"Read the `{name}` skill before any other work, then follow it exactly.\n"
        f"This prompt is a routing shim and holds no process of its own.\n"
        f"\nArguments: $ARGUMENTS\n"
    )
    return f"---\n{frontmatter}\n---\n\n{marker}\n\n{body}"


def _skill_support_files(directory: Path) -> tuple[Path, ...]:
    return tuple(
        sorted(
            path
            for path in directory.rglob("*")
            if path.is_file()
            and path.name != "SKILL.md"
            and not any(
                part.startswith(".") or part == "__pycache__"
                for part in path.relative_to(directory).parts
            )
        )
    )


def _is_executable(path: Path) -> bool:
    return bool(path.stat().st_mode & stat.S_IXUSR)


Renderer = Callable[[AgentDefinition], str]
DESTINATIONS: dict[str, tuple[str, str, Renderer]] = {
    "claude": ("agents", ".md", render_claude),
    "codex": (".codex/agents", ".toml", render_codex),
    "opencode": (".opencode/agents", ".md", render_opencode),
    "pi": ("pi-agents", ".md", render_pi),
}


class GeneratedAssetsStaleError(RuntimeError):
    def __init__(self, paths: tuple[Path, ...]) -> None:
        self.paths = paths
        super().__init__("Generated files are stale")


def _render_expected(
    expected: dict[Path, str],
    check: bool,
    executable: frozenset[Path] = frozenset(),
    owned_roots: tuple[Path, ...] = (),
) -> tuple[Path, ...]:
    """Write expected files. Files under an owned root that are not expected are removed."""
    changed: list[Path] = []
    for destination, content in expected.items():
        current = destination.read_text(encoding="utf-8") if destination.exists() else None
        wrong_mode = (
            os.name != "nt"
            and current is not None
            and _is_executable(destination) != (destination in executable)
        )
        if current == content and not wrong_mode:
            continue
        changed.append(destination)
        if not check:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(content, encoding="utf-8")
            if os.name != "nt":
                mode = destination.stat().st_mode
                bits = stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
                destination.chmod(mode | bits if destination in executable else mode & ~bits)
    for root in owned_roots:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*"), reverse=True):
            if path.is_dir():
                if not check and not any(path.iterdir()):
                    path.rmdir()
            elif path not in expected:
                changed.append(path)
                if not check:
                    path.unlink()
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


def _expected_pi(
    catalog: AssetCatalog, output_root: Path
) -> tuple[dict[Path, str], frozenset[Path]]:
    skills = load_skills(catalog)
    names = frozenset(skill.name for skill in skills)
    expected: dict[Path, str] = {}
    executable: set[Path] = set()
    for skill in skills:
        source = skill.source_path.parent
        destination = output_root / PI_SKILL_DIRECTORY / pi_name(skill.name)
        expected[destination / "SKILL.md"] = render_pi_skill(skill, names)
        for path in _skill_support_files(source):
            target = destination / path.relative_to(source)
            text = path.read_text(encoding="utf-8")
            expected[target] = _pi_references(text, names) if path.suffix == ".md" else text
            if _is_executable(path):
                executable.add(target)
        if skill.claude_command is not None:
            prompt = output_root / PI_PROMPT_DIRECTORY / f"{pi_name(skill.claude_command.name)}.md"
            expected[prompt] = render_pi_prompt(skill)
    return expected, frozenset(executable)


def _pi_roots(output_root: Path) -> tuple[Path, ...]:
    return (output_root / PI_SKILL_DIRECTORY, output_root / PI_PROMPT_DIRECTORY)


def render_pi_assets(
    catalog: AssetCatalog,
    output_root: Path,
    check: bool = False,
) -> tuple[Path, ...]:
    expected, executable = _expected_pi(catalog, output_root)
    return _render_expected(expected, check, executable, _pi_roots(output_root))


def render_assets(
    catalog: AssetCatalog,
    output_root: Path,
    check: bool = False,
) -> tuple[Path, ...]:
    pi_expected, executable = _expected_pi(catalog, output_root)
    expected = {
        **_expected_agents(catalog, output_root),
        **_expected_commands(catalog, output_root),
        **pi_expected,
    }
    return _render_expected(expected, check, executable, _pi_roots(output_root))
