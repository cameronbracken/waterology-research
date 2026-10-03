import math

import pytest

from waterology.core.atomic import dump_record, load_record, read_record, write_record


def test_records_round_trip_types_and_ambiguous_strings(tmp_path):
    payload = {
        "station": "00123",
        "country": "NO",
        "release": "1.10",
        "started_at": "2026-10-03T00:00:00Z",
        "empty": "",
        "missing": None,
        "count": 3,
        "rmse": 0.1 + 0.2,
        "passed": True,
        "command": ("python3", "model.py"),
        "nested": {"b": [1, {"c": "yes"}], "a": 1},
    }
    path = tmp_path / "record.yaml"
    write_record(path, payload)
    text = path.read_text()
    assert "{" not in text
    assert text.index("command:") < text.index("count:")
    assert read_record(path) == {**payload, "command": ["python3", "model.py"]}


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_records_reject_nonfinite_numbers(value):
    with pytest.raises(ValueError, match="NaN or infinite"):
        dump_record({"metric": value})


def test_invalid_record_raises_value_error():
    with pytest.raises(ValueError, match="Invalid YAML record"):
        load_record("key: [unclosed")
