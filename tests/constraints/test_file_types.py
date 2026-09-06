import json
import os
import subprocess
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

ROOT = Path(__file__).resolve().parents[2]


def scan(name, target):
    return subprocess.run(
        [sys.executable, str(ROOT / "constraints" / name), str(target)],
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize("direct", [True, False])
def test_parquet_mcse(tmp_path, direct):
    path = tmp_path / "simulation.PARQUET"
    pq.write_table(pa.table({"bias": [0.1], "coverage": [0.95]}), path)
    target = path if direct else tmp_path
    result = scan("mc-has-mcse.py", target)
    assert result.returncode == 1
    assert "bias, coverage" in result.stdout
    pq.write_table(pa.table({"bias": [0.1], "bias_mcse": [0.01]}), path)
    assert scan("mc-has-mcse.py", target).returncode == 0


def test_bad_parquet_fails(tmp_path):
    path = tmp_path / "mc-results.parquet"
    path.write_bytes(b"broken")
    result = scan("mc-has-mcse.py", path)
    assert result.returncode == 1
    assert "could not read" in result.stdout


def widget(layout):
    return (
        '<script type="application/json" data-for="htmlwidget-one">'
        + json.dumps({"x": {"layout": layout}})
        + "</script>"
    )


@pytest.mark.parametrize("suffix", [".Rmd", ".qmd"])
@pytest.mark.parametrize("direct", [True, False])
def test_source_requires_current_render_and_checks_layout(tmp_path, suffix, direct):
    source = tmp_path / ("report" + suffix)
    source.write_text("```{r}\nlibrary(plotly)\nplot_ly(x=1)\n```\n")
    target = source if direct else tmp_path
    result = scan("plotly-text-overlap.py", target)
    assert result.returncode == 1
    assert "render-required" in result.stdout
    html = source.with_suffix(".html")
    html.write_text(widget({"title": "Inside canvas"}))
    result = scan("plotly-text-overlap.py", target)
    assert result.returncode == 1
    assert "internal-title" in result.stdout
    html.write_text(widget({"xaxis": {"automargin": True}}))
    assert scan("plotly-text-overlap.py", target).returncode == 0
    os.utime(html, (1, 1))
    assert "stale-render" in scan("plotly-text-overlap.py", target).stdout


def test_quarto_output_configuration(tmp_path):
    source = tmp_path / "report.qmd"
    source.write_text("---\noutput-file: custom.html\n---\n```{python}\nimport plotly\n```\n")
    (tmp_path / "_quarto.yml").write_text("""project:
  output-dir: _site
""")
    output = tmp_path / "_site" / "custom.html"
    output.parent.mkdir()
    output.write_text(widget({}))
    assert scan("plotly-text-overlap.py", source).returncode == 0


def test_source_without_plotly_is_ignored(tmp_path):
    path = tmp_path / "notes.qmd"
    path.write_text("# Notes\n\nNo interactive figures here.\n")
    assert scan("plotly-text-overlap.py", tmp_path).returncode == 0


def test_plotly_source_without_widget_does_not_pass(tmp_path):
    path = tmp_path / "report.qmd"
    path.write_text("```{r}\nplotly::plot_ly(x=1)\n```\n")
    path.with_suffix(".html").write_text("<p>No widget</p>")
    assert "missing-layout" in scan("plotly-text-overlap.py", path).stdout


def test_python_plotly_html(tmp_path):
    source = tmp_path / "report.qmd"
    source.write_text("```{python}\nimport plotly.express as px\npx.scatter()\n```\n")
    source.with_suffix(".html").write_text(
        '<script>Plotly.newPlot("id", [], {"title":{"text":"Bad"}}, {});</script>'
    )
    result = scan("plotly-text-overlap.py", source)
    assert result.returncode == 1
    assert "internal-title" in result.stdout


def test_parquet_without_reader_fails_actionably(tmp_path):
    path = tmp_path / "simulation.parquet"
    pq.write_table(pa.table({"bias": [0.1]}), path)
    result = subprocess.run(
        [sys.executable, "-S", str(ROOT / "constraints/mc-has-mcse.py"), str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "requires pyarrow" in result.stdout


def test_scanners_skip_generated_files(tmp_path):
    generated = tmp_path / ".pixi"
    generated.mkdir()
    pq.write_table(pa.table({"bias": [0.1]}), generated / "simulation.parquet")
    (generated / "report.qmd").write_text("```{r}\nplotly::plot_ly(x=1)\n```\n")
    assert scan("mc-has-mcse.py", tmp_path).returncode == 0
    assert scan("plotly-text-overlap.py", tmp_path).returncode == 0
