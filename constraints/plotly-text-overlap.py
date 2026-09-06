#!/usr/bin/env python3
"""Fail when rendered Plotly widgets have predictable text collisions."""

from __future__ import annotations

import importlib.util
import json
import re
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


def _input_files(targets: list[Path]) -> list[Path]:
    files = []
    for target in targets:
        if target.is_dir():
            files.extend(
                path
                for path in target.rglob("*")
                if path.is_file()
                and not SKIP_DIRS.intersection(path.parts)
                and path.suffix.lower() in {".html", ".htm", ".rmd", ".qmd"}
            )
        elif target.suffix.lower() in {".html", ".htm", ".rmd", ".qmd"}:
            files.append(target)
    return sorted(set(files))


def _metadata(path: Path, *, frontmatter: bool = False) -> dict:
    import yaml

    text = path.read_text(encoding="utf-8")
    if frontmatter:
        match = re.match(r"\A---\s*\n(.*?)\n(?:---|\.\.\.)\s*(?:\n|$)", text, re.DOTALL)
        if not match:
            return {}
        text = match[1]
    try:
        value = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ValueError(f"{path}: invalid YAML: {exc}") from exc
    return value if isinstance(value, dict) else {}


def _rendered_file(path: Path) -> tuple[Path, list[Path]]:
    metadata = _metadata(path, frontmatter=True)
    dependencies = [path]
    root = path.parent
    output_dir = ""
    for parent in (path.parent, *path.parents[1:]):
        config = next(
            (
                parent / name
                for name in ("_quarto.yml", "_quarto.yaml")
                if (parent / name).is_file()
            ),
            None,
        )
        if config:
            project = _metadata(config).get("project", {})
            if isinstance(project, dict):
                output_dir = project.get("output-dir", "")
                if not output_dir:
                    output_dir = {"website": "_site", "book": "_book"}.get(project.get("type"), "")
            root = parent
            dependencies.append(config)
            break
    output = metadata.get("output-file", path.with_suffix(".html").name)
    if not isinstance(output, str) or not isinstance(output_dir, str):
        raise TypeError(f"{path}: output-file and output-dir must be strings")
    return root / output_dir / path.parent.relative_to(root) / output, dependencies


def _layouts(text, source, checker):
    records = checker.layouts_from_text(text, source=source)
    decoder = json.JSONDecoder()
    for index, match in enumerate(re.finditer(r"Plotly\.newPlot\s*\(", text)):
        remaining = text[match.end() :].lstrip()
        try:
            values = []
            for _ in range(3):
                value, end = decoder.raw_decode(remaining)
                values.append(value)
                remaining = remaining[end:].lstrip()
                if len(values) < 3:
                    if not remaining.startswith(","):
                        raise ValueError("expected comma")
                    remaining = remaining[1:].lstrip()
        except ValueError:
            # Calls using JavaScript variables require browser evaluation.
            continue
        if isinstance(values[2], dict):
            records.append(checker.LayoutRecord(f"{source}#plotly-{index}", values[2]))
    return records


def _source_records(path: Path, checker):
    text = path.read_text(encoding="utf-8")
    inline = _layouts(text, path.as_posix(), checker)
    # Detect Plotly code in executable chunks, not prose discussing Plotly.
    chunks = re.findall(
        r"^\s*(`{3,}|~{3,})\s*\{[^}]+\}[^\n]*\n(.*?)^\s*\1\s*$", text, re.MULTILINE | re.DOTALL
    )
    uses_plotly = any(re.search(r"\b(?:plotly|plot_ly|ggplotly)\b", code) for _, code in chunks)
    if not uses_plotly:
        return inline, []
    rendered, dependencies = _rendered_file(path)
    if not rendered.is_file():
        return inline, [f"render-required: {path}: render HTML to {rendered} before checking"]
    if any(dep.stat().st_mtime_ns > rendered.stat().st_mtime_ns for dep in dependencies):
        return inline, [f"stale-render: {path}: render {rendered} again before checking"]
    records = _layouts(rendered.read_text(encoding="utf-8"), rendered.as_posix(), checker)
    if not records:
        return inline, [f"missing-layout: {path}: no inspectable Plotly layouts in {rendered}"]
    return inline + records, []


def main() -> int:
    checker = _load_checker()
    targets = [Path(value) for value in sys.argv[1:]] or [Path.cwd()]
    records = []
    source_findings = []
    try:
        for path in _input_files(targets):
            if path.suffix.lower() in {".rmd", ".qmd"}:
                found, issues = _source_records(path, checker)
                records.extend(found)
                source_findings.extend(issues)
                continue
            records.extend(_layouts(path.read_text(encoding="utf-8"), path.as_posix(), checker))
    except (OSError, UnicodeError, ValueError, TypeError, ImportError) as exc:
        print(f"could not inspect Plotly layout: {exc}")
        return 1

    for issue in source_findings:
        print(issue)
    findings = checker.check_layouts(records)
    for finding in findings:
        print(f"{finding.code}: {finding.location}: {finding.message}")
    return 1 if findings or source_findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
