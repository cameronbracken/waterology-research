from pathlib import Path

import pytest
from pydantic import ValidationError

from waterology.core.config import ProjectConfig, load_project_config


def test_load_project_config_parses_portable_records(tmp_path: Path) -> None:
    path = tmp_path / "waterology.toml"
    path.write_text(
        """\
schema_version = 1
name = "flood-study"
artifact_roots = ["artifacts", "figures"]
command = ["pixi", "run", "analysis"]
environment_files = ["pixi.toml", "pixi.lock"]
outputs = ["results/metrics.json"]
default_compute_profile = "direct"

[concurrency]
max_runs = 2

[archive]
allow_missing_outputs = false
environment_allowlist = ["OMP_NUM_THREADS"]
log_redactions = ["token=[^\\\\s]+"]

[[metrics]]
name = "rmse"
path = "results/metrics.json"
format = "json"
field = "rmse"
""",
        encoding="utf-8",
    )

    config = load_project_config(path)

    assert config.name == "flood-study"
    assert config.command == ("pixi", "run", "analysis")
    assert config.concurrency.max_runs == 2
    assert config.archive.log_redactions == (r"token=[^\s]+",)
    assert config.metrics[0].field == "rmse"


def test_project_config_has_torc_compatible_default_memory() -> None:
    assert ProjectConfig(name="study").resources.memory_mb == 1024


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("artifact_roots", ["/tmp/results"]),
        ("environment_files", ["../pixi.toml"]),
        ("outputs", ["C:/results/output.csv"]),
    ],
)
def test_project_config_rejects_nonportable_paths(field: str, value: list[str]) -> None:
    data = {
        "schema_version": 1,
        "name": "study",
        "artifact_roots": ["artifacts"],
        "command": ["python3", "run.py"],
        "environment_files": [],
        "outputs": [],
        field: value,
    }

    with pytest.raises(ValidationError, match="relative project path"):
        ProjectConfig.model_validate(data)


def test_project_config_rejects_shell_command_string() -> None:
    with pytest.raises(ValidationError):
        ProjectConfig.model_validate(
            {
                "schema_version": 1,
                "name": "study",
                "artifact_roots": ["artifacts"],
                "command": "python3 run.py",
            }
        )


def test_project_config_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        ProjectConfig.model_validate(
            {
                "schema_version": 1,
                "name": "study",
                "artifact_roots": ["artifacts"],
                "command": [],
                "secret_token": "do-not-store-this",
            }
        )


def test_load_project_config_rejects_unsupported_schema(tmp_path: Path) -> None:
    path = tmp_path / "waterology.toml"
    path.write_text('schema_version = 2\nname = "future"\n', encoding="utf-8")

    with pytest.raises(ValidationError, match="Input should be 1"):
        load_project_config(path)


def test_project_config_rejects_invalid_log_redaction() -> None:
    with pytest.raises(ValidationError, match="invalid log redaction pattern"):
        ProjectConfig.model_validate(
            {
                "schema_version": 1,
                "name": "study",
                "archive": {"log_redactions": ["["]},
            }
        )


def test_legacy_configuration_keeps_its_execution_fingerprint_shape():
    # These are the fields included in saved pre-registry study execution hashes.
    expected = {
        "schema_version",
        "name",
        "artifact_roots",
        "command",
        "environment_files",
        "outputs",
        "default_compute_profile",
        "concurrency",
        "resources",
        "archive",
        "metrics",
    }
    assert set(ProjectConfig(name="legacy").model_dump(mode="json")) == expected
