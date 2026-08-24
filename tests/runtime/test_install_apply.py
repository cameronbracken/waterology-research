import json
import shutil
from pathlib import Path

import pytest

import waterology.runtime.install as install_module
from waterology.runtime.assets import AssetCatalog
from waterology.runtime.install import (
    InstallConflict,
    InstallConflictError,
    InstallMode,
    InstallPlan,
    InstallScope,
    Runtime,
    apply_install_plan,
    build_install_plan,
    preflight,
)


def make_plan(tmp_path: Path, mode: InstallMode = InstallMode.COPY) -> InstallPlan:
    return build_install_plan(
        Runtime.OPENCODE,
        InstallScope.PROJECT,
        tmp_path,
        mode,
        AssetCatalog.discover(),
    )


def test_copy_install_writes_manifest_and_assets(tmp_path: Path) -> None:
    result = apply_install_plan(make_plan(tmp_path))

    assert result.changed
    assert (tmp_path / ".opencode/agents/researcher.md").is_file()
    manifest = json.loads((tmp_path / ".opencode/.waterology-install.json").read_text())
    assert manifest["schema"] == 1
    assert manifest["waterology_version"] == "0.2.0"
    assert "agents/researcher.md" in manifest["assets"]
    serialized = (tmp_path / ".opencode/.waterology-install.json").read_text()
    assert serialized == json.dumps(manifest, indent=2, sort_keys=True) + "\n"


def test_unowned_destination_blocks_every_write(tmp_path: Path) -> None:
    collision = tmp_path / ".opencode/agents/researcher.md"
    collision.parent.mkdir(parents=True)
    collision.write_text("user-owned\n")

    with pytest.raises(InstallConflictError):
        apply_install_plan(make_plan(tmp_path))

    assert collision.read_text() == "user-owned\n"
    assert not (tmp_path / ".opencode/skills/project-conventions").exists()


def test_link_install_points_to_source_assets(tmp_path: Path) -> None:
    apply_install_plan(make_plan(tmp_path, InstallMode.LINK))

    installed = tmp_path / ".opencode/skills/project-conventions"
    assert installed.is_symlink()
    assert installed.resolve() == AssetCatalog.discover().path("skills/project-conventions")


@pytest.mark.parametrize("mode", [InstallMode.COPY, InstallMode.LINK])
def test_reinstall_is_idempotent(tmp_path: Path, mode: InstallMode) -> None:
    plan = make_plan(tmp_path, mode)
    apply_install_plan(plan)
    manifest = tmp_path / ".opencode/.waterology-install.json"
    original_manifest = manifest.read_bytes()

    result = apply_install_plan(plan)

    assert result.changed == ()
    assert result.unchanged == tuple(action.destination for action in plan.actions)
    assert manifest.read_bytes() == original_manifest


def test_modified_owned_destination_requires_force_and_blocks_every_write(
    tmp_path: Path,
) -> None:
    plan = make_plan(tmp_path)
    apply_install_plan(plan)
    missing = plan.actions[0].destination
    shutil.rmtree(missing)
    modified = tmp_path / ".opencode/agents/researcher.md"
    modified.write_text("locally modified\n")

    with pytest.raises(InstallConflictError) as caught:
        apply_install_plan(plan)

    assert caught.value.conflicts == (InstallConflict(modified, "owned destination was modified"),)
    assert not missing.exists()
    assert modified.read_text() == "locally modified\n"


def test_force_replaces_modified_owned_destination(tmp_path: Path) -> None:
    plan = make_plan(tmp_path)
    apply_install_plan(plan)
    destination = tmp_path / ".opencode/agents/researcher.md"
    destination.write_text("locally modified\n")

    result = apply_install_plan(plan, force=True)

    assert (
        destination.read_bytes()
        == AssetCatalog.discover().path(".opencode/agents/researcher.md").read_bytes()
    )
    assert destination in result.changed


def test_force_refuses_unowned_destination(tmp_path: Path) -> None:
    collision = tmp_path / ".opencode/agents/researcher.md"
    collision.parent.mkdir(parents=True)
    collision.write_text("user-owned\n")

    with pytest.raises(InstallConflictError) as caught:
        apply_install_plan(make_plan(tmp_path), force=True)

    assert caught.value.conflicts[0].reason == "destination is not owned"
    assert collision.read_text() == "user-owned\n"
    assert not (tmp_path / ".opencode/skills").exists()


def test_unsupported_manifest_schema_is_rejected_before_asset_writes(tmp_path: Path) -> None:
    manifest = tmp_path / ".opencode/.waterology-install.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text('{"schema": 2, "assets": {}}\n')

    with pytest.raises(ValueError, match="Unsupported install manifest schema"):
        apply_install_plan(make_plan(tmp_path))

    assert not (tmp_path / ".opencode/agents").exists()
    assert not (tmp_path / ".opencode/skills").exists()


def test_broken_symlink_manifest_is_rejected_before_asset_writes(tmp_path: Path) -> None:
    manifest = tmp_path / ".opencode/.waterology-install.json"
    manifest.parent.mkdir(parents=True)
    manifest.symlink_to(tmp_path / "missing-manifest.json")

    with pytest.raises(ValueError, match="Install manifest must be a regular file"):
        apply_install_plan(make_plan(tmp_path))

    assert manifest.is_symlink()
    assert not (tmp_path / ".opencode/agents").exists()
    assert not (tmp_path / ".opencode/skills").exists()


def test_directory_manifest_fingerprint_detects_nested_file_changes(tmp_path: Path) -> None:
    plan = make_plan(tmp_path)
    apply_install_plan(plan)
    installed = tmp_path / ".opencode/skills/project-conventions"
    manifest = json.loads((tmp_path / ".opencode/.waterology-install.json").read_text())
    record = manifest["assets"]["skills/project-conventions"]
    (installed / "SKILL.md").write_text("locally modified\n")

    conflicts = preflight(plan)

    assert record["kind"] == "directory"
    assert len(record["sha256"]) == 64
    assert conflicts[0].destination == installed
    assert conflicts[0].reason == "owned destination was modified"


def test_codex_install_writes_separate_root_relative_manifests(tmp_path: Path) -> None:
    plan = build_install_plan(
        Runtime.CODEX,
        InstallScope.PROJECT,
        tmp_path,
        InstallMode.COPY,
        AssetCatalog.discover(),
    )

    result = apply_install_plan(plan)

    agents_manifest = json.loads((tmp_path / ".agents/.waterology-install.json").read_text())
    codex_manifest = json.loads((tmp_path / ".codex/.waterology-install.json").read_text())
    assert set(result.manifests) == {
        tmp_path / ".agents/.waterology-install.json",
        tmp_path / ".codex/.waterology-install.json",
    }
    assert agents_manifest["assets"]
    assert all(key.startswith("skills/") for key in agents_manifest["assets"])
    assert codex_manifest["assets"]
    assert all(key.startswith("agents/") for key in codex_manifest["assets"])


def test_force_refuses_an_unowned_broken_symlink(tmp_path: Path) -> None:
    collision = tmp_path / ".opencode/agents/researcher.md"
    collision.parent.mkdir(parents=True)
    collision.symlink_to(tmp_path / "missing.md")

    with pytest.raises(InstallConflictError):
        apply_install_plan(make_plan(tmp_path, InstallMode.LINK), force=True)

    assert collision.is_symlink()
    assert not collision.exists()


def test_force_replaces_a_modified_owned_symlink(tmp_path: Path) -> None:
    plan = make_plan(tmp_path, InstallMode.LINK)
    apply_install_plan(plan)
    destination = tmp_path / ".opencode/skills/project-conventions"
    destination.unlink()
    destination.symlink_to(tmp_path / "missing", target_is_directory=True)

    with pytest.raises(InstallConflictError):
        apply_install_plan(plan)

    apply_install_plan(plan, force=True)

    assert destination.is_symlink()
    assert destination.resolve() == AssetCatalog.discover().path("skills/project-conventions")


def test_directory_replacement_restores_the_owned_directory_when_rename_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = make_plan(tmp_path)
    apply_install_plan(plan)
    destination = tmp_path / ".opencode/skills/project-conventions"
    marker = destination / "SKILL.md"
    marker.write_text("locally modified\n")
    original_siblings = {path.name for path in destination.parent.iterdir()}
    real_replace = install_module.os.replace

    def fail_staged_directory(source: Path, target: Path) -> None:
        source = Path(source)
        target = Path(target)
        if target == destination and ".waterology-stage-" in source.name:
            raise OSError("injected directory rename failure")
        real_replace(source, target)

    monkeypatch.setattr(install_module.os, "replace", fail_staged_directory)

    with pytest.raises(OSError, match="injected directory rename failure"):
        apply_install_plan(plan, force=True)

    assert destination.is_dir()
    assert marker.read_text() == "locally modified\n"
    assert {path.name for path in destination.parent.iterdir()} == original_siblings
