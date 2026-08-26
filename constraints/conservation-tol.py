#!/usr/bin/env python3
"""Check opt-in conservation evidence against its declared tolerance."""

from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

SKIP_DIRS = {".git", ".pixi", ".venv", "__pycache__", "node_modules", "renv"}
NAMES = {"conservation-check.json", "conservation-check.yaml", "conservation-check.yml"}
YAML_FIELD = re.compile(r"^\s*(metric|error|tolerance)\s*:\s*(.*?)\s*$")


def iter_evidence(targets: list[str]):
    for raw in targets:
        target = Path(raw)
        paths = (target,) if target.is_file() else target.rglob("*")
        for path in paths:
            if (
                path.is_file()
                and path.name in NAMES
                and not any(part in SKIP_DIRS for part in path.parts)
            ):
                yield path


def parse_simple_yaml(text: str) -> dict[str, object]:
    values: dict[str, object] = {}
    for line in text.splitlines():
        match = YAML_FIELD.match(line)
        if not match:
            continue
        name, raw = match.groups()
        values[name] = raw.strip("'\"") if name == "metric" else float(raw)
    return values


def parse_evidence(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    data = json.loads(text) if path.suffix == ".json" else parse_simple_yaml(text)
    if not isinstance(data, dict):
        raise TypeError("top level must be an object")
    return data


def check(path: Path) -> str | None:
    try:
        data = parse_evidence(path)
        metric = str(data["metric"])
        error = float(data["error"])
        tolerance = float(data["tolerance"])
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        return f"{path}: invalid conservation evidence: {exc}"
    if not metric.strip():
        return f"{path}: metric must not be empty"
    if not math.isfinite(error) or not math.isfinite(tolerance):
        return f"{path}: {metric} has a nonfinite error or tolerance"
    if tolerance <= 0:
        return f"{path}: {metric} tolerance must be positive"
    if abs(error) > tolerance:
        return f"{path}: {metric} error {error:g} exceeds tolerance {tolerance:g}"
    return None


def main() -> int:
    findings = [finding for path in iter_evidence(sys.argv[1:] or ["."]) if (finding := check(path))]
    if not findings:
        return 0
    print(f"{len(findings)} conservation check(s) failed:")
    for finding in findings:
        print(f"  {finding}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
