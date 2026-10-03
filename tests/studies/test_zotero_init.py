import io
import json
import subprocess
import tomllib

import pytest
from typer.testing import CliRunner

from waterology.cli import app
from waterology.core import zotero
from waterology.core.config import load_project_config, project_config_toml
from waterology.core.project import initialize_project


@pytest.fixture
def project(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    initialize_project(tmp_path)
    path = tmp_path / "waterology.toml"
    path.write_text("# Preserve this comment\n" + path.read_text())
    return tmp_path


def identity(monkeypatch, payload):
    monkeypatch.setenv("ZOTERO_API_KEY", "private-fixture-key")
    requests = []

    class Opener:
        def open(self, request, timeout):
            requests.append(request)
            assert timeout == 30
            return io.BytesIO(json.dumps(payload).encode())

    monkeypatch.setattr(zotero, "build_opener", lambda *args: Opener())
    return requests


def test_cli_init_resolves_library_and_updates_project(project, monkeypatch):
    requests = identity(
        monkeypatch,
        {
            "userID": 123,
            "access": {"user": {"library": True, "write": True}},
        },
    )
    result = CliRunner().invoke(app, ["zotero", "init", "My collection", "--path", str(project)])
    assert result.exit_code == 0, result.output
    settings = tomllib.loads((project / ".zotero.toml").read_text())
    assert settings["library_id"] == "123"
    assert settings["collection_name"] == "My collection"
    assert len(settings["collection_key"]) == 8
    assert requests[0].full_url == "https://api.zotero.org/keys/current"
    assert requests[0].get_header("Zotero-api-key") == "private-fixture-key"
    assert "private-fixture-key" not in result.output
    assert "private-fixture-key" not in (project / ".zotero.toml").read_text()
    config = load_project_config(project / "waterology.toml")
    assert config.zotero.settings_file == ".zotero.toml"
    assert "# Preserve this comment" in (project / "waterology.toml").read_text()
    assert tomllib.loads(project_config_toml(config))["zotero"] == {"settings_file": ".zotero.toml"}
    monkeypatch.delenv("ZOTERO_API_KEY")
    assert zotero.initialize_zotero(project, "My collection") == settings
    assert len(requests) == 1
    with pytest.raises(ValueError, match="different destination"):
        zotero.initialize_zotero(project, "Another collection")
    assert zotero.settings_for(project).collection_key == settings["collection_key"]


@pytest.mark.parametrize("legacy", [".zotero.nt", "zotero.nt"])
def test_init_migrates_legacy_without_changing_identity(project, legacy):
    (project / legacy).write_text(
        "library_id: 00123\ncollection_name: Legacy\ncollection_key: ABCDEFGH\n"
    )
    result = zotero.initialize_zotero(project, "Legacy")
    assert result["library_id"] == "00123"
    assert result["collection_key"] == "ABCDEFGH"
    assert (project / legacy).exists()
    assert zotero.settings_for(project).model_dump() == result


@pytest.mark.parametrize(
    "payload",
    [
        {"userID": 123, "access": {"user": {"library": True}}},
        {"userID": "invalid", "access": {"user": {"library": True, "write": True}}},
        {},
    ],
)
def test_rejected_identity_leaves_configuration_unchanged(project, monkeypatch, payload):
    before = (project / "waterology.toml").read_bytes()
    identity(monkeypatch, payload)
    with pytest.raises(ValueError, match="Could not resolve"):
        zotero.initialize_zotero(project, "Fixture")
    assert not (project / ".zotero.toml").exists()
    assert (project / "waterology.toml").read_bytes() == before


def test_missing_key_is_actionable(project, monkeypatch):
    monkeypatch.delenv("ZOTERO_API_KEY", raising=False)
    result = CliRunner().invoke(app, ["zotero", "init", "Fixture", "--path", str(project)])
    assert result.exit_code != 0
    assert "ZOTERO_API_KEY" in result.output
    assert not (project / ".zotero.toml").exists()


def test_group_destination(project, monkeypatch):
    identity(
        monkeypatch,
        {
            "userID": 123,
            "access": {
                "groups": {"456": {"library": True, "write": True}},
            },
        },
    )
    settings = zotero.initialize_zotero(project, "Group", group_id="456")
    assert settings["library_type"] == "group"
    assert settings["library_id"] == "456"


def test_network_error_does_not_expose_key(project, monkeypatch):
    monkeypatch.setenv("ZOTERO_API_KEY", "private-fixture-key")

    class Opener:
        def open(self, *args, **kwargs):
            raise OSError("private-fixture-key")

    monkeypatch.setattr(zotero, "build_opener", lambda *args: Opener())
    result = CliRunner().invoke(app, ["zotero", "init", "Fixture", "--path", str(project)])
    assert result.exit_code != 0
    assert "private-fixture-key" not in result.output
    assert not (project / ".zotero.toml").exists()


def test_settings_follow_project_pointer_and_reject_missing_file(project):
    zotero.configure_zotero(project, {"library_id": "123", "collection_name": "Fixture"})
    (project / ".zotero.toml").rename(project / "custom.toml")
    path = project / "waterology.toml"
    path.write_text(path.read_text() + '\n[zotero]\nsettings_file = "custom.toml"\n')
    assert zotero.settings_for(project).library_id == "123"
    (project / "custom.toml").unlink()
    with pytest.raises(ValueError, match="missing"):
        zotero.settings_for(project)


def test_repeat_init_preserves_settings_comments(project, monkeypatch):
    identity(
        monkeypatch,
        {
            "userID": 123,
            "access": {"user": {"library": True, "write": True}},
        },
    )
    zotero.initialize_zotero(project, "Fixture")
    path = project / ".zotero.toml"
    path.write_text("# Retain settings comment\n" + path.read_text())
    before = path.read_bytes()
    zotero.initialize_zotero(project, "Fixture")
    assert path.read_bytes() == before


def test_init_rejects_symlink_settings(project, tmp_path):
    target = project / "target.toml"
    target.write_text(
        'library_id = "123"\ncollection_name = "Fixture"\ncollection_key = "ABCDEFGH"\n'
    )
    (project / ".zotero.toml").symlink_to(target)
    with pytest.raises(ValueError, match="symlink"):
        zotero.initialize_zotero(project, "Fixture")


def test_group_all_permissions(project, monkeypatch):
    identity(
        monkeypatch,
        {
            "userID": 123,
            "access": {
                "groups": {"all": {"library": True, "write": True}},
            },
        },
    )
    assert zotero.initialize_zotero(project, "Fixture", group_id="456")["library_id"] == "456"
