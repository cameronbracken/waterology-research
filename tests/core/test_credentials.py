import os

import pytest

from waterology.core.credentials import PROVIDER_VARIABLES, credentials_file_path, load_credentials

pytestmark = pytest.mark.skipif(os.name == "nt", reason="POSIX permission checks")


def _write(path, text, mode=0o600):
    path.write_text(text)
    path.chmod(mode)
    return path


def test_fills_only_missing_provider_keys(tmp_path):
    source = _write(
        tmp_path / "research.env",
        "export ZOTERO_API_KEY=from-file\nOPENALEX_API_KEY='quoted'\nUNRELATED=ignored\n",
    )
    environment = {"OPENALEX_API_KEY": "from-shell"}
    result = load_credentials(source, environment)
    assert environment == {"OPENALEX_API_KEY": "from-shell", "ZOTERO_API_KEY": "from-file"}
    assert result.loaded == ("ZOTERO_API_KEY",)
    assert result.problem is None
    assert "from-file" not in str(result.summary())


def test_skips_file_when_every_key_is_set(tmp_path):
    environment = {name: "set" for name in PROVIDER_VARIABLES.values()}
    result = load_credentials(tmp_path / "absent.env", environment)
    assert result.problem is None
    assert result.loaded == ()


def test_reports_missing_file(tmp_path):
    environment = {}
    result = load_credentials(tmp_path / "absent.env", environment)
    assert result.problem == "file not found"
    assert environment == {}


def test_rejects_file_readable_by_others(tmp_path):
    source = _write(tmp_path / "research.env", "ZOTERO_API_KEY=secret\n", mode=0o644)
    environment = {}
    result = load_credentials(source, environment)
    assert "chmod 600" in result.problem
    assert environment == {}


def test_path_comes_from_machine_config(tmp_path, monkeypatch):
    config = tmp_path / "config.toml"
    config.write_text('[credentials]\nfile = "secrets/research.env"\n')
    monkeypatch.setenv("WATEROLOGY_CONFIG", str(config))
    assert credentials_file_path() == tmp_path / "secrets" / "research.env"
    config.write_text('[credentials]\nfile = ""\n')
    assert credentials_file_path() is None


def test_invalid_machine_config_is_reported_not_raised(tmp_path, monkeypatch):
    config = tmp_path / "config.toml"
    config.write_text("[credentials]\nunknown = 1\n")
    monkeypatch.setenv("WATEROLOGY_CONFIG", str(config))
    result = load_credentials(environment={})
    assert result.path is None
    assert "Invalid machine configuration" in result.problem


def test_research_access_explains_missing_keys(tmp_path, monkeypatch):
    from waterology.core.research_access import research_access

    for name in PROVIDER_VARIABLES.values():
        monkeypatch.delenv(name, raising=False)
    load_credentials(tmp_path / "absent.env", {})
    result = research_access()
    assert result["credentials_file"]["problem"] == "file not found"
    assert any("do not inherit direnv" in warning for warning in result["warnings"])
    assert any(str(tmp_path / "absent.env") in warning for warning in result["warnings"])
