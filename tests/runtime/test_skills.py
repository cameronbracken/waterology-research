import json
from pathlib import Path

import yaml

from waterology.runtime.assets import AssetCatalog
from waterology.runtime.skills import load_skills, parse_skill


def test_parse_skill_reads_optional_claude_command_metadata(tmp_path: Path) -> None:
    path = tmp_path / "session-log" / "SKILL.md"
    path.parent.mkdir()
    path.write_text(
        """---
name: session-log
description: Write a durable session log.
metadata:
  claude-command:
    name: log
    argument-hint: (none)
---

Write a session log.
""",
        encoding="utf-8",
    )

    skill = parse_skill(path)

    assert skill.name == "session-log"
    assert skill.description == "Write a durable session log."
    assert skill.claude_command is not None
    assert skill.claude_command.name == "log"
    assert skill.claude_command.argument_hint == "(none)"


def test_load_skills_returns_only_command_backed_skills(tmp_path: Path) -> None:
    for name, command in (("session-log", "log"), ("writing-style", None)):
        path = tmp_path / "skills" / name / "SKILL.md"
        path.parent.mkdir(parents=True)
        command_metadata = (
            f"""metadata:
  claude-command:
    name: {command}
    argument-hint: (none)
"""
            if command
            else ""
        )
        path.write_text(
            f"---\nname: {name}\ndescription: Test {name}.\n{command_metadata}---\n\nBody.\n",
            encoding="utf-8",
        )

    skills = load_skills(AssetCatalog.discover(tmp_path))

    assert [skill.name for skill in skills] == ["session-log", "writing-style"]
    assert [skill.name for skill in skills if skill.claude_command] == ["session-log"]


def test_retired_paper_workflow_is_not_packaged() -> None:
    catalog = AssetCatalog.discover()
    skills = load_skills(catalog)

    assert "paper-writing" not in {skill.name for skill in skills}
    assert "draft" not in {skill.claude_command.name for skill in skills if skill.claude_command}
    assert not (catalog.root / "commands/draft.md").exists()


def test_primary_entrypoints_are_exposed_for_implicit_invocation() -> None:
    catalog = AssetCatalog.discover()
    manifest = json.loads(catalog.path(".codex-plugin/plugin.json").read_text())
    assert (catalog.root / manifest["skills"]).resolve() == catalog.path("skills")
    skills = {skill.name: skill for skill in load_skills(catalog)}
    for name in (
        "project-conventions",
        "r-code-style",
        "data-visualization",
        "diagrams",
        "reports",
        "interactive-graphics",
        "interactive-reports",
        "markdown-notes",
        "documentation",
        "writing-style",
        "setup-environment",
        "publish-blog-post",
        "figure-style",
        "figure-composer",
    ):
        source = skills[name].source_path
        policy = yaml.safe_load((source.parent / "agents/openai.yaml").read_text())
        assert policy["policy"]["allow_implicit_invocation"] is True, name
        metadata = yaml.safe_load(source.read_text().split("---", 2)[1])
        assert not metadata.get("disable-model-invocation", False), name
