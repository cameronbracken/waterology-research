import pytest
from typer.testing import CliRunner

from waterology.cli import app
from waterology.core.user_settings import UserConfigError, load_user_config


def test_legacy_profile_and_dashboard_sections_are_ignored_cleanly(tmp_path):
    config = tmp_path / "config.toml"
    config.write_text(
        """trusted_profiles = ["local"]
[identity]
name = "Example Researcher"
email = "researcher@example.org"
[preferences]
files = ["preferences.md"]
[writing]
papers = ["https://doi.org/10.0000/example"]
[guidance]
figures = ["figures.md"]
[profiles.local]
mode = "local"
api_url = "http://localhost:8080"
[dashboard]
profile = "local"
"""
    )
    loaded = load_user_config(config)
    assert loaded.identity.email == "researcher@example.org"
    assert loaded.writing.papers == ("https://doi.org/10.0000/example",)
    assert loaded.preferences.files == ("preferences.md",)
    assert loaded.guidance["figures"] == ("figures.md",)


def test_config_init_and_path(tmp_path, monkeypatch):
    config = tmp_path / "config.toml"
    monkeypatch.setenv("WATEROLOGY_CONFIG", str(config))
    runner = CliRunner()

    path_result = runner.invoke(app, ["config", "path"])
    assert path_result.exit_code == 0
    assert path_result.output.strip() == str(config)

    init_result = runner.invoke(app, ["config", "init"])
    assert init_result.exit_code == 0, init_result.output
    loaded = load_user_config(config)
    assert loaded.identity.name == ""
    assert loaded.preferences.files == ()

    before = config.read_bytes()
    assert runner.invoke(app, ["config", "init"]).exit_code == 0
    assert config.read_bytes() == before


def test_invalid_settings_do_not_echo_values(tmp_path):
    config = tmp_path / "config.toml"
    config.write_text('[identity]\nemail = ["private-value"]\n')
    with pytest.raises(UserConfigError) as exc_info:
        load_user_config(config)
    assert "private-value" not in str(exc_info.value)


@pytest.mark.parametrize("runtime", ["claude", "opencode"])
@pytest.mark.parametrize("mode", ["copy", "link"])
def test_install_never_copies_personal_values_or_config_context_calls(
    tmp_path, monkeypatch, runtime, mode
):
    config = tmp_path / "config.toml"
    preferences = tmp_path / "private.md"
    preferences.write_text("Fictional private installation marker 3927")
    config.write_text('[preferences]\nfiles = ["private.md"]\n')
    monkeypatch.setenv("WATEROLOGY_CONFIG", str(config))
    target = tmp_path / "project"
    runner = CliRunner()
    result = runner.invoke(app, ["install", runtime, "--target", str(target), "--mode", mode])
    assert result.exit_code == 0, result.output
    skill_root = target / f".{runtime}" / "skills"
    assert "waterology config context" not in (skill_root / "writing-style/SKILL.md").read_text()
    for path in target.rglob("*"):
        if path.is_file():
            assert b"Fictional private installation marker 3927" not in path.read_bytes()
    if mode == "copy":
        assert not list(target.rglob("*.pyc"))
