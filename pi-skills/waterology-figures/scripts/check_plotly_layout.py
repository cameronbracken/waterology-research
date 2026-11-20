#!/usr/bin/env python3
"""Reject Plotly layouts with predictable text-collision risks."""

from __future__ import annotations

import argparse
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, NamedTuple

SKIP_DIRS = {".git", ".pixi", ".venv", "__pycache__", "node_modules", "renv"}


class LayoutRecord(NamedTuple):
    location: str
    layout: dict[str, Any]


class Finding(NamedTuple):
    code: str
    location: str
    message: str


class _HtmlWidgetParser(HTMLParser):
    def __init__(self, source: str) -> None:
        super().__init__(convert_charrefs=True)
        self.source = source
        self.current_id: str | None = None
        self.current_text: list[str] = []
        self.payloads: list[tuple[str, dict[str, Any]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if (
            tag == "script"
            and values.get("type") == "application/json"
            and values.get("data-for", "").startswith("htmlwidget-")
        ):
            self.current_id = values["data-for"]
            self.current_text = []

    def handle_data(self, data: str) -> None:
        if self.current_id is not None:
            self.current_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != "script" or self.current_id is None:
            return
        raw = "".join(self.current_text)
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON for {self.source}#{self.current_id}: {exc}") from exc
        self.payloads.append((self.current_id, payload))
        self.current_id = None
        self.current_text = []


def _payload_layout(payload: dict[str, Any]) -> dict[str, Any] | None:
    nested = payload.get("x")
    if isinstance(nested, dict) and isinstance(nested.get("layout"), dict):
        return nested["layout"]
    if isinstance(payload.get("layout"), dict):
        return payload["layout"]
    return None


def layouts_from_text(text: str, *, source: str) -> list[LayoutRecord]:
    if text.lstrip().startswith("{"):
        payload = json.loads(text)
        layout = _payload_layout(payload)
        return [] if layout is None else [LayoutRecord(source, layout)]

    parser = _HtmlWidgetParser(source)
    parser.feed(text)
    records = []
    for widget_id, payload in parser.payloads:
        layout = _payload_layout(payload)
        if layout is not None:
            records.append(LayoutRecord(f"{source}#{widget_id}", layout))
    return records


def _text(value: Any) -> str:
    if isinstance(value, dict):
        value = value.get("text", "")
    if value is None:
        return ""
    return re.sub(r"<[^>]+>", "", str(value)).strip()


def _number(value: Any, default: float) -> float:
    if isinstance(value, bool):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def check_layouts(records: list[LayoutRecord]) -> list[Finding]:
    findings = []
    for location, layout in records:
        if _text(layout.get("title")):
            findings.append(
                Finding(
                    "internal-title",
                    location,
                    "place the title or caption outside the interactive canvas",
                )
            )

        legend = layout.get("legend")
        margin = layout.get("margin") if isinstance(layout.get("margin"), dict) else {}
        if isinstance(legend, dict):
            orientation = legend.get("orientation", "v")
            legend_y = _number(legend.get("y"), 1.0)
            legend_x = _number(legend.get("x"), 1.0)
            if orientation == "h" and legend_y >= 0.9:
                findings.append(
                    Finding(
                        "top-horizontal-legend",
                        location,
                        "move the horizontal legend below the plotting domain",
                    )
                )
            if orientation == "h" and legend_y < 0 and _number(margin.get("b"), 0) < 80:
                findings.append(
                    Finding(
                        "bottom-legend-margin",
                        location,
                        "reserve at least 80 px below a horizontal legend",
                    )
                )
            if orientation != "h" and legend_x > 1 and _number(margin.get("r"), 0) < 120:
                findings.append(
                    Finding(
                        "right-legend-margin",
                        location,
                        "reserve at least 120 px beside an external vertical legend",
                    )
                )

        for axis_name, axis in layout.items():
            if not re.fullmatch(r"[xy]axis\d*", axis_name) or not isinstance(axis, dict):
                continue
            if axis.get("visible") is False:
                continue
            has_text = axis.get("showticklabels") is not False or bool(_text(axis.get("title")))
            if has_text and axis.get("automargin") is not True:
                findings.append(
                    Finding(
                        "axis-automargin",
                        f"{location}:{axis_name}",
                        "enable automargin for axes with tick labels or titles",
                    )
                )
    return findings


def _input_files(targets: list[Path]) -> list[Path]:
    files = []
    for target in targets:
        if target.is_dir():
            files.extend(
                path
                for path in target.rglob("*")
                if path.is_file()
                and not SKIP_DIRS.intersection(path.parts)
                and path.suffix.lower() in {".html", ".htm", ".json"}
            )
        else:
            files.append(target)
    return sorted(set(files))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check Plotly JSON or htmlwidget layouts for text-collision risks."
    )
    parser.add_argument("targets", nargs="+", type=Path)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    records = []
    try:
        for path in _input_files(args.targets):
            records.extend(
                layouts_from_text(path.read_text(encoding="utf-8"), source=path.as_posix())
            )
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    findings = check_layouts(records)
    if args.as_json:
        print(
            json.dumps(
                {
                    "layouts": len(records),
                    "findings": [finding._asdict() for finding in findings],
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        for finding in findings:
            print(f"{finding.code}: {finding.location}: {finding.message}")
        if not records:
            print("no Plotly layouts found")
        elif not findings:
            print(f"checked {len(records)} Plotly layout(s): no text-collision risks found")

    if not records or findings:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
