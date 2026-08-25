from pathlib import Path

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
