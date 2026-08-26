#!/usr/bin/env python3
"""Fail on TeX overfull boxes of at least one point."""

from __future__ import annotations

import re
import sys
from pathlib import Path

SKIP_DIRS = {".git", ".pixi", ".venv", "__pycache__", "node_modules", "renv"}
OVERFULL = re.compile(r"Overfull \\[hv]box \(([0-9.]+)pt too (?:wide|high)\)(.*)")


def iter_logs(targets: list[str]):
    for raw in targets:
        target = Path(raw)
        paths = (target,) if target.is_file() else target.rglob("*.log")
        for path in paths:
            if not any(part in SKIP_DIRS for part in path.parts):
                yield path


def main() -> int:
    findings: list[str] = []
    for path in iter_logs(sys.argv[1:] or ["."]):
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in OVERFULL.finditer(text):
            width = float(match.group(1))
            if width < 1:
                continue
            severity = "major" if width > 10 else "minor"
            location = match.group(2).strip() or "location unavailable"
            findings.append(f"{path}: {severity}: {width:g} pt; {location}")
    if not findings:
        return 0
    print(f"{len(findings)} material overfull box(es):")
    for finding in findings:
        print(f"  {finding}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
