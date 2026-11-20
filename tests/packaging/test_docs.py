import json
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+[^)]*)?\)")


def test_distribution_name_preserves_waterology_cli_and_slim_deps() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    pixi = tomllib.loads((ROOT / "pixi.toml").read_text())

    assert project["project"]["name"] == "waterology-research"
    assert project["project"]["version"] == "1.0.0"
    assert project["project"]["scripts"] == {
        "waterology": "waterology.cli:app",
        "waterology-mcp": "waterology.mcp.server:main",
        "wgy": "waterology.cli:app",
    }
    assert project["project"]["optional-dependencies"]["mcp"] == ["mcp>=2,<3"]
    assert project["project"]["optional-dependencies"]["zotero"] == ["pyzotero>=1.6,<2"]
    assert "dashboard" not in project["project"]["optional-dependencies"]
    assert "rocrate" not in project["project"]["optional-dependencies"]
    assert "waterology-research" in pixi["pypi-dependencies"]

    repository = "https://codeberg.org/waterology/waterology-research"
    for path in (".claude-plugin/plugin.json", ".codex-plugin/plugin.json"):
        manifest = json.loads((ROOT / path).read_text())
        assert manifest["name"] == "waterology"
        assert manifest["version"] == "1.0.0"
        assert manifest["homepage"] == repository
        assert manifest["repository"] == repository


def test_readme_and_docs_links_resolve() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for command in (
        "pixi run waterology install antigravity",
        "pixi run waterology install claude",
        "pixi run waterology install codex",
        "pixi run waterology install opencode",
        "pixi run waterology install pi",
        "pixi run waterology install all --dry-run",
        "pixi run waterology doctor",
    ):
        assert command in readme
    assert "Research workflows are runtime neutral." in readme

    for doc in [ROOT / "README.md", *sorted((ROOT / "docs").rglob("*.md"))]:
        for match in MARKDOWN_LINK.finditer(doc.read_text(encoding="utf-8")):
            target = match.group(1).strip("<>").split("#", 1)[0]
            if not target or re.match(r"^[a-z][a-z0-9+.-]*:", target, re.IGNORECASE):
                continue
            assert (doc.parent / target).exists(), f"Broken link in {doc}: {target}"


def test_claude_guidance_defers_to_agents() -> None:
    claude = (ROOT / "CLAUDE.md").read_text()
    assert len(claude.splitlines()) <= 20
    assert "AGENTS.md" in claude


def test_canonical_guidance_has_required_commands() -> None:
    agents = (ROOT / "AGENTS.md").read_text()
    for heading in (
        "## Purpose",
        "## Source layout",
        "## Development",
        "## Quality",
        "## Skill edits",
        "## Attribution",
        "## Git",
        "## Scope",
    ):
        assert heading in agents
    assert "Root `skills/` and `agent-definitions/` are canonical." in agents
    assert "pixi run pytest" in agents
    assert "pixi run ruff check" in agents
    assert "waterology render --check" in agents
    assert "python3 constraints/check-all.py ." in agents


def test_pi_package_loads_skills_subagents_and_mcp_extension() -> None:
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    assert package["version"] == "1.0.0"
    assert "pi-package" in package["keywords"]
    assert package["pi"] == {
        "extensions": ["./pi-extensions"],
        "skills": ["./pi-skills"],
        "prompts": ["./pi-prompts"],
    }
    assert package["pi-subagents"] == {"agents": ["./pi-agents"]}
