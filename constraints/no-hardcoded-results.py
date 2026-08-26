#!/usr/bin/env python3
"""Detect common hardcoded empirical result forms in TeX and Quarto prose."""

from __future__ import annotations

import re
import sys
from pathlib import Path

SKIP_DIRS = {".git", ".pixi", ".venv", "__pycache__", "node_modules", "renv", "out"}
ALLOW = "waterology: allow-hardcoded-result"
LAYOUT_PERCENT = re.compile(
    r"\b(?:fig-|min-|max-)?(?:width|height)\s*[:=]\s*[\"']?\d+(?:\.\d+)?\s*(?:%|\\%)",
    re.IGNORECASE,
)
PATTERNS = (
    re.compile(r"\b\d+(?:\.\d+)?\s*(?:%|\\%)"),
    re.compile(r"\bp\s*[<=>]\s*0?\.\d+", re.IGNORECASE),
    re.compile(r"\b[Nn]\s*=\s*\d+\b"),
)
DYNAMIC_CONSTRUCTS = (
    re.compile(r"\\input\{[^{}]*\}"),
    re.compile(r"\{\{<.*?>\}\}"),
    re.compile(r"`r\s+[^`]+`"),
)


def iter_documents(targets: list[str]):
    for raw in targets:
        target = Path(raw)
        paths = (target,) if target.is_file() else target.rglob("*")
        for path in paths:
            if path.suffix.lower() in {".tex", ".qmd"} and not any(
                part in SKIP_DIRS for part in path.parts
            ):
                yield path


def strip_layout_percent(line: str) -> str:
    stripped = line.lstrip()
    is_layout = (
        "![" in line
        or stripped.startswith(("<", "{"))
        or "\\includegraphics" in line
    )
    return LAYOUT_PERCENT.sub("", line) if is_layout else line


def findings(path: Path) -> list[str]:
    results: list[str] = []
    in_fence = False
    in_frontmatter = False
    for number, raw_line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        line = raw_line
        if (
            path.suffix.lower() == ".qmd"
            and line.strip() == "---"
            and (number == 1 or in_frontmatter)
        ):
            in_frontmatter = not in_frontmatter
            continue
        if in_frontmatter:
            continue
        if path.suffix.lower() == ".qmd" and line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or ALLOW in line:
            continue
        if path.suffix.lower() == ".tex":
            line = re.split(r"(?<!\\)%", line, maxsplit=1)[0]
        for construct in DYNAMIC_CONSTRUCTS:
            line = construct.sub("", line)
        line = strip_layout_percent(line)
        if any(pattern.search(line) for pattern in PATTERNS):
            results.append(f"{path}:{number}: {raw_line.strip()}")
    return results


def main() -> int:
    results = [item for path in iter_documents(sys.argv[1:] or ["."]) for item in findings(path)]
    if not results:
        return 0
    print(f"{len(results)} possible hardcoded result line(s):")
    for result in results:
        print(f"  {result}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
