import json
from dataclasses import replace
from pathlib import Path

import pytest

from waterology.runtime import install as module
from waterology.runtime.assets import AssetCatalog
from waterology.runtime.install import (
    InstallConflictError,
    InstallMode,
    InstallScope,
    Runtime,
    apply_install_plan,
    apply_uninstall_plan,
    build_install_plan,
)


@pytest.mark.parametrize("runtime", list(Runtime))
@pytest.mark.parametrize("scope", list(InstallScope))
@pytest.mark.parametrize("mode", list(InstallMode))
def test_round_trip(tmp_path, monkeypatch, runtime, scope, mode):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / "config"))
    plan = build_install_plan(runtime, scope, tmp_path / "project", mode, AssetCatalog.discover())
    apply_install_plan(plan)
    user_file = plan.actions[0].destination.parent / "personal.txt"
    user_file.write_text("keep")
    result = apply_uninstall_plan(plan)
    assert result.changed
    assert user_file.read_text() == "keep"
    assert all(not p.exists() and not p.is_symlink() for p in result.changed)
    assert not apply_uninstall_plan(plan).changed
    apply_install_plan(plan)
    assert all(a.destination.exists() for a in plan.actions)


def test_uninstall_preserves_modified_asset_and_all_other_assets(tmp_path):
    plan = build_install_plan(
        Runtime.PI, InstallScope.PROJECT, tmp_path, InstallMode.COPY, AssetCatalog.discover()
    )
    apply_install_plan(plan)
    changed = plan.actions[0].destination / "SKILL.md"
    changed.write_text("user edit")
    with pytest.raises(InstallConflictError):
        apply_uninstall_plan(plan)
    assert changed.read_text() == "user edit"
    assert all(a.destination.exists() for a in plan.actions)


def test_upgrade_removes_retired_assets(tmp_path):
    plan = build_install_plan(
        Runtime.PI, InstallScope.PROJECT, tmp_path, InstallMode.COPY, AssetCatalog.discover()
    )
    apply_install_plan(plan)
    retired = plan.actions[0]
    newer = replace(plan, actions=plan.actions[1:])
    apply_install_plan(newer)
    assert not retired.destination.exists()
    data = json.loads(retired.manifest.read_text())
    assert retired.destination.relative_to(retired.manifest.parent).as_posix() not in data["assets"]


def test_uninstall_rollback(tmp_path, monkeypatch):
    plan = build_install_plan(
        Runtime.PI, InstallScope.PROJECT, tmp_path, InstallMode.COPY, AssetCatalog.discover()
    )
    apply_install_plan(plan)
    real_replace = module.os.replace
    calls = 0

    def fail_once(src, dst):
        nonlocal calls
        calls += 1
        if calls == 3:
            raise OSError("interrupted")
        return real_replace(src, dst)

    monkeypatch.setattr(module.os, "replace", fail_once)
    with pytest.raises(OSError, match="interrupted"):
        apply_uninstall_plan(plan)
    assert all(a.destination.exists() for a in plan.actions)
    assert all(a.manifest.exists() for a in plan.actions)


@pytest.mark.parametrize("operation", ["install", "uninstall"])
@pytest.mark.parametrize("phase", ["backup", "replacement"])
def test_recover_killed_process(tmp_path, operation, phase):
    import subprocess
    import sys

    from waterology.runtime.install import recover_install

    plan = build_install_plan(
        Runtime.PI, InstallScope.PROJECT, tmp_path, InstallMode.COPY, AssetCatalog.discover()
    )
    apply_install_plan(plan)
    before = {a.destination: module._path_state(a.destination) for a in plan.actions}
    script = """
import os, sys
from dataclasses import replace
from pathlib import Path
from waterology.runtime import install as m
from waterology.runtime.assets import AssetCatalog
plan = m.build_install_plan(m.Runtime.PI, m.InstallScope.PROJECT, Path(sys.argv[1]), m.InstallMode.COPY, AssetCatalog.discover())
real = m.os.replace
phase = sys.argv[3]
def crash(src, dst):
    real(src, dst)
    if phase == 'backup' and '.waterology-backup-' in str(dst):
        os._exit(81)
    if phase == 'replacement' and '.waterology-stage-' in str(src):
        os._exit(81)
m.os.replace = crash
if sys.argv[2] == 'uninstall':
    m.apply_uninstall_plan(plan)
else:
    m.apply_install_plan(replace(plan, actions=plan.actions[1:]))
"""
    # Uninstall has no replacement stage, so kill on its second backup instead.
    if operation == "uninstall" and phase == "replacement":
        script = script.replace(
            "if phase == 'replacement' and '.waterology-stage-' in str(src):",
            "if phase == 'replacement' and '.waterology-backup-' in str(dst):",
        )
    result = subprocess.run(
        [sys.executable, "-c", script, str(tmp_path), operation, phase],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 81, result.stderr
    assert (tmp_path / module._TRANSACTION_NAME).exists()
    assert recover_install(plan, dry_run=True)
    recover_install(plan)
    assert {a.destination: module._path_state(a.destination) for a in plan.actions} == before
    assert not (tmp_path / module._INSTALL_LOCK_NAME).exists()
    assert not (tmp_path / module._TRANSACTION_NAME).exists()
    apply_install_plan(plan)


def test_cli_uninstall_detects_link_mode_and_dry_run(tmp_path):
    from typer.testing import CliRunner

    from waterology.cli import app

    runner = CliRunner()
    args = ["pi", "--target", str(tmp_path), "--json"]
    assert runner.invoke(app, ["install", *args, "--mode", "link"]).exit_code == 0
    preview = runner.invoke(app, ["uninstall", *args, "--dry-run"])
    assert preview.exit_code == 0, preview.output
    paths = json.loads(preview.stdout)["results"]["pi"]
    assert all(Path(p).exists() for p in paths)
    removed = runner.invoke(app, ["uninstall", *args])
    assert removed.exit_code == 0, removed.output
    assert all(not Path(p).exists() for p in paths)


def test_upgrade_preserves_modified_retired_asset(tmp_path):
    plan = build_install_plan(
        Runtime.PI, InstallScope.PROJECT, tmp_path, InstallMode.COPY, AssetCatalog.discover()
    )
    apply_install_plan(plan)
    retired = plan.actions[0]
    (retired.destination / "SKILL.md").write_text("keep my edit")
    with pytest.raises(InstallConflictError):
        apply_install_plan(replace(plan, actions=plan.actions[1:]), force=True)
    assert (retired.destination / "SKILL.md").read_text() == "keep my edit"


@pytest.mark.parametrize("addition", ["empty_directory", "dangling_link", "directory_link"])
def test_uninstall_preserves_added_tree_entries(tmp_path, addition):
    plan = build_install_plan(
        Runtime.PI, InstallScope.PROJECT, tmp_path, InstallMode.COPY, AssetCatalog.discover()
    )
    apply_install_plan(plan)
    added = plan.actions[0].destination / "personal"
    if addition == "empty_directory":
        added.mkdir()
    else:
        added.symlink_to(
            tmp_path / ("absent" if addition == "dangling_link" else "outside"),
            target_is_directory=True,
        )
        if addition == "directory_link":
            (tmp_path / "outside").mkdir()
    with pytest.raises(InstallConflictError):
        apply_uninstall_plan(plan)
    assert added.exists() or added.is_symlink()


def test_recover_lock_only_and_reject_live_process(tmp_path):
    import os
    import subprocess
    import sys

    plan = build_install_plan(
        Runtime.PI, InstallScope.PROJECT, tmp_path, InstallMode.COPY, AssetCatalog.discover()
    )
    lock = tmp_path / module._INSTALL_LOCK_NAME
    lock.write_text(str(os.getpid()))
    with pytest.raises(ValueError, match="still running"):
        module.recover_install(plan)
    process = subprocess.Popen([sys.executable, "-c", "pass"])
    process.wait()
    lock.write_text(str(process.pid))
    assert module.recover_install(plan, dry_run=True) == (lock,)
    assert lock.exists()
    module.recover_install(plan)
    assert not lock.exists()


def test_recovery_serializes_with_other_recovery(tmp_path):
    plan = build_install_plan(
        Runtime.PI, InstallScope.PROJECT, tmp_path, InstallMode.COPY, AssetCatalog.discover()
    )
    with module._recovery_guard(tmp_path):
        with pytest.raises(ValueError, match="recovery is in progress"):
            module.recover_install(plan)
        with pytest.raises(ValueError, match="recovery is in progress"):
            apply_install_plan(plan)
    assert module.recover_install(plan) == ()


def test_upgrade_protects_modified_config_even_with_force(tmp_path):
    plan = build_install_plan(
        Runtime.CODEX, InstallScope.PROJECT, tmp_path, InstallMode.COPY, AssetCatalog.discover()
    )
    apply_install_plan(plan)
    config = tmp_path / ".codex/config.toml"
    config.write_text("# my settings\n")
    with pytest.raises(InstallConflictError):
        apply_install_plan(plan, force=True)
    assert config.read_text() == "# my settings\n"


def test_recovery_guard_releases_after_process_death(tmp_path):
    import subprocess
    import sys

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import os, sys; from pathlib import Path; from waterology.runtime.install import _recovery_guard\nwith _recovery_guard(Path(sys.argv[1])): os._exit(81)",
            str(tmp_path),
        ],
        check=False,
    )
    assert result.returncode == 81
    plan = build_install_plan(
        Runtime.PI, InstallScope.PROJECT, tmp_path, InstallMode.COPY, AssetCatalog.discover()
    )
    assert module.recover_install(plan) == ()
    apply_install_plan(plan)


def test_recover_committed_cleanup_after_process_death(tmp_path):
    import subprocess
    import sys

    plan = build_install_plan(
        Runtime.PI, InstallScope.PROJECT, tmp_path, InstallMode.COPY, AssetCatalog.discover()
    )
    apply_install_plan(plan)
    script = """
import os, sys
from pathlib import Path
from waterology.runtime import install as m
from waterology.runtime.assets import AssetCatalog
plan = m.build_install_plan(m.Runtime.PI, m.InstallScope.PROJECT, Path(sys.argv[1]), m.InstallMode.COPY, AssetCatalog.discover())
m._cleanup_backups = lambda changes: os._exit(81)
m.apply_uninstall_plan(plan)
"""
    result = subprocess.run([sys.executable, "-c", script, str(tmp_path)], check=False)
    assert result.returncode == 81
    assert json.loads((tmp_path / module._TRANSACTION_NAME).read_text())["state"] == "committed"
    module.recover_install(plan)
    assert all(not a.destination.exists() for a in plan.actions)
    assert not list(tmp_path.rglob("*.waterology-backup-*"))


def test_upgrade_old_manifest_version(tmp_path):
    plan = build_install_plan(
        Runtime.PI, InstallScope.PROJECT, tmp_path, InstallMode.COPY, AssetCatalog.discover()
    )
    apply_install_plan(plan)
    for manifest in {a.manifest for a in plan.actions}:
        data = json.loads(manifest.read_text())
        data["waterology_version"] = "0.5.7"
        manifest.write_text(json.dumps(data))
    apply_install_plan(replace(plan, actions=plan.actions[1:]))
    assert not plan.actions[0].destination.exists()
    assert (
        json.loads(plan.actions[0].manifest.read_text())["waterology_version"] == module.__version__
    )


def test_empty_uninstall_does_not_hide_pending_transaction(tmp_path):
    plan = build_install_plan(
        Runtime.PI, InstallScope.PROJECT, tmp_path, InstallMode.COPY, AssetCatalog.discover()
    )
    (tmp_path / module._TRANSACTION_NAME).write_text("{}")
    with pytest.raises(InstallConflictError, match="conflict"):
        apply_uninstall_plan(plan)
    with pytest.raises(InstallConflictError, match="conflict"):
        module.preflight(plan)


def test_windows_recovery_never_uses_kill_to_probe_pid(monkeypatch):
    def fail_kill(*args):
        raise AssertionError("kill must not be used on Windows")

    monkeypatch.setattr(module.sys, "platform", "win32")
    monkeypatch.setattr(module.os, "kill", fail_kill)
    monkeypatch.setattr(module, "_windows_process_is_running", lambda pid: True)
    with pytest.raises(ValueError, match="still running"):
        module._require_exited(123)
    monkeypatch.setattr(module, "_windows_process_is_running", lambda pid: False)
    module._require_exited(123)


def test_uninstall_rechecks_verified_state_before_deletion(tmp_path, monkeypatch):
    plan = build_install_plan(
        Runtime.PI, InstallScope.PROJECT, tmp_path, InstallMode.COPY, AssetCatalog.discover()
    )
    apply_install_plan(plan)
    added = plan.actions[0].destination / "user-notes.txt"
    run = module._run_transaction

    def edit_after_preflight(prepared, expected, selected):
        added.write_text("keep")
        return run(prepared, expected, selected)

    monkeypatch.setattr(module, "_run_transaction", edit_after_preflight)
    with pytest.raises(InstallConflictError):
        apply_uninstall_plan(plan)
    assert added.read_text() == "keep"
