import tomllib
from pathlib import Path

import pytest
import yaml

from waterology.runtime.agents import AgentDefinition
from waterology.runtime.assets import AssetCatalog
from waterology.runtime.render import (
    GeneratedAssetsStaleError,
    render_agents,
    render_assets,
    render_claude,
    render_claude_command,
    render_codex,
    render_opencode,
    render_pi,
)
from waterology.runtime.skills import ClaudeCommand, SkillDefinition


def sample_agent(tmp_path: Path) -> AgentDefinition:
    return AgentDefinition(
        name="researcher",
        description="Gather primary evidence.",
        capabilities=("read", "write", "shell", "web"),
        body="Gather evidence and cite it.\n",
        source_path=tmp_path / "researcher.md",
    )


def sample_skill(tmp_path: Path) -> SkillDefinition:
    return SkillDefinition(
        name="session-log",
        description=(
            "Write a durable session log. Use when the user asks to log progress, "
            "save session notes, or write up what was done."
        ),
        body=(
            "<!-- Adapted from example/upstream, prompts/log.md at commit "
            "0123456789abcdef (MIT). -->\n\n"
            "Write the log to `notes/<date>-session.md`.\n"
        ),
        source_path=tmp_path / "skills/session-log/SKILL.md",
        claude_command=ClaudeCommand(name="log", argument_hint="(none)"),
    )


def split_markdown_frontmatter(text: str) -> tuple[dict[str, object], str]:
    _, frontmatter, body = text.split("---", 2)
    return yaml.safe_load(frontmatter), body


def test_claude_renderer_maps_capabilities(tmp_path: Path) -> None:
    metadata, body = split_markdown_frontmatter(render_claude(sample_agent(tmp_path)))

    assert metadata["name"] == "researcher"
    assert metadata["tools"] == (
        "Read, Grep, Glob, Write, Edit, Bash, WebSearch, WebFetch, "
        "mcp__kagi__kagi_search_fetch, mcp__kagi__kagi_extract"
    )
    assert "Generated from agent-definitions/researcher.md" in body


def test_codex_renderer_is_valid_toml(tmp_path: Path) -> None:
    rendered = render_codex(sample_agent(tmp_path))

    data = tomllib.loads(rendered)

    assert data == {
        "name": "researcher",
        "description": "Gather primary evidence.",
        "developer_instructions": "Gather evidence and cite it.\n",
    }


def test_opencode_renderer_uses_v2_subagent_format(tmp_path: Path) -> None:
    metadata, body = split_markdown_frontmatter(render_opencode(sample_agent(tmp_path)))

    assert metadata == {"description": "Gather primary evidence.", "mode": "subagent"}
    assert "Gather evidence and cite it." in body


def test_pi_renderer_uses_namespaced_subagent_format(tmp_path: Path) -> None:
    metadata, body = split_markdown_frontmatter(render_pi(sample_agent(tmp_path)))

    assert metadata == {
        "name": "researcher",
        "package": "waterology",
        "description": "Gather primary evidence.",
        "advertise": True,
        "tools": (
            "read, grep, find, ls, write, edit, bash, web_search, fetch_content, "
            "get_search_content, source_check"
        ),
        "systemPromptMode": "replace",
        "inheritProjectContext": True,
        "inheritGlobalContext": False,
        "inheritSkills": True,
    }
    assert "Generated from agent-definitions/researcher.md" in body
    assert "Gather evidence and cite it." in body


def test_claude_command_renderer_delegates_to_canonical_skill(tmp_path: Path) -> None:
    metadata, body = split_markdown_frontmatter(render_claude_command(sample_skill(tmp_path)))

    assert metadata == {
        "description": "Alias for the `session-log` skill: Write a durable session log.",
        "argument-hint": "(none)",
    }
    assert "Generated from skills/session-log/SKILL.md" in body
    assert "example/upstream" not in body
    assert "prompts/log.md" not in body
    assert "0123456789abcdef" not in body
    assert "MIT" not in body
    assert "`session-log` skill" in body
    assert "$ARGUMENTS" in body
    assert "Write the log to" not in body


def test_claude_command_description_drops_the_skill_trigger_clause(tmp_path: Path) -> None:
    skill = sample_skill(tmp_path)
    metadata, _ = split_markdown_frontmatter(render_claude_command(skill))
    description = metadata["description"]

    assert "Use when the user asks" not in description
    assert description != skill.description
    assert skill.name in description


def test_claude_command_description_keeps_a_trigger_free_summary(tmp_path: Path) -> None:
    skill = SkillDefinition(
        name="watch",
        description="Create a research watch baseline.",
        body="Record the baseline.\n",
        source_path=tmp_path / "skills/watch/SKILL.md",
        claude_command=ClaudeCommand(name="watch", argument_hint="<topic>"),
    )

    metadata, _ = split_markdown_frontmatter(render_claude_command(skill))

    assert metadata["description"] == (
        "Alias for the `watch` skill: Create a research watch baseline."
    )


def test_claude_command_body_requires_loading_the_skill(tmp_path: Path) -> None:
    _, body = split_markdown_frontmatter(render_claude_command(sample_skill(tmp_path)))

    assert "Skill tool" in body
    assert "routing shim" in body


def test_render_agents_writes_checks_and_detects_stale_outputs(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    agent_definitions = source_root / "agent-definitions"
    agent_definitions.mkdir(parents=True)
    (agent_definitions / "researcher.md").write_text(
        "---\n"
        "name: researcher\n"
        "description: Gather evidence.\n"
        "capabilities: [read]\n"
        "---\n\n"
        "Gather evidence.\n",
        encoding="utf-8",
    )
    output_root = tmp_path / "output"
    expected_paths = {
        output_root / "agents/researcher.md",
        output_root / ".codex/agents/researcher.toml",
        output_root / ".opencode/agents/researcher.md",
        output_root / "pi-agents/researcher.md",
    }

    changed = render_agents(AssetCatalog.discover(source_root), output_root)

    assert set(changed) == expected_paths
    assert all(path.is_file() for path in expected_paths)
    assert render_agents(AssetCatalog.discover(source_root), output_root) == ()

    stale_path = output_root / ".codex/agents/researcher.toml"
    stale_path.write_text("stale\n", encoding="utf-8")

    with pytest.raises(GeneratedAssetsStaleError) as error:
        render_agents(AssetCatalog.discover(source_root), output_root, check=True)

    assert error.value.paths == (stale_path,)
    assert stale_path.read_text(encoding="utf-8") == "stale\n"


def test_render_assets_includes_skill_backed_claude_commands(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    skill_directory = source_root / "skills/session-log"
    skill_directory.mkdir(parents=True)
    (skill_directory / "SKILL.md").write_text(
        """---
name: session-log
description: Write a durable session log.
metadata:
  claude-command:
    name: log
    argument-hint: (none)
---

Write the log to `notes/<date>-session.md`.
""",
        encoding="utf-8",
    )
    agent_definitions = source_root / "agent-definitions"
    agent_definitions.mkdir()
    (agent_definitions / "researcher.md").write_text(
        "---\n"
        "name: researcher\n"
        "description: Gather evidence.\n"
        "capabilities: [read]\n"
        "---\n\n"
        "Gather evidence.\n",
        encoding="utf-8",
    )
    output_root = tmp_path / "output"

    changed = render_assets(AssetCatalog.discover(source_root), output_root)

    command_path = output_root / "commands/log.md"
    assert command_path in changed
    assert command_path.is_file()
    assert "`session-log` skill" in command_path.read_text(encoding="utf-8")
    assert render_assets(AssetCatalog.discover(source_root), output_root) == ()
