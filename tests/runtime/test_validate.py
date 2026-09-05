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

    assert claude["name"] == codex["name"] == "waterology"
    assert claude["version"] == codex["version"] == "0.4.0"
    for field in ("description", "author", "homepage", "repository", "license", "keywords"):
        assert claude[field] == codex[field]
    assert "Claude Code plugin" not in claude["description"]
    assert codex["skills"] == "./skills/"


def test_repository_assets_validate_cleanly() -> None:
    assert validate_assets(AssetCatalog.discover()) == ()


def test_validation_reports_a_mismatched_skill_directory(tmp_path: Path) -> None:
    catalog = copied_catalog(tmp_path)
    skill = catalog.path("skills/eli5/SKILL.md")
    skill.write_text(skill.read_text(encoding="utf-8").replace("name: eli5", "name: wrong-name", 1))

    issues = validate_assets(catalog)

    assert ("skills/eli5/SKILL.md", "invalid-name", "wrong-name") in {
        (issue.path, issue.code, issue.message) for issue in issues
    }


def test_validation_reports_duplicate_skill_names(tmp_path: Path) -> None:
    catalog = copied_catalog(tmp_path)
    skill = catalog.path("skills/eli5/SKILL.md")
    skill.write_text(
        skill.read_text(encoding="utf-8").replace("name: eli5", "name: autoresearch", 1)
    )

    issues = validate_assets(catalog)

    assert ("skills/eli5/SKILL.md", "duplicate-name", "autoresearch") in {
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
    name: log
    argument-hint: (none)
---

# Writing Style""",
            1,
        ),
        encoding="utf-8",
    )

    issues = validate_assets(catalog)

    assert ("skills/writing-style/SKILL.md", "duplicate-claude-command", "log") in {
        (issue.path, issue.code, issue.message) for issue in issues
    }


def test_validation_reports_invalid_claude_command_metadata(tmp_path: Path) -> None:
    catalog = copied_catalog(tmp_path)
    skill = catalog.path("skills/session-log/SKILL.md")
    skill.write_text(
        skill.read_text(encoding="utf-8").replace("argument-hint: (none)", "argument-hint: ''"),
        encoding="utf-8",
    )

    issues = validate_assets(catalog)

    assert ("skills/session-log/SKILL.md", "invalid-skill-definition") in {
        (issue.path, issue.code) for issue in issues
    }


def test_validation_reports_a_missing_local_skill_reference(tmp_path: Path) -> None:
    catalog = copied_catalog(tmp_path)
    skill = catalog.path("skills/eli5/SKILL.md")
    skill.write_text(
        skill.read_text(encoding="utf-8")
        + "\n[Missing reference](references/missing.md)\n",
        encoding="utf-8",
    )

    issues = validate_assets(catalog)

    assert (
        "skills/eli5/SKILL.md",
        "missing-skill-reference",
        "references/missing.md",
    ) in {(issue.path, issue.code, issue.message) for issue in issues}


def test_validation_checks_nested_skill_references_and_images(tmp_path: Path) -> None:
    catalog = copied_catalog(tmp_path)
    skill_directory = catalog.path("skills/eli5")
    reference = skill_directory / "references" / "guide.md"
    reference.parent.mkdir()
    reference.write_text("![Missing image](missing.png)\n", encoding="utf-8")
    skill = skill_directory / "SKILL.md"
    skill.write_text(
        skill.read_text(encoding="utf-8")
        + "\n[Guide](references/guide.md)\n",
        encoding="utf-8",
    )

    issues = validate_assets(catalog)

    assert (
        "skills/eli5/references/guide.md",
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
    command = catalog.path("commands/log.md")
    command.write_text("stale\n", encoding="utf-8")

    issues = validate_assets(catalog)

    assert ("commands/log.md", "stale-generated-command") in {
        (issue.path, issue.code) for issue in issues
    }
    assert command.read_text(encoding="utf-8") == "stale\n"


def test_validation_reports_generated_command_directory(tmp_path: Path) -> None:
    catalog = copied_catalog(tmp_path)
    command = catalog.path("commands/log.md")
    command.unlink()
    command.mkdir()

    issues = validate_assets(catalog)

    assert (
        "commands/log.md",
        "invalid-asset-type",
        "generated command must be a file",
    ) in {(issue.path, issue.code, issue.message) for issue in issues}


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


def test_validation_reports_malformed_manifest_json(tmp_path: Path) -> None:
    catalog = copied_catalog(tmp_path)
    manifest = catalog.path(".claude-plugin/plugin.json")
    manifest.write_text("{", encoding="utf-8")

    issues = validate_assets(catalog)

    assert (".claude-plugin/plugin.json", "invalid-json") in {
        (issue.path, issue.code) for issue in issues
    }


def test_validation_reports_a_non_object_manifest(tmp_path: Path) -> None:
    catalog = copied_catalog(tmp_path)
    manifest = catalog.path(".claude-plugin/plugin.json")
    manifest.write_text("[]", encoding="utf-8")

    issues = validate_assets(catalog)

    assert (".claude-plugin/plugin.json", "invalid-manifest") in {
        (issue.path, issue.code) for issue in issues
    }


def test_validation_reports_a_missing_manifest(tmp_path: Path) -> None:
    catalog = copied_catalog(tmp_path)
    manifest = catalog.path(".claude-plugin/plugin.json")
    manifest.unlink()

    issues = validate_assets(catalog)

    assert (".claude-plugin/plugin.json", "missing-asset") in {
        (issue.path, issue.code) for issue in issues
    }
    assert not manifest.exists()


@pytest.mark.parametrize("directory", (".codex/agents", "agents", ".opencode/agents"))
def test_validation_reports_a_missing_generated_agent_directory(
    tmp_path: Path, directory: str
) -> None:
    catalog = copied_catalog(tmp_path)
    agent_directory = catalog.path(directory)
    shutil.rmtree(agent_directory)

    issues = validate_assets(catalog)

    assert (directory, "missing-asset") in {(issue.path, issue.code) for issue in issues}
    assert not agent_directory.exists()


def test_validation_collects_missing_and_malformed_generated_assets(tmp_path: Path) -> None:
    catalog = copied_catalog(tmp_path)
    shutil.rmtree(catalog.path("agents"))
    codex_agent = catalog.path(".codex/agents/researcher.toml")
    codex_agent.write_text("not valid = [", encoding="utf-8")

    issues = validate_assets(catalog)
    issue_codes = {(issue.path, issue.code) for issue in issues}

    assert ("agents", "missing-asset") in issue_codes
    assert (".codex/agents/researcher.toml", "invalid-toml") in issue_codes
    assert (".codex/agents/researcher.toml", "stale-generated-agent") in issue_codes
    assert not any(
        path.startswith("agents/") and code == "stale-generated-agent" for path, code in issue_codes
    )
    assert codex_agent.read_text(encoding="utf-8") == "not valid = ["


def test_validation_reports_a_generated_agent_path_with_the_wrong_type(tmp_path: Path) -> None:
    catalog = copied_catalog(tmp_path)
    agent_directory = catalog.path("agents")
    shutil.rmtree(agent_directory)
    agent_directory.write_text("not a directory", encoding="utf-8")

    issues = validate_assets(catalog)
    issue_codes = {(issue.path, issue.code) for issue in issues}

    assert ("agents", "invalid-asset-type") in issue_codes
    assert not any(
        path.startswith("agents/") and code == "stale-generated-agent" for path, code in issue_codes
    )
    assert agent_directory.read_text(encoding="utf-8") == "not a directory"


def test_validation_reports_a_missing_canonical_agent_and_orphaned_adapters(
    tmp_path: Path,
) -> None:
    catalog = copied_catalog(tmp_path)
    catalog.path("agent-definitions/writer.md").unlink()

    issues = validate_assets(catalog)
    issue_codes = {(issue.path, issue.code) for issue in issues}

    assert ("agent-definitions/writer.md", "missing-asset") in issue_codes
    for path in (
        "agents/writer.md",
        ".codex/agents/writer.toml",
        ".opencode/agents/writer.md",
    ):
        assert (path, "orphaned-generated-agent") in issue_codes


def test_validation_reports_a_missing_canonical_agent_directory(tmp_path: Path) -> None:
    catalog = copied_catalog(tmp_path)
    shutil.rmtree(catalog.path("agent-definitions"))

    issues = validate_assets(catalog)

    assert ("agent-definitions", "missing-asset") in {(issue.path, issue.code) for issue in issues}


def test_validation_reports_an_unexpected_canonical_agent(tmp_path: Path) -> None:
    catalog = copied_catalog(tmp_path)
    unexpected = catalog.path("agent-definitions") / "extra.md"
    unexpected.write_text(
        "---\n"
        "name: extra\n"
        "description: Unexpected agent.\n"
        "capabilities: [read]\n"
        "---\n\n"
        "Unexpected agent.\n",
        encoding="utf-8",
    )

    issues = validate_assets(catalog)

    assert ("agent-definitions/extra.md", "unexpected-asset") in {
        (issue.path, issue.code) for issue in issues
    }


def test_validation_checks_an_unexpected_canonical_agent_definition(tmp_path: Path) -> None:
    catalog = copied_catalog(tmp_path)
    unexpected = catalog.path("agent-definitions") / "extra.md"
    unexpected.write_text(
        "---\n"
        "name: writer\n"
        "description: Unexpected agent.\n"
        "capabilities: [read]\n"
        "---\n\n"
        "Unexpected agent.\n",
        encoding="utf-8",
    )

    issues = validate_assets(catalog)
    issue_codes = {(issue.path, issue.code) for issue in issues}

    assert ("agent-definitions/extra.md", "unexpected-asset") in issue_codes
    assert ("agent-definitions/extra.md", "invalid-name") in issue_codes


def test_validation_reports_a_canonical_filename_name_mismatch(tmp_path: Path) -> None:
    catalog = copied_catalog(tmp_path)
    writer = catalog.path("agent-definitions/writer.md")
    writer.write_text(
        writer.read_text(encoding="utf-8").replace("name: writer", "name: reviewer", 1),
        encoding="utf-8",
    )

    issues = validate_assets(catalog)

    assert ("agent-definitions/writer.md", "invalid-name") in {
        (issue.path, issue.code) for issue in issues
    }


@pytest.mark.parametrize(
    ("content", "code"),
    (
        ("Writer body without frontmatter.\n", "invalid-frontmatter"),
        ("---\nname: [\n---\n\nWriter body.\n", "invalid-frontmatter"),
        ("---\nscalar\n---\n\nWriter body.\n", "invalid-frontmatter"),
        (
            (
                "---\n"
                "name: writer\n"
                "description: Write research results.\n"
                "capabilities: [invalid]\n"
                "---\n\n"
                "Writer body.\n"
            ),
            "invalid-agent-definition",
        ),
    ),
)
def test_validation_reports_invalid_canonical_agent_definitions(
    tmp_path: Path, content: str, code: str
) -> None:
    catalog = copied_catalog(tmp_path)
    catalog.path("agent-definitions/writer.md").write_text(content, encoding="utf-8")

    issues = validate_assets(catalog)

    assert ("agent-definitions/writer.md", code) in {(issue.path, issue.code) for issue in issues}


@pytest.mark.parametrize(
    ("directory", "filename"),
    (
        ("agents", "writer.md"),
        (".codex/agents", "writer.toml"),
        (".opencode/agents", "writer.md"),
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


@pytest.mark.parametrize(
    ("directory", "filename"),
    (
        ("agents", "orphan.md"),
        (".codex/agents", "orphan.toml"),
        (".opencode/agents", "orphan.md"),
    ),
)
def test_validation_reports_an_orphaned_generated_agent(
    tmp_path: Path, directory: str, filename: str
) -> None:
    catalog = copied_catalog(tmp_path)
    orphan = catalog.path(directory) / filename
    orphan.write_text("orphan\n", encoding="utf-8")

    issues = validate_assets(catalog)

    assert (f"{directory}/{filename}", "orphaned-generated-agent") in {
        (issue.path, issue.code) for issue in issues
    }
