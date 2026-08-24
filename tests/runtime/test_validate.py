import json
import shutil
from pathlib import Path

import pytest

from waterology.runtime.assets import AssetCatalog
from waterology.runtime.validate import validate_assets


def copied_catalog(tmp_path: Path) -> AssetCatalog:
    source = AssetCatalog.discover().root
    destination = tmp_path / "assets"
    shutil.copytree(source, destination)
    return AssetCatalog.discover(destination)


def test_runtime_manifests_have_matching_identity() -> None:
    catalog = AssetCatalog.discover()
    claude = json.loads(catalog.path(".claude-plugin/plugin.json").read_text())
    codex = json.loads(catalog.path(".codex-plugin/plugin.json").read_text())

    assert claude["name"] == codex["name"] == "waterology"
    assert claude["version"] == codex["version"] == "0.2.0"
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
    skill.write_text(skill.read_text(encoding="utf-8").replace("name: eli5", "name: autoresearch", 1))

    issues = validate_assets(catalog)

    assert ("skills/eli5/SKILL.md", "duplicate-name", "autoresearch") in {
        (issue.path, issue.code, issue.message) for issue in issues
    }


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
    assert not any(path.startswith("agents/") and code == "stale-generated-agent" for path, code in issue_codes)
    assert codex_agent.read_text(encoding="utf-8") == "not valid = ["


def test_validation_reports_a_generated_agent_path_with_the_wrong_type(tmp_path: Path) -> None:
    catalog = copied_catalog(tmp_path)
    agent_directory = catalog.path("agents")
    shutil.rmtree(agent_directory)
    agent_directory.write_text("not a directory", encoding="utf-8")

    issues = validate_assets(catalog)
    issue_codes = {(issue.path, issue.code) for issue in issues}

    assert ("agents", "invalid-asset-type") in issue_codes
    assert not any(path.startswith("agents/") and code == "stale-generated-agent" for path, code in issue_codes)
    assert agent_directory.read_text(encoding="utf-8") == "not a directory"
