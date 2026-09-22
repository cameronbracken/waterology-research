import hashlib
import json
import shutil
from dataclasses import replace
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


def load_manifest(tmp_path: Path, root: str = ".opencode") -> dict:
    return json.loads((tmp_path / root / ".waterology-install.json").read_text())


def write_manifest(tmp_path: Path, data: dict, root: str = ".opencode") -> None:
    (tmp_path / root / ".waterology-install.json").write_text(json.dumps(data) + "\n")


def test_copy_install_writes_manifest_and_assets(tmp_path: Path) -> None:
    result = apply_install_plan(make_plan(tmp_path))

    assert result.changed
    assert (tmp_path / ".opencode/agents/researcher.md").is_file()
    manifest = json.loads((tmp_path / ".opencode/.waterology-install.json").read_text())
    assert manifest["schema"] == 1
    assert manifest["waterology_version"] == "0.5.7"
    assert "agents/researcher.md" in manifest["assets"]
    serialized = (tmp_path / ".opencode/.waterology-install.json").read_text()
    assert serialized == json.dumps(manifest, indent=2, sort_keys=True) + "\n"


@pytest.mark.parametrize(
    ("runtime", "skill_root"),
    [
        (Runtime.CLAUDE, ".claude/skills"),
        (Runtime.CODEX, ".agents/skills"),
        (Runtime.OPENCODE, ".opencode/skills"),
        (Runtime.PI, ".pi/skills"),
    ],
)
def test_installed_autoresearch_tree_reference_resolves(
    tmp_path: Path, runtime: Runtime, skill_root: str
) -> None:
    plan = build_install_plan(
        runtime,
        InstallScope.PROJECT,
        tmp_path,
        InstallMode.COPY,
        AssetCatalog.discover(),
    )

    apply_install_plan(plan)

    skill = tmp_path / skill_root / "autoresearch/SKILL.md"
    reference = skill.parent / "references/experiment-tree.md"
    token_reference = skill.parent / "references/token-discipline.md"
    assert skill.is_file()
    assert reference.is_file()
    assert token_reference.is_file()
    skill_text = skill.read_text(encoding="utf-8")
    assert "[experiment-tree.md](references/experiment-tree.md)" in skill_text
    assert "[token-discipline.md](references/token-discipline.md)" in skill_text


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
    assert set(codex_manifest["assets"]) >= {"agents/researcher.toml", "config.toml"}
    assert (tmp_path / ".codex/config.toml").read_text(encoding="utf-8") == (
        '[mcp_servers.waterology]\ncommand = "waterology-mcp"\n'
    )


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


def test_project_install_rejects_a_symlinked_runtime_root(tmp_path: Path) -> None:
    project = tmp_path / "project"
    outside = tmp_path / "outside"
    project.mkdir()
    outside.mkdir()
    (project / ".opencode").symlink_to(outside, target_is_directory=True)

    with pytest.raises(InstallConflictError) as caught:
        apply_install_plan(make_plan(project))

    assert caught.value.conflicts[0].destination == project / ".opencode"
    assert not any(outside.iterdir())


def test_project_install_rejects_a_nested_symlink_parent(tmp_path: Path) -> None:
    project = tmp_path / "project"
    outside = tmp_path / "outside"
    (project / ".opencode").mkdir(parents=True)
    outside.mkdir()
    (project / ".opencode/skills").symlink_to(outside, target_is_directory=True)

    with pytest.raises(InstallConflictError) as caught:
        apply_install_plan(make_plan(project))

    assert caught.value.conflicts[0].destination == project / ".opencode/skills"
    assert not any(outside.iterdir())
    assert not (project / ".opencode/agents").exists()


def test_user_install_rejects_a_symlinked_runtime_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "home"
    outside = tmp_path / "outside"
    home.mkdir()
    outside.mkdir()
    (home / ".agents").symlink_to(outside, target_is_directory=True)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    plan = build_install_plan(
        Runtime.CODEX,
        InstallScope.USER,
        Path("unused"),
        InstallMode.COPY,
        AssetCatalog.discover(),
    )

    with pytest.raises(InstallConflictError):
        apply_install_plan(plan)

    assert not any(outside.iterdir())
    assert not (home / ".codex").exists()


def test_install_rejects_a_lexical_destination_escape(tmp_path: Path) -> None:
    plan = make_plan(tmp_path)
    outside = tmp_path.parent / "outside.md"
    escaped_action = replace(
        plan.actions[-1],
        destination=outside,
        manifest=tmp_path / ".opencode/.waterology-install.json",
    )
    escaped_plan = replace(plan, actions=(escaped_action,))

    with pytest.raises(InstallConflictError) as caught:
        apply_install_plan(escaped_plan)

    assert caught.value.conflicts[0].destination == outside
    assert not outside.exists()


def test_boolean_manifest_schema_is_rejected(tmp_path: Path) -> None:
    manifest = tmp_path / ".opencode/.waterology-install.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text('{"schema": true, "runtime": "opencode", "mode": "copy", "assets": {}}\n')

    with pytest.raises(ValueError, match="Unsupported install manifest schema"):
        apply_install_plan(make_plan(tmp_path))

    assert not (tmp_path / ".opencode/agents").exists()


def test_manifest_runtime_must_match_the_plan(tmp_path: Path) -> None:
    plan = make_plan(tmp_path)
    apply_install_plan(plan)
    manifest = load_manifest(tmp_path)
    manifest["runtime"] = "codex"
    write_manifest(tmp_path, manifest)

    with pytest.raises(ValueError, match="runtime does not match"):
        apply_install_plan(plan)


def test_copy_to_link_mode_transition_is_rejected(tmp_path: Path) -> None:
    apply_install_plan(make_plan(tmp_path, InstallMode.COPY))
    destination = tmp_path / ".opencode/agents/researcher.md"

    with pytest.raises(ValueError, match="mode does not match"):
        apply_install_plan(make_plan(tmp_path, InstallMode.LINK))

    assert not destination.is_symlink()


@pytest.mark.parametrize(
    "record",
    [
        [],
        {"source": ".opencode/agents/researcher.md", "kind": "file"},
        {
            "source": ".opencode/agents/researcher.md",
            "sha256": "not-a-hash",
            "kind": "file",
        },
        {
            "source": ".opencode/agents/researcher.md",
            "sha256": "0" * 64,
            "kind": "file",
            "extra": True,
        },
        {
            "source": ".opencode/agents/researcher.md",
            "sha256": "0" * 64,
            "kind": [],
        },
        {
            "source": ".opencode/agents/researcher.md",
            "sha256": "0" * 64,
            "kind": "device",
        },
    ],
)
def test_malformed_manifest_asset_records_are_rejected(tmp_path: Path, record: object) -> None:
    plan = make_plan(tmp_path)
    apply_install_plan(plan)
    manifest = load_manifest(tmp_path)
    manifest["assets"]["agents/researcher.md"] = record
    write_manifest(tmp_path, manifest)

    with pytest.raises(ValueError, match="Invalid install manifest asset record"):
        apply_install_plan(plan)


def test_manifest_asset_keys_must_be_normalized_relative_paths(tmp_path: Path) -> None:
    plan = make_plan(tmp_path)
    apply_install_plan(plan)
    manifest = load_manifest(tmp_path)
    manifest["assets"]["../outside.md"] = {
        "source": ".opencode/agents/researcher.md",
        "sha256": "0" * 64,
        "kind": "file",
    }
    write_manifest(tmp_path, manifest)

    with pytest.raises(ValueError, match="normalized relative path"):
        apply_install_plan(plan)


def test_manifest_source_must_match_the_planned_source(tmp_path: Path) -> None:
    plan = make_plan(tmp_path)
    apply_install_plan(plan)
    manifest = load_manifest(tmp_path)
    manifest["assets"]["agents/researcher.md"]["source"] = "agents/other.md"
    write_manifest(tmp_path, manifest)

    with pytest.raises(ValueError, match="source does not match"):
        apply_install_plan(plan, force=True)


def test_manifest_kind_must_match_the_planned_kind(tmp_path: Path) -> None:
    plan = make_plan(tmp_path)
    apply_install_plan(plan)
    manifest = load_manifest(tmp_path)
    manifest["assets"]["agents/researcher.md"]["kind"] = "directory"
    write_manifest(tmp_path, manifest)

    with pytest.raises(ValueError, match="kind does not match"):
        apply_install_plan(plan, force=True)


def test_manifest_kind_must_match_the_actual_destination(tmp_path: Path) -> None:
    plan = make_plan(tmp_path)
    apply_install_plan(plan)
    destination = tmp_path / ".opencode/agents/researcher.md"
    destination.unlink()
    destination.mkdir()

    with pytest.raises(ValueError, match="kind does not match the destination"):
        apply_install_plan(plan, force=True)

    assert destination.is_dir()


def test_uppercase_manifest_hashes_are_valid(tmp_path: Path) -> None:
    plan = make_plan(tmp_path)
    apply_install_plan(plan)
    manifest = load_manifest(tmp_path)
    for record in manifest["assets"].values():
        record["sha256"] = record["sha256"].upper()
    write_manifest(tmp_path, manifest)

    result = apply_install_plan(plan)

    assert result.changed == ()


def test_recorded_link_must_still_point_to_the_planned_source(tmp_path: Path) -> None:
    plan = make_plan(tmp_path, InstallMode.LINK)
    apply_install_plan(plan)
    destination = tmp_path / ".opencode/skills/project-conventions"
    destination.unlink()
    destination.symlink_to(tmp_path / "other", target_is_directory=True)
    manifest = load_manifest(tmp_path)
    digest = hashlib.sha256(str(destination.resolve()).encode()).hexdigest()
    manifest["assets"]["skills/project-conventions"]["sha256"] = digest
    write_manifest(tmp_path, manifest)

    with pytest.raises(InstallConflictError) as caught:
        apply_install_plan(plan)

    assert caught.value.conflicts == (
        InstallConflict(destination, "owned symlink points to a different source"),
    )


def test_late_action_failure_rolls_back_an_earlier_action(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = make_plan(tmp_path)
    first = plan.actions[0].destination
    failing = plan.actions[1].destination
    real_replace = install_module.os.replace

    def fail_second_action(source: Path, target: Path) -> None:
        source = Path(source)
        target = Path(target)
        if target == failing and ".waterology-stage-" in source.name:
            raise OSError("injected late action failure")
        real_replace(source, target)

    monkeypatch.setattr(install_module.os, "replace", fail_second_action)

    with pytest.raises(OSError, match="injected late action failure"):
        apply_install_plan(plan)

    assert not first.exists()
    assert not failing.exists()
    assert not any(tmp_path.iterdir())


def test_late_action_failure_restores_an_earlier_owned_action(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = make_plan(tmp_path)
    apply_install_plan(plan)
    earlier = plan.actions[0].destination
    marker = earlier / "SKILL.md"
    marker.write_text("locally modified\n")
    failing = plan.actions[1].destination
    shutil.rmtree(failing)
    manifest = tmp_path / ".opencode/.waterology-install.json"
    prior_manifest = manifest.read_bytes()
    real_replace = install_module.os.replace

    def fail_second_action(source: Path, target: Path) -> None:
        source = Path(source)
        target = Path(target)
        if target == failing and ".waterology-stage-" in source.name:
            raise OSError("injected owned action failure")
        real_replace(source, target)

    monkeypatch.setattr(install_module.os, "replace", fail_second_action)

    with pytest.raises(OSError, match="injected owned action failure"):
        apply_install_plan(plan, force=True)

    assert marker.read_text() == "locally modified\n"
    assert not failing.exists()
    assert manifest.read_bytes() == prior_manifest
    assert not list(tmp_path.rglob("*.waterology-stage-*"))
    assert not list(tmp_path.rglob("*.waterology-backup-*"))


def test_second_codex_manifest_failure_rolls_back_actions_and_first_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = build_install_plan(
        Runtime.CODEX,
        InstallScope.PROJECT,
        tmp_path,
        InstallMode.COPY,
        AssetCatalog.discover(),
    )
    failing = tmp_path / ".codex/.waterology-install.json"
    real_replace = install_module.os.replace

    def fail_second_manifest(source: Path, target: Path) -> None:
        source = Path(source)
        target = Path(target)
        if target == failing and ".waterology-stage-" in source.name:
            raise OSError("injected second manifest failure")
        real_replace(source, target)

    monkeypatch.setattr(install_module.os, "replace", fail_second_manifest)

    with pytest.raises(OSError, match="injected second manifest failure"):
        apply_install_plan(plan)

    assert not (tmp_path / ".agents").exists()
    assert not (tmp_path / ".codex").exists()


def test_manifest_failure_restores_prior_manifests(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = build_install_plan(
        Runtime.CODEX,
        InstallScope.PROJECT,
        tmp_path,
        InstallMode.COPY,
        AssetCatalog.discover(),
    )
    apply_install_plan(plan)
    agents_manifest = tmp_path / ".agents/.waterology-install.json"
    codex_manifest = tmp_path / ".codex/.waterology-install.json"
    for path in (agents_manifest, codex_manifest):
        data = json.loads(path.read_text())
        data["waterology_version"] = "prior-version"
        path.write_text(json.dumps(data) + "\n")
    prior_agents = agents_manifest.read_bytes()
    prior_codex = codex_manifest.read_bytes()
    real_replace = install_module.os.replace

    def fail_second_manifest(source: Path, target: Path) -> None:
        source = Path(source)
        target = Path(target)
        if target == codex_manifest and ".waterology-stage-" in source.name:
            raise OSError("injected manifest update failure")
        real_replace(source, target)

    monkeypatch.setattr(install_module.os, "replace", fail_second_manifest)

    with pytest.raises(OSError, match="injected manifest update failure"):
        apply_install_plan(plan)

    assert agents_manifest.read_bytes() == prior_agents
    assert codex_manifest.read_bytes() == prior_codex
    assert not list(tmp_path.rglob("*.waterology-stage-*"))
    assert not list(tmp_path.rglob("*.waterology-backup-*"))


def test_manifest_staging_failure_cleans_all_stages_and_created_parents(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = build_install_plan(
        Runtime.CODEX,
        InstallScope.PROJECT,
        tmp_path,
        InstallMode.COPY,
        AssetCatalog.discover(),
    )
    real_write_text = Path.write_text

    def fail_second_manifest_stage(
        path: Path, data: str, encoding: str | None = None, errors: str | None = None
    ) -> int:
        if path.parent == tmp_path / ".codex" and ".waterology-stage-" in path.name:
            raise OSError("injected manifest staging failure")
        return real_write_text(path, data, encoding=encoding, errors=errors)

    monkeypatch.setattr(Path, "write_text", fail_second_manifest_stage)

    with pytest.raises(OSError, match="injected manifest staging failure"):
        apply_install_plan(plan)

    assert not any(tmp_path.iterdir())


def test_destination_appearing_after_staging_is_not_overwritten(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = make_plan(tmp_path)
    destination = next(action.destination for action in plan.actions if action.source.is_file())
    real_commit = install_module._commit_prepared_changes

    def create_collision_then_commit(*args: object, **kwargs: object) -> None:
        destination.write_text("created during install\n")
        real_commit(*args, **kwargs)

    monkeypatch.setattr(
        install_module,
        "_commit_prepared_changes",
        create_collision_then_commit,
    )

    with pytest.raises(InstallConflictError, match="conflict"):
        apply_install_plan(plan)

    assert destination.read_text() == "created during install\n"
    assert not plan.actions[0].destination.exists()
    assert not (tmp_path / ".opencode/.waterology-install.json").exists()


def test_failed_stage_replacement_does_not_remove_a_new_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = make_plan(tmp_path)
    destination = next(action.destination for action in plan.actions if action.source.is_file())
    real_replace = install_module.os.replace

    def create_collision_and_fail(source: Path, target: Path) -> None:
        source = Path(source)
        target = Path(target)
        if target == destination and ".waterology-stage-" in source.name:
            destination.write_text("created during replacement\n")
            raise OSError("injected replacement race")
        real_replace(source, target)

    monkeypatch.setattr(install_module.os, "replace", create_collision_and_fail)

    with pytest.raises(OSError, match="injected replacement race"):
        apply_install_plan(plan)

    assert destination.read_text() == "created during replacement\n"
    assert not plan.actions[0].destination.exists()
    assert not (tmp_path / ".opencode/.waterology-install.json").exists()


@pytest.mark.parametrize("mutation", ["disappear", "kind", "fingerprint"])
def test_owned_destination_state_is_revalidated_before_commit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    plan = make_plan(tmp_path)
    apply_install_plan(plan)
    destination = next(action.destination for action in plan.actions if action.source.is_file())
    real_commit = install_module._commit_prepared_changes

    def mutate_then_commit(*args: object, **kwargs: object) -> None:
        destination.unlink()
        if mutation == "kind":
            destination.mkdir()
        elif mutation == "fingerprint":
            destination.write_text("changed during install\n")
        real_commit(*args, **kwargs)

    monkeypatch.setattr(install_module, "_commit_prepared_changes", mutate_then_commit)

    with pytest.raises(InstallConflictError, match="conflict"):
        apply_install_plan(plan)

    if mutation == "disappear":
        assert not destination.exists()
    elif mutation == "kind":
        assert destination.is_dir()
    else:
        assert destination.read_text() == "changed during install\n"


def test_owned_link_target_is_revalidated_before_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = make_plan(tmp_path, InstallMode.LINK)
    apply_install_plan(plan)
    destination = plan.actions[0].destination
    raced_target = tmp_path / "other"
    real_commit = install_module._commit_prepared_changes

    def retarget_then_commit(*args: object, **kwargs: object) -> None:
        destination.unlink()
        destination.symlink_to(raced_target, target_is_directory=True)
        real_commit(*args, **kwargs)

    monkeypatch.setattr(install_module, "_commit_prepared_changes", retarget_then_commit)

    with pytest.raises(InstallConflictError, match="conflict"):
        apply_install_plan(plan)

    assert destination.is_symlink()
    assert destination.resolve() == raced_target


def test_force_modified_destination_is_revalidated_before_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = make_plan(tmp_path)
    apply_install_plan(plan)
    destination = next(action.destination for action in plan.actions if action.source.is_file())
    destination.write_text("modified before force install\n")
    real_commit = install_module._commit_prepared_changes

    def modify_again_then_commit(*args: object, **kwargs: object) -> None:
        destination.write_text("modified after staging\n")
        real_commit(*args, **kwargs)

    monkeypatch.setattr(install_module, "_commit_prepared_changes", modify_again_then_commit)

    with pytest.raises(InstallConflictError, match="conflict"):
        apply_install_plan(plan, force=True)

    assert destination.read_text() == "modified after staging\n"


@pytest.mark.parametrize("path_kind", ["destination", "manifest"])
def test_plan_paths_with_internal_parent_segments_are_rejected(
    tmp_path: Path, path_kind: str
) -> None:
    plan = make_plan(tmp_path)
    action = plan.actions[-1]
    if path_kind == "destination":
        action = replace(
            action,
            destination=tmp_path / ".opencode/agents/../agents/unnormalized.md",
        )
    else:
        action = replace(
            action,
            manifest=tmp_path / ".opencode/nested/../.waterology-install.json",
        )
    plan = replace(plan, actions=(action,))

    with pytest.raises(InstallConflictError, match="conflict") as caught:
        apply_install_plan(plan)

    assert caught.value.conflicts[0].reason == "path is not normalized"
    assert not any(tmp_path.iterdir())


@pytest.mark.parametrize("version", [None, "", 3])
def test_manifest_waterology_version_must_be_a_nonempty_string(
    tmp_path: Path, version: object
) -> None:
    plan = make_plan(tmp_path)
    apply_install_plan(plan)
    manifest = load_manifest(tmp_path)
    if version is None:
        manifest.pop("waterology_version")
    else:
        manifest["waterology_version"] = version
    write_manifest(tmp_path, manifest)

    with pytest.raises(ValueError, match="waterology_version"):
        apply_install_plan(plan)


def test_concurrent_waterology_install_lock_blocks_all_plan_writes(tmp_path: Path) -> None:
    lock = tmp_path / ".waterology-install.lock"
    lock.write_text("existing installer\n")

    with pytest.raises(InstallConflictError) as caught:
        apply_install_plan(make_plan(tmp_path))

    assert caught.value.conflicts == (
        InstallConflict(lock, "another Waterology install is in progress"),
    )
    assert lock.read_text() == "existing installer\n"
    assert not (tmp_path / ".opencode").exists()


def test_locked_preflight_detects_a_destination_created_during_lock_acquisition(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = make_plan(tmp_path)
    lock = tmp_path / ".waterology-install.lock"
    collision = next(action.destination for action in plan.actions if action.source.is_file())
    real_open = install_module.os.open

    def create_collision_after_lock(
        path: str | bytes | Path,
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        descriptor = real_open(path, flags, mode, dir_fd=dir_fd)
        if Path(path) == lock:
            collision.parent.mkdir(parents=True)
            collision.write_text("created during lock acquisition\n")
        return descriptor

    monkeypatch.setattr(install_module.os, "open", create_collision_after_lock)

    with pytest.raises(InstallConflictError):
        apply_install_plan(plan)

    assert collision.read_text() == "created during lock acquisition\n"
    assert not plan.actions[0].destination.exists()
    assert not (tmp_path / ".opencode/.waterology-install.json").exists()
    assert not lock.exists()


def test_install_lock_is_removed_after_staging_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = make_plan(tmp_path)
    lock = tmp_path / ".waterology-install.lock"
    lock_seen = False

    def fail_staging(
        action: object,
        trusted_root: Path,
        created_parents: list[Path],
    ) -> Path:
        nonlocal lock_seen
        lock_seen = lock.is_file()
        raise OSError("injected staging failure with lock")

    monkeypatch.setattr(install_module, "_stage_action", fail_staging)

    with pytest.raises(OSError, match="injected staging failure with lock"):
        apply_install_plan(plan)

    assert lock_seen
    assert not lock.exists()
    assert not any(tmp_path.iterdir())


def test_install_lock_is_removed_after_commit_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = make_plan(tmp_path)
    lock = tmp_path / ".waterology-install.lock"
    lock_seen = False

    def fail_commit(*args: object, **kwargs: object) -> None:
        nonlocal lock_seen
        lock_seen = lock.is_file()
        raise OSError("injected commit failure with lock")

    monkeypatch.setattr(install_module, "_commit_prepared_changes", fail_commit)

    with pytest.raises(OSError, match="injected commit failure with lock"):
        apply_install_plan(plan)

    assert lock_seen
    assert not lock.exists()
    assert not any(tmp_path.iterdir())


def test_moved_backup_is_verified_before_the_stage_is_installed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = make_plan(tmp_path)
    apply_install_plan(plan)
    destination = next(action.destination for action in plan.actions if action.source.is_file())
    destination.write_text("authorized force change\n")
    prior_manifest = (tmp_path / ".opencode/.waterology-install.json").read_bytes()
    real_replace = install_module.os.replace

    def mutate_moved_backup(source: Path, target: Path) -> None:
        source = Path(source)
        target = Path(target)
        real_replace(source, target)
        if source == destination and ".waterology-backup-" in target.name:
            target.write_text("changed while moving to backup\n")

    monkeypatch.setattr(install_module.os, "replace", mutate_moved_backup)

    with pytest.raises(InstallConflictError):
        apply_install_plan(plan, force=True)

    recovery_paths = [
        destination,
        *destination.parent.glob(f".{destination.name}.waterology-backup-*"),
    ]
    assert any(
        path.is_file() and path.read_text() == "changed while moving to backup\n"
        for path in recovery_paths
    )
    assert (tmp_path / ".opencode/.waterology-install.json").read_bytes() == prior_manifest
    assert not (tmp_path / ".waterology-install.lock").exists()


def test_rollback_preserves_an_externally_replaced_installed_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = make_plan(tmp_path)
    installed_then_replaced = plan.actions[0].destination
    failing = plan.actions[1].destination
    real_replace = install_module.os.replace

    def replace_first_then_fail(source: Path, target: Path) -> None:
        source = Path(source)
        target = Path(target)
        if target == installed_then_replaced and ".waterology-stage-" in source.name:
            real_replace(source, target)
            shutil.rmtree(target)
            target.write_text("external replacement\n")
            return
        if target == failing and ".waterology-stage-" in source.name:
            raise OSError("injected failure after external replacement")
        real_replace(source, target)

    monkeypatch.setattr(install_module.os, "replace", replace_first_then_fail)

    with pytest.raises(OSError, match="injected failure") as caught:
        apply_install_plan(plan)

    assert installed_then_replaced.read_text() == "external replacement\n"
    assert any(
        str(installed_then_replaced) in note for note in getattr(caught.value, "__notes__", ())
    )
    assert not (tmp_path / ".waterology-install.lock").exists()


def test_rollback_preserves_a_new_destination_and_reports_its_backup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = make_plan(tmp_path)
    apply_install_plan(plan)
    destination = next(action.destination for action in plan.actions if action.source.is_file())
    destination.write_text("authorized force change\n")
    real_replace = install_module.os.replace
    backup: Path | None = None

    def create_destination_before_restore(source: Path, target: Path) -> None:
        nonlocal backup
        source = Path(source)
        target = Path(target)
        if source == destination and ".waterology-backup-" in target.name:
            backup = target
            real_replace(source, target)
            return
        if target == destination and ".waterology-stage-" in source.name:
            destination.write_text("appeared before backup restoration\n")
            raise OSError("injected replacement failure before restore")
        real_replace(source, target)

    monkeypatch.setattr(install_module.os, "replace", create_destination_before_restore)

    with pytest.raises(OSError, match="injected replacement failure") as caught:
        apply_install_plan(plan, force=True)

    assert destination.read_text() == "appeared before backup restoration\n"
    assert backup is not None
    assert backup.read_text() == "authorized force change\n"
    assert any(str(backup) in note for note in getattr(caught.value, "__notes__", ()))
    assert not (tmp_path / ".waterology-install.lock").exists()
