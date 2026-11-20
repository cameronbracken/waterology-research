import json
import shutil
from pathlib import Path

import pytest

from waterology.runtime.assets import AssetCatalog
from waterology.runtime.validate import validate_assets

COPY_IGNORE = shutil.ignore_patterns(
    ".git",
    ".pixi",
    ".pytest_cache",
    ".ruff_cache",
    ".superpowers",
    ".worktrees",
    "__pycache__",
    "*.pyc",
)


def copied_catalog(tmp_path: Path) -> AssetCatalog:
    source = AssetCatalog.discover().root
    destination = tmp_path / "assets"
    shutil.copytree(source, destination, ignore=COPY_IGNORE)
    return AssetCatalog.discover(destination)


def test_runtime_manifests_have_matching_identity() -> None:
    catalog = AssetCatalog.discover()
    claude = json.loads(catalog.path(".claude-plugin/plugin.json").read_text())
    codex = json.loads(catalog.path(".codex-plugin/plugin.json").read_text())
    pi = json.loads(catalog.path("package.json").read_text())

    assert claude["name"] == codex["name"] == "waterology"
    assert claude["version"] == codex["version"] == pi["version"] == "1.0.0"
    assert pi["pi"] == {
        "extensions": ["./pi-extensions"],
        "skills": ["./pi-skills"],
        "prompts": ["./pi-prompts"],
    }
    assert pi["pi-subagents"] == {"agents": ["./pi-agents"]}
    for field in ("description", "author", "homepage", "repository", "license", "keywords"):
        assert claude[field] == codex[field]
    assert codex["skills"] == "./skills/"


def test_repository_assets_validate_cleanly() -> None:
    assert validate_assets(AssetCatalog.discover()) == ()


def test_validation_reports_invalid_pi_package(tmp_path: Path) -> None:
    catalog = copied_catalog(tmp_path)
    package = catalog.path("package.json")
    package.write_text(
        '{"version":"1.0.0","keywords":["pi-package"],"pi":{"skills":[]},'
        '"pi-subagents":{"agents":[]}}\n',
        encoding="utf-8",
    )

    issues = validate_assets(catalog)

    assert any(
        issue.path == "package.json" and issue.code == "invalid-pi-package" for issue in issues
    )


def test_validation_reports_a_mismatched_skill_directory(tmp_path: Path) -> None:
    catalog = copied_catalog(tmp_path)
    skill = catalog.path("skills/figures/SKILL.md")
    skill.write_text(
        skill.read_text(encoding="utf-8").replace("name: figures", "name: wrong-name", 1)
    )

    issues = validate_assets(catalog)

    assert ("skills/figures/SKILL.md", "invalid-name", "wrong-name") in {
        (issue.path, issue.code, issue.message) for issue in issues
    }


def test_validation_reports_duplicate_skill_names(tmp_path: Path) -> None:
    catalog = copied_catalog(tmp_path)
    skill = catalog.path("skills/figures/SKILL.md")
    skill.write_text(
        skill.read_text(encoding="utf-8").replace("name: figures", "name: autoresearch", 1)
    )

    issues = validate_assets(catalog)

    assert ("skills/figures/SKILL.md", "duplicate-name", "autoresearch") in {
        (issue.path, issue.code, issue.message) for issue in issues
    }


def test_validation_reports_duplicate_claude_command_names(tmp_path: Path) -> None:
    catalog = copied_catalog(tmp_path)
    skill = catalog.path("skills/writing-style/SKILL.md")
    skill.write_text(
        skill.read_text(encoding="utf-8").replace(
            "---\n\n# Writing Style",
            """metadata:
  claude-command:
    name: lit
    argument-hint: <topic>
---

# Writing Style""",
            1,
        ),
        encoding="utf-8",
    )

    issues = validate_assets(catalog)

    assert ("skills/writing-style/SKILL.md", "duplicate-claude-command", "lit") in {
        (issue.path, issue.code, issue.message) for issue in issues
    }


def test_validation_reports_invalid_claude_command_metadata(tmp_path: Path) -> None:
    catalog = copied_catalog(tmp_path)
    skill = catalog.path("skills/literature-review/SKILL.md")
    skill.write_text(
        skill.read_text(encoding="utf-8").replace(
            "argument-hint: <topic, research question, or author/lab>",
            "argument-hint: ''",
        ),
        encoding="utf-8",
    )

    issues = validate_assets(catalog)

    assert ("skills/literature-review/SKILL.md", "invalid-skill-definition") in {
        (issue.path, issue.code) for issue in issues
    }


def test_validation_reports_a_missing_local_skill_reference(tmp_path: Path) -> None:
    catalog = copied_catalog(tmp_path)
    skill = catalog.path("skills/figures/SKILL.md")
    skill.write_text(
        skill.read_text(encoding="utf-8") + "\n[Missing reference](references/missing.md)\n",
        encoding="utf-8",
    )

    issues = validate_assets(catalog)

    assert (
        "skills/figures/SKILL.md",
        "missing-skill-reference",
        "references/missing.md",
    ) in {(issue.path, issue.code, issue.message) for issue in issues}


def test_validation_checks_nested_skill_references_and_images(tmp_path: Path) -> None:
    catalog = copied_catalog(tmp_path)
    skill_directory = catalog.path("skills/figures")
    reference = skill_directory / "references" / "guide.md"
    reference.write_text("![Missing image](missing.png)\n", encoding="utf-8")
    skill = skill_directory / "SKILL.md"
    skill.write_text(
        skill.read_text(encoding="utf-8") + "\n[Guide](references/guide.md)\n",
        encoding="utf-8",
    )

    issues = validate_assets(catalog)

    assert (
        "skills/figures/references/guide.md",
        "missing-skill-reference",
        "missing.png",
    ) in {(issue.path, issue.code, issue.message) for issue in issues}


def test_validation_reports_malformed_codex_toml(tmp_path: Path) -> None:
    catalog = copied_catalog(tmp_path)
    agent = catalog.path(".codex/agents/researcher.toml")
    agent.write_text("not valid = [", encoding="utf-8")

    issues = validate_assets(catalog)

    assert (".codex/agents/researcher.toml", "invalid-toml") in {
        (issue.path, issue.code) for issue in issues
    }


def test_validation_reports_stale_generated_agents_without_writing(tmp_path: Path) -> None:
    catalog = copied_catalog(tmp_path)
    agent = catalog.path(".codex/agents/researcher.toml")
    agent.write_text("stale\n", encoding="utf-8")

    issues = validate_assets(catalog)

    assert (".codex/agents/researcher.toml", "stale-generated-agent") in {
        (issue.path, issue.code) for issue in issues
    }
    assert agent.read_text(encoding="utf-8") == "stale\n"


def test_validation_reports_stale_generated_command_without_writing(tmp_path: Path) -> None:
    catalog = copied_catalog(tmp_path)
    command = catalog.path("commands/lit.md")
    command.write_text("stale\n", encoding="utf-8")

    issues = validate_assets(catalog)

    assert ("commands/lit.md", "stale-generated-command") in {
        (issue.path, issue.code) for issue in issues
    }
    assert command.read_text(encoding="utf-8") == "stale\n"


def test_validation_reports_orphaned_generated_command(tmp_path: Path) -> None:
    catalog = copied_catalog(tmp_path)
    command = catalog.path("commands") / "orphan.md"
    command.write_text(
        "---\n"
        "description: Orphaned command.\n"
        "argument-hint: (none)\n"
        "---\n\n"
        "<!-- Generated from skills/missing/SKILL.md. Do not edit. -->\n",
        encoding="utf-8",
    )

    issues = validate_assets(catalog)

    assert ("commands/orphan.md", "orphaned-generated-command") in {
        (issue.path, issue.code) for issue in issues
    }


def test_validation_reports_a_missing_canonical_agent_and_orphaned_adapters(
    tmp_path: Path,
) -> None:
    catalog = copied_catalog(tmp_path)
    catalog.path("agent-definitions/reviewer.md").unlink()

    issues = validate_assets(catalog)
    issue_codes = {(issue.path, issue.code) for issue in issues}

    assert ("agent-definitions/reviewer.md", "missing-asset") in issue_codes
    for path in (
        ".agent/agents/reviewer.md",
        "agents/reviewer.md",
        ".codex/agents/reviewer.toml",
        ".opencode/agents/reviewer.md",
        "pi-agents/reviewer.md",
    ):
        assert (path, "orphaned-generated-agent") in issue_codes


@pytest.mark.parametrize(
    ("directory", "filename"),
    (
        (".agent/agents", "reviewer.md"),
        ("agents", "reviewer.md"),
        (".codex/agents", "reviewer.toml"),
        (".opencode/agents", "reviewer.md"),
        ("pi-agents", "reviewer.md"),
    ),
)
def test_validation_reports_a_missing_generated_agent(
    tmp_path: Path, directory: str, filename: str
) -> None:
    catalog = copied_catalog(tmp_path)
    missing = catalog.path(f"{directory}/{filename}")
    missing.unlink()

    issues = validate_assets(catalog)

    assert (f"{directory}/{filename}", "missing-asset") in {
        (issue.path, issue.code) for issue in issues
    }
    assert not missing.exists()
