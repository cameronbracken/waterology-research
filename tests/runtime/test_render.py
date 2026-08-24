import tomllib
from pathlib import Path

import yaml

from waterology.runtime.agents import AgentDefinition
from waterology.runtime.render import render_claude, render_codex, render_opencode


def sample_agent(tmp_path: Path) -> AgentDefinition:
    return AgentDefinition(
        name="researcher",
        description="Gather primary evidence.",
        capabilities=("read", "write", "shell", "web"),
        body="Gather evidence and cite it.\n",
        source_path=tmp_path / "researcher.md",
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
