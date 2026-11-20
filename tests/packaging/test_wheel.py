import json
import subprocess
import sys
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


def test_wheel_contains_cross_runtime_assets_without_retired_subsystems(tmp_path: Path) -> None:
    wheel = Path(ProjectBuilder(ROOT).build("wheel", tmp_path))
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())

    required = {
        "waterology/mcp/server.py",
        "waterology/core/literature.py",
        "waterology/core/literature_providers.py",
        "waterology/core/zotero.py",
        "waterology/core/huggingface.py",
        "waterology_assets/.mcp.json",
        "waterology_assets/opencode.json",
        "waterology_assets/package.json",
        "waterology_assets/skills/project-conventions/SKILL.md",
        "waterology_assets/skills/project-conventions/scripts/myst_to_quarto.py",
        "waterology_assets/skills/writing-style/SKILL.md",
        "waterology_assets/skills/research-software-quality/SKILL.md",
        "waterology_assets/skills/figures/SKILL.md",
        "waterology_assets/skills/figures/scripts/check_plotly_layout.py",
        "waterology_assets/skills/diagrams/SKILL.md",
        "waterology_assets/skills/diagrams/scripts/check_tikz_svg.py",
        "waterology_assets/skills/reports/SKILL.md",
        "waterology_assets/skills/reports/scripts/verify_report_bundle.py",
        "waterology_assets/skills/audit-reproducibility/SKILL.md",
        "waterology_assets/skills/audit-reproducibility/templates/run-all.sh",
        "waterology_assets/skills/bib-validate/scripts/validate_bib.py",
        "waterology_assets/skills/compile-latex/SKILL.md",
        "waterology_assets/skills/compile-latex/scripts/overfull_boxes.py",
        "waterology_assets/skills/literature-review/SKILL.md",
        "waterology_assets/skills/simulation-study/SKILL.md",
        "waterology_assets/commands/lit.md",
        "waterology_assets/commands/simulation-study.md",
        "waterology_assets/agent-definitions/engineer.md",
        "waterology_assets/agent-definitions/researcher.md",
        "waterology_assets/agent-definitions/reviewer.md",
        "waterology_assets/.agent/agents/researcher.md",
        "waterology_assets/.agent/agents/reviewer.md",
        "waterology_assets/agents/researcher.md",
        "waterology_assets/.codex/agents/researcher.toml",
        "waterology_assets/.opencode/agents/researcher.md",
        "waterology_assets/pi-agents/researcher.md",
        "waterology_assets/constraints/check-all.py",
        "waterology_assets/.claude-plugin/plugin.json",
        "waterology_assets/.codex-plugin/plugin.json",
        "waterology_assets/ATTRIBUTION.md",
    }
    assert required <= names
    assert not any(name.startswith("waterology/dashboard/") for name in names)
    assert not any(name.startswith("waterology/torc/") for name in names)
    assert not any(name.startswith("waterology/agents/") for name in names)


def _assert_manifest_covers_installed_destinations(manifest_path: Path) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    installed_destinations: set[str] = set()
    for path in manifest_path.parent.iterdir():
        if path.name in {manifest_path.name, ".waterology-install.lock"}:
            continue
        destinations = path.iterdir() if path.is_dir() else (path,)
        installed_destinations.update(
            destination.relative_to(manifest_path.parent).as_posix() for destination in destinations
        )

    assert set(manifest["assets"]) == installed_destinations
    assert all((manifest_path.parent / destination).exists() for destination in manifest["assets"])


@pytest.mark.parametrize(
    ("runtime", "agent_path", "skill_path", "mcp_path"),
    [
        (
            "claude",
            ".claude/agents/researcher.md",
            ".claude/skills/project-conventions",
            ".mcp.json",
        ),
        (
            "opencode",
            ".opencode/agents/researcher.md",
            ".opencode/skills/project-conventions",
            "opencode.json",
        ),
    ],
)
def test_project_install_smoke(
    tmp_path: Path,
    runtime: str,
    agent_path: str,
    skill_path: str,
    mcp_path: str,
) -> None:
    result = runner.invoke(app, ["install", runtime, "--target", str(tmp_path)])

    assert result.exit_code == 0, result.stdout
    assert (tmp_path / skill_path / "SKILL.md").is_file()
    assert (tmp_path / mcp_path).is_file()
    installed_agent = tmp_path / agent_path
    if installed_agent.suffix == ".toml":
        assert tomllib.loads(installed_agent.read_text(encoding="utf-8"))["name"] == "researcher"
    else:
        assert yaml.safe_load(installed_agent.read_text(encoding="utf-8").split("---", 2)[1])

    skills_root = (tmp_path / skill_path).parent
    for relative in (
        "bib-validate/scripts/validate_bib.py",
        "project-conventions/scripts/myst_to_quarto.py",
    ):
        completed = subprocess.run(
            [sys.executable, str(skills_root / relative), "--help"],
            capture_output=True,
            check=False,
            text=True,
        )
        assert completed.returncode == 0, completed.stderr
    completed = subprocess.run(
        [
            sys.executable,
            str(skills_root / "compile-latex/scripts/overfull_boxes.py"),
            str(tmp_path),
        ],
        capture_output=True,
        check=False,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr

    manifests = sorted(tmp_path.rglob(".waterology-install.json"))
    assert manifests
    for manifest in manifests:
        _assert_manifest_covers_installed_destinations(manifest)

    if runtime == "claude":
        assert (tmp_path / ".claude/commands/lit.md").is_file()


def test_pi_project_install_smoke(tmp_path: Path) -> None:
    result = runner.invoke(app, ["install", "pi", "--target", str(tmp_path)])

    assert result.exit_code == 0, result.stdout
    assert (tmp_path / ".pi/skills/waterology-project-conventions/SKILL.md").is_file()
    assert (tmp_path / ".pi/prompts/waterology-lit.md").is_file()
    agent = tmp_path / ".pi/agents/researcher.md"
    assert agent.is_file()
    metadata = yaml.safe_load(agent.read_text(encoding="utf-8").split("---", 2)[1])
    assert metadata["package"] == "waterology"
    manifest = tmp_path / ".pi/.waterology-install.json"
    assert manifest.is_file()
    _assert_manifest_covers_installed_destinations(manifest)


def test_all_runtime_dry_run_is_json_and_read_only(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["install", "all", "--target", str(tmp_path), "--dry-run", "--json"],
    )

    assert result.exit_code == 0
    assert json.loads(result.stdout)["dry_run"] is True
    assert list(tmp_path.iterdir()) == []
