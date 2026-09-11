import pytest
from typer.testing import CliRunner

from waterology.cli import app
from waterology.core.profiles import load_machine_config, trust_profile


def test_personal_settings_survive_profile_trust(tmp_path):
    config = tmp_path / "config.toml"
    config.write_text("""[identity]
name = "Example Researcher"
email = "researcher@example.org"
[preferences]
files = ["preferences.md"]
[writing]
papers = ["https://doi.org/10.0000/example"]
[guidance]
figure-style = ["figures.md"]
[profiles.local]
mode = "local"
api_url = "http://localhost:8080"
""")
    trust_profile(config, "local")
    loaded = load_machine_config(config)
    assert loaded.identity.email == "researcher@example.org"
    assert loaded.writing.papers == ("https://doi.org/10.0000/example",)
    assert loaded.preferences.files == ("preferences.md",)
    assert loaded.guidance["figure-style"] == ("figures.md",)


def test_context_uses_only_requested_guidance(tmp_path, monkeypatch):
    config = tmp_path / "config.toml"
    config.write_text("""[identity]
email = "researcher@example.org"
[preferences]
files = ["preferences.md"]
[writing]
files = ["writing.md"]
papers = ["https://doi.org/10.0000/example"]
[guidance]
figure-style = ["figures.md"]
""")
    for name in ("preferences", "writing", "figures"):
        (tmp_path / f"{name}.md").write_text(f"{name} instructions")
    monkeypatch.setenv("WATEROLOGY_CONFIG", str(config))
    runner = CliRunner()
    result = runner.invoke(app, ["config", "context", "writing-style"])
    assert result.exit_code == 0, result.output
    assert "preferences instructions" in result.output
    assert "writing instructions" in result.output
    assert "figures instructions" not in result.output
    assert "researcher@example.org" not in result.output
    assert "https://doi.org/10.0000/example" in result.output
    result = runner.invoke(app, ["config", "context", "figure-style"])
    assert result.exit_code == 0
    assert "figures instructions" in result.output
    assert "writing instructions" not in result.output


def test_empty_configuration_has_no_personal_defaults(tmp_path, monkeypatch):
    config = tmp_path / "config.toml"
    monkeypatch.setenv("WATEROLOGY_CONFIG", str(config))
    runner = CliRunner()
    assert runner.invoke(app, ["config", "context", "writing-style"]).exit_code == 0
    assert not config.exists()
    result = runner.invoke(app, ["config", "init"])
    assert result.exit_code == 0, result.output
    loaded = load_machine_config(config)
    assert loaded.identity.name == ""
    assert loaded.preferences.files == ()
    assert loaded.writing.papers == ()
    before = config.read_bytes()
    assert runner.invoke(app, ["config", "init"]).exit_code == 0
    assert config.read_bytes() == before


def test_missing_guidance_is_error_without_content_dump(tmp_path, monkeypatch):
    config = tmp_path / "config.toml"
    config.write_text('[preferences]\nfiles = ["missing.md"]\n')
    monkeypatch.setenv("WATEROLOGY_CONFIG", str(config))
    result = CliRunner().invoke(app, ["config", "context", "project-conventions"])
    assert result.exit_code == 1
    assert "Cannot read local guidance" in result.output


def test_invalid_settings_do_not_echo_values(tmp_path, monkeypatch):
    config = tmp_path / "config.toml"
    config.write_text('[identity]\nemail = ["private-value"]\n')
    monkeypatch.setenv("WATEROLOGY_CONFIG", str(config))
    result = CliRunner().invoke(app, ["config", "context", "project-conventions"])
    assert result.exit_code == 1
    assert "private-value" not in result.output


def test_dashboard_uses_profile_and_environment_without_printing_credentials(tmp_path, monkeypatch):
    import subprocess

    config = tmp_path / "config.toml"
    config.write_text("""[profiles.control]
mode = "local"
api_url = "http://localhost:8080/torc-service/v1"
[dashboard]
profile = "control"
llm_provider = "openai"
openai_base_url = "http://localhost:4000/v1"
openai_model = "example-model"
api_key_env = "EXAMPLE_LLM_KEY"
""")
    monkeypatch.setenv("WATEROLOGY_CONFIG", str(config))
    monkeypatch.setenv("EXAMPLE_LLM_KEY", "fixture-private-value")
    seen = []

    def fake_call(command, env):
        seen.append(command)
        assert env["OPENAI_API_KEY"] == "fixture-private-value"
        assert env["OPENAI_MODEL"] == "example-model"
        return 0

    monkeypatch.setattr(subprocess, "call", fake_call)
    runner = CliRunner()
    result = runner.invoke(app, ["config", "dashboard", "--dry-run"])
    assert result.exit_code == 0, result.output
    assert not seen
    result = runner.invoke(app, ["config", "dashboard"])
    assert result.exit_code == 0, result.output
    assert seen == [
        ["torc-dash", "--host", "127.0.0.1", "--api-url", "http://localhost:8080/torc-service/v1"]
    ]
    assert "fixture-private-value" not in result.output


@pytest.mark.parametrize("runtime", ["claude", "codex", "opencode"])
@pytest.mark.parametrize("mode", ["copy", "link"])
def test_install_includes_resolver_but_never_copies_personal_values(
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
    skill_root = target / (".agents" if runtime == "codex" else f".{runtime}") / "skills"
    assert "waterology config context" in (skill_root / "writing-style/SKILL.md").read_text()
    for path in target.rglob("*"):
        if path.is_file():
            assert b"Fictional private installation marker 3927" not in path.read_bytes()
    if mode == "copy":
        assert not list(target.rglob("*.pyc"))
    result = runner.invoke(app, ["config", "context", "writing-style"])
    assert "Fictional private installation marker 3927" in result.output
    preferences.write_text("Updated local instructions")
    assert (
        "Updated local instructions"
        in runner.invoke(app, ["config", "context", "writing-style"]).output
    )
    monkeypatch.setenv("WATEROLOGY_CONFIG", str(tmp_path / "other-user.toml"))
    result = runner.invoke(app, ["config", "context", "writing-style"])
    assert "Updated local instructions" not in result.output
