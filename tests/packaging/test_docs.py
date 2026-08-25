from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_readme_documents_all_runtimes_and_cli() -> None:
    readme = (ROOT / "README.md").read_text()
    assert "Claude Code" in readme
    assert "Codex" in readme
    assert "OpenCode" in readme
    assert "waterology install all" in readme
    assert "waterology doctor" in readme


def test_claude_guidance_defers_to_agents() -> None:
    claude = (ROOT / "CLAUDE.md").read_text()
    assert len(claude.splitlines()) <= 20
    assert "AGENTS.md" in claude


def test_canonical_guidance_has_required_commands() -> None:
    agents = (ROOT / "AGENTS.md").read_text()
    assert "pixi run pytest" in agents
    assert "pixi run ruff check" in agents
    assert "waterology render --check" in agents
    assert "python3 constraints/check-all.py ." in agents
