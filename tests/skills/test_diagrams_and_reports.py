from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

from waterology.runtime.assets import AssetCatalog
from waterology.runtime.skills import load_skills

ROOT = Path(__file__).resolve().parents[2]
DIAGRAMS_SKILL = ROOT / "skills/diagrams/SKILL.md"
DIAGRAMS_STY = ROOT / "skills/diagrams/resources/flowchart-tikz.sty"
DIAGRAMS_CHECKER = ROOT / "skills/diagrams/scripts/check_tikz_svg.py"
REPORTS_SKILL = ROOT / "skills/reports/SKILL.md"
REPORTS_TEMPLATE = ROOT / "skills/reports/resources/report_template.md"
REPORTS_PLOT_TEMPLATE = ROOT / "skills/reports/resources/earth_tone_plot_template.R"
REPORTS_VERIFIER = ROOT / "skills/reports/scripts/verify_report_bundle.py"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_diagrams_skill_defaults_to_tikz_flowcharts_with_bundled_resources() -> None:
    text = DIAGRAMS_SKILL.read_text(encoding="utf-8")
    assert "TikZ" in text
    assert "resources/flowchart-tikz.sty" in text
    assert "scripts/check_tikz_svg.py" in text
    assert "references/integration-patterns.md" in text
    assert DIAGRAMS_STY.is_file()
    assert DIAGRAMS_CHECKER.is_file()


def test_reports_skill_defaults_to_markdown_bundle_with_bundled_resources() -> None:
    text = REPORTS_SKILL.read_text(encoding="utf-8")
    assert "reports/<topic>-<YYYY-MM-DD>/" in text
    assert "resources/report_template.md" in text
    assert "resources/earth_tone_plot_template.R" in text
    assert "scripts/verify_report_bundle.py" in text
    assert REPORTS_TEMPLATE.is_file()
    assert REPORTS_PLOT_TEMPLATE.is_file()
    assert REPORTS_VERIFIER.is_file()


def test_verify_report_bundle_accepts_valid_bundle_and_syncs_readme(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "reports" / "demo-2026-11-08"
    fig_dir = bundle_dir / "figures"
    fig_dir.mkdir(parents=True)
    (fig_dir / "fig1_demo.png").write_bytes(b"\x89PNG\r\n\x1a\nvalid")

    report_md = bundle_dir / "DEMO_REPORT.md"
    report_md.write_text(
        "# Demo Report (`demo-2026-11-08`)\n\n"
        "![Figure 1: Demo Figure](figures/fig1_demo.png)\n"
        "**Figure 1:** *(a) Panel A; (b) Panel B.*\n\n"
        "<details>\n"
        "<summary><strong>Table 1: Demo Table (Click to expand)</strong></summary>\n\n"
        "**Table 1:** *Demo caption.*\n\n"
        "| Method | Score |\n"
        "| :--- | :---: |\n"
        "| `A` | 0.95 |\n\n"
        "</details>\n",
        encoding="utf-8",
    )

    proc = subprocess.run(
        [sys.executable, str(REPORTS_VERIFIER), str(report_md), "--sync-readme"],
        capture_output=True,
        check=False,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert "[PASS]" in proc.stdout
    readme = bundle_dir / "README.md"
    assert readme.is_file()
    assert readme.read_text(encoding="utf-8") == report_md.read_text(encoding="utf-8")


def test_verify_report_bundle_rejects_unpaired_or_open_details(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "reports" / "bad-2026-11-08"
    bundle_dir.mkdir(parents=True)
    report_md = bundle_dir / "BAD_REPORT.md"
    report_md.write_text(
        "# Bad Report\n\n"
        "**Figure 1:** *Caption without table.*\n\n"
        "<details open>\n"
        "<summary><strong>Table 2: Raw $x$ math</strong></summary>\n\n"
        "**Table 2:** *Mismatched table.*\n"
        "</details>\n",
        encoding="utf-8",
    )

    proc = subprocess.run(
        [sys.executable, str(REPORTS_VERIFIER), str(report_md)],
        capture_output=True,
        check=False,
        text=True,
    )
    assert proc.returncode == 1
    assert "`<details open>`" in proc.stderr
    assert "contains raw LaTeX `$`" in proc.stderr


def test_check_tikz_svg_detects_overlapping_nodes_and_accepts_separated_nodes() -> None:
    checker = _load_module("check_tikz_svg", DIAGRAMS_CHECKER)

    good_svg = (
        '<svg xmlns="http://www.w3.org/2000/svg">'
        '<path fill="var(--m-res-fill)" stroke="var(--m-res-stroke)" d="M 0 0 L 40 0 L 40 20 L 0 20 Z"/>'
        '<path fill="var(--m-reach-fill)" stroke="var(--m-reach-stroke)" d="M 80 0 L 120 0 L 120 20 L 80 20 Z"/>'
        '<path fill="none" stroke="var(--m-line)" d="M 40 10 L 80 10"/>'
        "</svg>"
    )
    checker.check_tikz_svg_overlaps(good_svg, context_label="good")

    bad_svg = (
        '<svg xmlns="http://www.w3.org/2000/svg">'
        '<path fill="var(--m-res-fill)" stroke="var(--m-res-stroke)" d="M 0 0 L 40 0 L 40 20 L 0 20 Z"/>'
        '<path fill="var(--m-reach-fill)" stroke="var(--m-reach-stroke)" d="M 20 0 L 60 0 L 60 20 L 20 20 Z"/>'
        "</svg>"
    )
    try:
        checker.check_tikz_svg_overlaps(bad_svg, context_label="bad")
    except RuntimeError as exc:
        assert "overlaps" in str(exc)
    else:
        raise AssertionError("Expected overlap check to fail")


def test_skill_catalog_keeps_canonical_diagrams_and_reports_names() -> None:
    skills = {skill.name: skill for skill in load_skills(AssetCatalog.discover())}
    assert "diagrams" in skills
    assert "reports" in skills
