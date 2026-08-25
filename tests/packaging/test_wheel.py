import json
import tomllib
import zipfile
from pathlib import Path

import pytest
import yaml
from build import ProjectBuilder
from typer.testing import CliRunner

from waterology.cli import app

ROOT = Path(__file__).resolve().parents[2]
runner = CliRunner()


def test_wheel_contains_cross_runtime_assets(tmp_path: Path) -> None:
    wheel = Path(ProjectBuilder(ROOT).build("wheel", tmp_path))
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())

    required = {
        "waterology_assets/skills/project-conventions/SKILL.md",
        "waterology_assets/skills/writing-style/SKILL.md",
        "waterology_assets/skills/writing-style/references/scientific-prose.md",
        "waterology_assets/skills/research-software-quality/SKILL.md",
        "waterology_assets/skills/research-software-quality/references/worktrees.md",
        "waterology_assets/agents/researcher.md",
        "waterology_assets/.codex/agents/researcher.toml",
        "waterology_assets/.opencode/agents/researcher.md",
        "waterology_assets/.claude-plugin/plugin.json",
        "waterology_assets/.codex-plugin/plugin.json",
        "waterology_assets/ATTRIBUTION.md",
    }
    assert required <= names


def _assert_manifest_covers_installed_destinations(manifest_path: Path) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    installed_destinations: set[str] = set()
    for path in manifest_path.parent.iterdir():
        if path.name in {manifest_path.name, ".waterology-install.lock"}:
            continue
        destinations = path.iterdir() if path.is_dir() else (path,)
        installed_destinations.update(
            destination.relative_to(manifest_path.parent).as_posix()
            for destination in destinations
        )

    assert set(manifest["assets"]) == installed_destinations
    assert all((manifest_path.parent / destination).exists() for destination in manifest["assets"])


@pytest.mark.parametrize(
    ("runtime", "agent_path", "skill_path"),
    [
        ("claude", ".claude/agents/researcher.md", ".claude/skills/project-conventions"),
        ("codex", ".codex/agents/researcher.toml", ".agents/skills/project-conventions"),
        ("opencode", ".opencode/agents/researcher.md", ".opencode/skills/project-conventions"),
    ],
)
def test_project_install_smoke(
    tmp_path: Path,
    runtime: str,
    agent_path: str,
    skill_path: str,
) -> None:
    result = runner.invoke(app, ["install", runtime, "--target", str(tmp_path)])

    assert result.exit_code == 0, result.stdout
    assert (tmp_path / skill_path / "SKILL.md").is_file()
    installed_agent = tmp_path / agent_path
    if installed_agent.suffix == ".toml":
        assert tomllib.loads(installed_agent.read_text(encoding="utf-8"))["name"] == "researcher"
    else:
        assert yaml.safe_load(installed_agent.read_text(encoding="utf-8").split("---", 2)[1])

    manifests = sorted(tmp_path.rglob(".waterology-install.json"))
    assert manifests
    for manifest in manifests:
        _assert_manifest_covers_installed_destinations(manifest)

    if runtime == "claude":
        assert (tmp_path / ".claude/commands/deepresearch.md").is_file()


def test_all_runtime_dry_run_is_json_and_read_only(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["install", "all", "--target", str(tmp_path), "--dry-run", "--json"],
    )

    assert result.exit_code == 0
    assert json.loads(result.stdout)["dry_run"] is True
    assert list(tmp_path.iterdir()) == []
