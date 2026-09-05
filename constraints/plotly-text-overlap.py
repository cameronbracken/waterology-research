#!/usr/bin/env python3
"""Fail when rendered Plotly widgets have predictable text collisions."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKER_PATH = ROOT / "skills/figure-style/scripts/check_plotly_layout.py"
SKIP_DIRS = {".git", ".pixi", ".venv", "__pycache__", "node_modules", "renv"}


def _load_checker():
    spec = importlib.util.spec_from_file_location("waterology_plotly_layout", CHECKER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {CHECKER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _html_files(targets: list[Path]) -> list[Path]:
    files = []
    for target in targets:
        if target.is_dir():
            files.extend(
                path
                for path in target.rglob("*")
                if path.is_file()
                and not SKIP_DIRS.intersection(path.parts)
                and path.suffix.lower() in {".html", ".htm"}
            )
        elif target.suffix.lower() in {".html", ".htm"}:
            files.append(target)
    return sorted(set(files))


def main() -> int:
    checker = _load_checker()
    targets = [Path(value) for value in sys.argv[1:]] or [Path.cwd()]
    records = []
    try:
        for path in _html_files(targets):
            records.extend(
                checker.layouts_from_text(path.read_text(encoding="utf-8"), source=path.as_posix())
            )
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"could not inspect Plotly layout: {exc}")
        return 1

    findings = checker.check_layouts(records)
    for finding in findings:
        print(f"{finding.code}: {finding.location}: {finding.message}")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
