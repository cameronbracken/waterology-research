"""YAML application outputs use the same extraction and replay contracts as JSON."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from waterology.core.config import (
    MetricExtractor,
    OutputCheck,
    ProjectConfig,
    load_project_config,
    project_config_toml,
)
from waterology.core.execution import MetricExtractionError, _extract_metrics
from waterology.core.reproduction import _compare


def yaml_config():
    return ProjectConfig(
        name="yaml-fixture",
        metrics=(
            MetricExtractor(name="rmse", path="metrics.yaml", format="yaml", field="scores.rmse"),
        ),
    )


def test_yaml_metric_and_replay_config_round_trip(tmp_path):
    config = yaml_config()
    path = tmp_path / "waterology.toml"
    path.write_text(project_config_toml(config))
    assert load_project_config(path).metrics == config.metrics
    check = OutputCheck(path="metrics.yml", mode="numeric", format="yaml", field="scores.rmse")
    assert OutputCheck.model_validate(check.model_dump()).format == "yaml"


def test_json_defaults_preserve_existing_output_check_serialization():
    check = OutputCheck(path="metrics.json", mode="numeric", field="scores.rmse")
    assert check.format == "json"
    assert "format" not in check.model_dump(mode="json")
    assert MetricExtractor(name="value", path="metrics.json", field="value").format == "json"


@pytest.mark.parametrize("mode", ["bytes", "statistical"])
def test_yaml_format_only_applies_to_numeric_output_checks(mode):
    kwargs = {"validator": "check"} if mode == "statistical" else {}
    with pytest.raises(ValidationError, match="numeric"):
        OutputCheck(path="metrics.yaml", mode=mode, format="yaml", **kwargs)


def test_nested_yaml_extraction_ignores_unrelated_metadata_types(tmp_path):
    (tmp_path / "metrics.yaml").write_text("date: 2026-09-29\nscores: \n  rmse: 1.25\n")
    assert _extract_metrics(yaml_config(), tmp_path, required=True) == {"rmse": 1.25}


@pytest.mark.parametrize(
    "text",
    [
        "scores: [broken",
        "scores: {}",
        "[]",
        "",
        "scores: \n  rmse: 1\n  rmse: 2\n",
        "scores: !!python/object:builtins.object {}",
        "scores: \n  rmse: 2026-09-29\n",
        "scores: {rmse: 1}\n---\nscores: {rmse: 2}\n",
    ],
)
def test_bad_yaml_retains_required_optional_extraction_behavior(tmp_path, text):
    (tmp_path / "metrics.yaml").write_text(text)
    with pytest.raises(MetricExtractionError, match="Unable to extract"):
        _extract_metrics(yaml_config(), tmp_path, required=True)
    assert _extract_metrics(yaml_config(), tmp_path, required=False) == {}


def test_yaml_extraction_does_not_follow_an_escaping_symlink(tmp_path):
    root = tmp_path / "worktree"
    root.mkdir()
    outside = tmp_path / "outside.yaml"
    outside.write_text("scores: {rmse: 1}\n")
    (root / "metrics.yaml").symlink_to(outside)
    with pytest.raises(MetricExtractionError, match="escapes"):
        _extract_metrics(yaml_config(), root, required=True)


def compare_files(tmp_path: Path, expected: str, observed: str, *, format="yaml", **kwargs):
    reference = tmp_path / "reference"
    actual = tmp_path / "actual"
    for root, content in [(reference, expected), (actual, observed)]:
        (root / "artifacts").mkdir(parents=True)
        (root / "artifacts/result").write_text(content)
    check = OutputCheck(path="result", mode="numeric", format=format, field="scores.rmse", **kwargs)
    return _compare(reference, actual, (check,))[0]


@pytest.mark.parametrize("format", ["json", "yaml"])
@pytest.mark.parametrize("observed,passed", [(1.0005, True), (1.01, False)])
def test_numeric_replay_uses_explicit_format_and_tolerance(tmp_path, format, observed, passed):
    encode = (
        (lambda value: json.dumps({"scores": {"rmse": value}}))
        if format == "json"
        else (lambda value: f"scores: \n  rmse: {value}\n")
    )
    result = compare_files(tmp_path, encode(1.0), encode(observed), format=format, atol=0.001)
    assert result["passed"] is passed


@pytest.mark.parametrize("value", ["true", ".nan", ".inf", "-.inf", "null", "'1.0'", "[]", "{}"])
def test_yaml_replay_does_not_coerce_or_accept_invalid_numeric_values(tmp_path, value):
    result = compare_files(tmp_path, "scores: {rmse: 1}\n", f"scores: {{rmse: {value}}}\n")
    assert not result["passed"]


@pytest.mark.parametrize(
    "content", ["broken: [", "scores: {}", "[]", "", "scores: \n  rmse: 1\n  rmse: 2\n"]
)
def test_yaml_replay_returns_failed_check_for_invalid_document(tmp_path, content):
    result = compare_files(tmp_path, "scores: {rmse: 1}\n", content)
    assert not result["passed"]


def test_yaml_replay_retains_failure_for_missing_reference(tmp_path):
    actual = tmp_path / "actual/artifacts"
    actual.mkdir(parents=True)
    (actual / "result.yaml").write_text("value: 1\n")
    check = OutputCheck(path="result.yaml", mode="numeric", format="yaml", field="value")
    result = _compare(tmp_path / "missing", tmp_path / "actual", (check,))
    assert not result[0]["passed"]


@pytest.mark.parametrize(
    "text",
    [
        "scores: {rmse: " + "[" * 600 + "0" + "]" * 600 + "}",
        "scores: &loop {rmse: *loop}",
    ],
    ids=["deep_nesting", "recursive_alias"],
)
def test_nested_yaml_failure_uses_normal_extraction_and_replay_outcomes(tmp_path, text):
    (tmp_path / "metrics.yaml").write_text(text)
    with pytest.raises(MetricExtractionError):
        _extract_metrics(yaml_config(), tmp_path, required=True)
    assert _extract_metrics(yaml_config(), tmp_path, required=False) == {}
    assert not compare_files(tmp_path, "scores: {rmse: 1}", text)["passed"]


def test_selected_yaml_mapping_must_match_archive_serialization(tmp_path):
    (tmp_path / "metrics.yaml").write_text("scores: {rmse: {a: 1, 2: 3}}")
    with pytest.raises(MetricExtractionError):
        _extract_metrics(yaml_config(), tmp_path, required=True)
    assert _extract_metrics(yaml_config(), tmp_path, required=False) == {}
