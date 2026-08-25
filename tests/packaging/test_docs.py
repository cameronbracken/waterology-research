import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_distribution_name_preserves_waterology_cli() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    pixi = tomllib.loads((ROOT / "pixi.toml").read_text())

    assert project["project"]["name"] == "waterology-research"
    assert project["project"]["scripts"] == {"waterology": "waterology.cli:app"}
    assert "waterology-research" in pixi["pypi-dependencies"]
    assert "waterology" not in pixi["pypi-dependencies"]

    repository = "https://codeberg.org/waterology/waterology-research"
    for path in (".claude-plugin/plugin.json", ".codex-plugin/plugin.json"):
        manifest = json.loads((ROOT / path).read_text())
        assert manifest["name"] == "waterology"
        assert manifest["homepage"] == repository
        assert manifest["repository"] == repository

    readme = (ROOT / "README.md").read_text()
    assert "ssh://git@codeberg.org/waterology/waterology-research.git" in readme


def test_readme_documents_all_runtimes_and_cli() -> None:
    readme = (ROOT / "README.md").read_text()
    assert "Claude Code" in readme
    assert "Codex" in readme
    assert "OpenCode" in readme
    assert "waterology install all" in readme
    assert "waterology doctor" in readme


def test_readme_documents_the_local_experiment_workflow() -> None:
    readme = (ROOT / "README.md").read_text()
    for command in (
        "pixi run waterology init",
        "pixi run waterology experiment create",
        "pixi run waterology worktree open",
        "pixi run waterology run start",
        "pixi run waterology run assess",
        "pixi run waterology archive verify",
        "pixi run waterology repair-index",
    ):
        assert command in readme
    assert "SQLite is a rebuildable index." in readme
    assert "freezes the experiment at the run commit." in readme


def test_readme_documents_install_scope_and_runtime_contracts() -> None:
    readme = (ROOT / "README.md").read_text()
    for command in (
        "pixi run waterology install claude",
        "pixi run waterology install codex",
        "pixi run waterology install opencode",
        "pixi run waterology install all --dry-run",
        "pixi run waterology doctor",
        "pixi run waterology install codex --scope user",
    ):
        assert command in readme
    for url in (
        "https://developers.openai.com/plugins/concepts/plugins",
        "https://opencode.ai/docs/skills",
        "https://opencode.ai/v2/docs/agents",
    ):
        assert url in readme
    assert "Project scope is the default." in readme
    assert "Use `--scope user` for user configuration." in readme
    assert "`--target` is available only for project installs." in readme
    assert "Both `install` and `doctor` support `--json`." in readme
    assert "Root `skills/` is canonical." in readme
    assert "Generated Codex agents install in `.codex/agents/`." in readme
    assert "Codex installs root skills in `.agents/skills/`." in readme
    assert "only after confirming that no Waterology install process is running" in readme


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
    assert "`agents/`, `.codex/agents/`, and `.opencode/agents/` are generated." in agents
    assert "pixi run pytest" in agents
    assert "pixi run ruff check" in agents
    assert "waterology render --check" in agents
    assert "python3 constraints/check-all.py ." in agents


def test_roadmap_marks_platform_slices_complete() -> None:
    readme = (ROOT / "README.md").read_text()
    roadmap = (ROOT / "ROADMAP.md").read_text()

    assert (
        "The cross runtime foundation, research methods migration, and experiment core\n"
        "are complete."
    ) in readme
    assert "Research workflows are runtime neutral." in readme
    assert "- [x] **Slice 1: cross runtime foundation**" in roadmap
    assert "- [x] **Slice 2: research methods**" in roadmap
    assert "- [x] **Slice 3: experiment core**" in roadmap
    assert roadmap.count("- [x]") == 3
    assert "Task 10 owns the remaining acceptance checks." not in roadmap
    assert "Later skill migration remains planned for Slice 2." not in roadmap
    assert "## Research feature roadmap" in roadmap
