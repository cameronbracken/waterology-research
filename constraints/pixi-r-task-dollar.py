#!/usr/bin/env python3
"""Constraint check: R commands in pixi.toml tasks contain no ``$``.

See pixi-r-task-dollar.md for the rule. pixi runs tasks through
deno_task_shell, which expands ``$var`` even inside single quotes, silently
mangling R expressions like ``.Platform$path.sep``. Exits 0 (PASS) when
clean, 1 (FAIL) on a violation, 2 (ERROR) on internal problems.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", ".pixi", "renv"}
ALLOW_MARKER = "waterology: allow-task-dollar"

# [tasks], [tasks.name], [feature.<x>.tasks], [feature.<x>.tasks.name], ...
TASK_SECTION = re.compile(r"^\s*\[[^]]*\btasks\b[^]]*\]\s*(#.*)?$")
ANY_SECTION = re.compile(r"^\s*\[[^]]+\]")
R_INVOCATION = re.compile(r"\bRscript\b|\bR\s+--?[A-Za-z]|\br\s+-e\b|\bpixi run r\b")


def iter_pixi_tomls(targets: list[str]):
    for raw in targets:
        root = Path(raw)
        if root.is_file():
            if root.name == "pixi.toml":
                yield root
            continue
        for path in root.rglob("pixi.toml"):
            if not any(part in SKIP_DIRS for part in path.parts):
                yield path


def check_file(path: Path) -> list[str]:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        print(f"could not read {path}: {exc}", file=sys.stderr)
        return []
    findings = []
    in_tasks = False
    for lineno, line in enumerate(lines, start=1):
        if ANY_SECTION.match(line):
            in_tasks = bool(TASK_SECTION.match(line))
            continue
        if not in_tasks or ALLOW_MARKER in line:
            continue
        if "$" in line and R_INVOCATION.search(line):
            findings.append(f"{path}:{lineno}: R task command contains '$'")
    return findings


def main() -> int:
    targets = sys.argv[1:] or ["."]
    findings = [msg for path in iter_pixi_tomls(targets) for msg in check_file(path)]
    if findings:
        print(f"{len(findings)} R pixi task(s) with '$' (deno_task_shell expands it):")
        for finding in findings:
            print(f"  {finding}")
        print(
            'Use $-free R forms (.Platform[["path.sep"]]) or move the code '
            "to a script; mark intentional shell expansion with "
            "'# waterology: allow-task-dollar'."
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
