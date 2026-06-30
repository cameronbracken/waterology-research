#!/usr/bin/env python3
"""Constraint check: no machine-specific absolute paths in source.

See no-absolute-paths.md for the rule. Exits 0 (PASS) when clean, 1 (FAIL)
when any flagged path is found, 2 (ERROR) on an internal problem.

Adapted from edwinhu/workflows (MIT, per README); path patterns informed by
flonat/claude-research (MIT, (c) 2026 Florian Burnat).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SOURCE_SUFFIXES = {
    ".R", ".r", ".py", ".f90", ".f", ".F90", ".f95", ".qmd", ".Rmd", ".jl", ".do",
}
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "renv", "out"}
ALLOW_MARKER = "waterology: allow-abs-path"

# The pattern definitions below contain the very strings they look for, so they
# carry the documented escape marker to exempt this detector from itself.
PATTERNS = [
    (re.compile(r"/Users/[A-Za-z0-9._-]+"), "POSIX home path (/Users/...)"),  # waterology: allow-abs-path
    (re.compile(r"/home/[A-Za-z0-9._-]+"), "POSIX home path (/home/...)"),  # waterology: allow-abs-path
    (re.compile(r"(?<![\w/.])~/[A-Za-z0-9._-]"), "tilde home path (~/...)"),  # waterology: allow-abs-path
    (re.compile(r"[A-Za-z]:\\\\?[A-Za-z0-9._-]"), "Windows drive path (C:\\...)"),  # waterology: allow-abs-path
    (re.compile(r"CloudStorage/|/Dropbox/|/OneDrive/"), "cloud-storage root"),  # waterology: allow-abs-path
]


def iter_source_files(targets: list[str]):
    for raw in targets:
        root = Path(raw)
        if root.is_file():
            if root.suffix in SOURCE_SUFFIXES:
                yield root
            continue
        for path in root.rglob("*"):
            if path.is_dir():
                continue
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            if path.suffix in SOURCE_SUFFIXES:
                yield path


def scan_file(path: Path) -> list[str]:
    findings: list[str] = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"could not read {path}: {exc}", file=sys.stderr)
        return findings
    for lineno, line in enumerate(text.splitlines(), start=1):
        if ALLOW_MARKER in line:
            continue
        for pattern, label in PATTERNS:
            if pattern.search(line):
                findings.append(f"{path}:{lineno}: {label}  |  {line.strip()[:100]}")
                break
    return findings


def main() -> int:
    targets = sys.argv[1:] or ["."]
    all_findings: list[str] = []
    for path in iter_source_files(targets):
        all_findings.extend(scan_file(path))

    if all_findings:
        print(f"{len(all_findings)} machine-specific path(s) found:")
        for finding in all_findings:
            print(f"  {finding}")
        print("Use project-relative paths, or mark intentional lines with "
              "'# waterology: allow-abs-path'.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
