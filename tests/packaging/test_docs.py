from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_readme_documents_all_runtimes_and_cli() -> None:
    readme = (ROOT / "README.md").read_text()
    assert "Claude Code" in readme
    assert "Codex" in readme
    assert "OpenCode" in readme
    assert "waterology install all" in readme
    assert "waterology doctor" in readme


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
        "## TDD",
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


def test_roadmap_leaves_cross_runtime_foundation_unchecked() -> None:
    roadmap = (ROOT / "ROADMAP.md").read_text()
    assert "- [ ] **Slice 1: cross runtime foundation**" in roadmap
    assert "Task 10 owns the remaining acceptance checks." in roadmap
    assert "## Research feature roadmap" in roadmap
