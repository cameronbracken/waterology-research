from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "skills/figure-style/scripts/check_plotly_layout.py"
CONSTRAINT = ROOT / "constraints/plotly-text-overlap.py"
REPORT_FIGURE_CSS = ROOT / "skills/figure-style/assets/report-figure.css"


def _load_checker():
    spec = importlib.util.spec_from_file_location("check_plotly_layout", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _html(layout: dict) -> str:
    payload = {"x": {"layout": layout}, "evals": [], "jsHooks": {}}
    return (
        '<script type="application/json" data-for="htmlwidget-1">'
        + json.dumps(payload)
        + "</script>"
    )


def test_checker_finds_default_ggplotly_text_collision_risks() -> None:
    checker = _load_checker()
    layouts = checker.layouts_from_text(
        _html(
            {
                "title": {"text": "A long title inside the widget"},
                "legend": {"orientation": "h", "y": 1.02},
                "margin": {"t": 45, "b": 40, "l": 35, "r": 10},
                "xaxis": {"title": {"text": "Date"}},
                "yaxis": {"title": {"text": "Flow (m3/s)"}},
            }
        ),
        source="report.html",
    )

    findings = checker.check_layouts(layouts)
    assert {finding.code for finding in findings} == {
        "internal-title",
        "top-horizontal-legend",
        "axis-automargin",
    }
    assert {finding.location for finding in findings if finding.code == "axis-automargin"} == {
        "report.html#htmlwidget-1:xaxis",
        "report.html#htmlwidget-1:yaxis",
    }


def test_checker_accepts_separated_title_legend_and_axes() -> None:
    checker = _load_checker()
    layouts = checker.layouts_from_text(
        _html(
            {
                "legend": {
                    "orientation": "h",
                    "x": 0,
                    "y": -0.2,
                    "xanchor": "left",
                    "yanchor": "top",
                },
                "margin": {"t": 24, "b": 120, "l": 45, "r": 24},
                "xaxis": {"automargin": True, "title": {"text": "Date", "standoff": 12}},
                "yaxis": {
                    "automargin": True,
                    "title": {"text": "Flow (m3/s)", "standoff": 12},
                },
            }
        ),
        source="report.html",
    )

    assert checker.check_layouts(layouts) == []


def test_checker_rejects_an_underreserved_external_legend(tmp_path: Path) -> None:
    report = tmp_path / "report.html"
    report.write_text(
        _html(
            {
                "legend": {"orientation": "h", "x": 0, "y": -0.2},
                "margin": {"b": 40},
                "xaxis": {"automargin": True},
                "yaxis": {"automargin": True},
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(report)],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 1
    assert "bottom-legend-margin" in result.stdout


def test_constraint_rejects_hazardous_html_and_accepts_safe_html(tmp_path: Path) -> None:
    report = tmp_path / "report.html"
    hazardous = {
        "title": {"text": "Title"},
        "legend": {"orientation": "h", "y": 1.02},
        "xaxis": {"automargin": False},
    }
    report.write_text(_html(hazardous), encoding="utf-8")
    failed = subprocess.run(
        [sys.executable, str(CONSTRAINT), str(tmp_path)],
        capture_output=True,
        check=False,
        text=True,
    )
    assert failed.returncode == 1
    assert "internal-title" in failed.stdout

    safe = {
        "legend": {"orientation": "h", "y": -0.2},
        "margin": {"b": 100},
        "xaxis": {"automargin": True},
    }
    report.write_text(_html(safe), encoding="utf-8")
    passed = subprocess.run(
        [sys.executable, str(CONSTRAINT), str(tmp_path)],
        capture_output=True,
        check=False,
        text=True,
    )
    assert passed.returncode == 0
    assert passed.stdout == ""


def test_constraint_ignores_environment_html(tmp_path: Path) -> None:
    environment_html = tmp_path / ".pixi" / "site-packages" / "template.html"
    environment_html.parent.mkdir(parents=True)
    environment_html.write_text("{{ not_json }}", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(CONSTRAINT), str(tmp_path)],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0
    assert result.stdout == ""


def test_report_figure_css_uses_whitespace_instead_of_container_chrome() -> None:
    styles = REPORT_FIGURE_CSS.read_text(encoding="utf-8")

    assert "border: 0" in styles
    assert "border-radius: 0" in styles
    assert "box-shadow: none" in styles
    assert "background: transparent" in styles
    assert "overflow: visible" in styles
