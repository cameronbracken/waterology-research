import json
import shutil
from pathlib import Path

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
