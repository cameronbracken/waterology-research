"""Portable Quarto bundles from explicit archived measurements."""

import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from waterology.core.atomic import write_json
from waterology.core.claims import list_claims, verify_claim
from waterology.core.comparison import compare_runs
from waterology.core.config import _portable_project_path
from waterology.core.project import discover_project

_RENDER_SCRIPT = '''"""Regenerate the report fragment from retained comparison data."""
import csv
import html
import json
from pathlib import Path

root = Path(__file__).resolve().parent
comparison = json.loads((root / 'comparison.json').read_text())
claims = json.loads((root / 'claims.json').read_text())
lines = ['| Run | Status | Metric | Unit | Value | Delta | Reason |',
         '| --- | --- | --- | --- | --- | --- | --- |']
def cell(value):
    return ''.join('&#' + str(ord(c)) + ';' for c in str(value).replace('\\n', ' '))
rows = []
for run in comparison['rows']:
    units = {r['name']: r['unit'] for r in (run.get('contract') or {}).get('metrics', [])}
    for name, value in (run['metrics'] or {'unavailable': None}).items():
        row = [run['run_id'], run['status'], name, units.get(name, ''),
               value, run['deltas'].get(name), run['reason'] or '']
        rows.append(row)
        lines.append('| ' + ' | '.join(cell(v) for v in row) + ' |')
with (root / 'measurements.csv').open('w', newline='') as stream:
    writer = csv.writer(stream)
    writer.writerow(['run', 'status', 'metric', 'unit', 'value', 'delta', 'reason'])
    writer.writerows(rows)
lines.extend(['', 'Claim evidence checks:', ''])
if not claims:
    lines.append('No claims registered.')
for claim in claims:
    lines.append('- ' + cell(claim['claim']['claim']) + ': ' + cell(claim['status']) + ' (reference integrity: ' + cell(claim['reference_status']) + ')')
(root / 'results.md').write_text('\\n'.join(lines) + '\\n')
try:
    import plotly.graph_objects as go
except ImportError:
    (root / 'figure.md').write_text('Interactive figure unavailable: install the reports extra. Measurements remain in the table.\\n')
else:
    sections = []
    for name in sorted({row[2] for row in rows if row[2] != 'unavailable'}):
        selected = [row for row in rows if row[2] == name and row[1] == 'verified']
        if not selected:
            continue
        fig = go.Figure(go.Bar(x=[row[0] for row in selected], y=[row[4] for row in selected], marker_color='#71816d'))
        fig.update_layout(template='plotly_white', yaxis_title=f'{name} ({selected[0][3]})',
                          margin=dict(t=30,b=100,l=70,r=30), height=440)
        fig.update_xaxes(automargin=True, title_standoff=12)
        fig.update_yaxes(automargin=True, title_standoff=12)
        sections.append(fig.to_html(full_html=False, include_plotlyjs=True))
    (root / 'figure.md').write_text('\\n'.join('```{=html}\\n' + section + '\\n```' for section in sections))
'''


def export_report(start: Path, run_ids: list[str], *, baseline: str, destination: str) -> dict:
    project = discover_project(start)
    relative = _portable_project_path(destination)
    parts = Path(relative).parts
    if parts[0].casefold() in {".waterology", ".git"} or any(
        part.rstrip(" .") != part for part in parts
    ):
        raise ValueError("Report exports must be outside repository control state")
    current = project.root
    for part in parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("Report destination must not traverse symlinks")
    target = project.root / relative
    if target.exists() or target.is_symlink() or not target.resolve().is_relative_to(project.root):
        raise ValueError("Report destination must be a new project directory")
    comparison = compare_runs(start, run_ids, baseline=baseline)
    claims = [verify_claim(start, c) for c in list_claims(start) if c.run_id in run_ids]
    complete = comparison["complete"] and all(c["status"] in {"PASS", "EXPLAINED"} for c in claims)
    target.parent.mkdir(parents=True, exist_ok=True)
    staged = Path(tempfile.mkdtemp(prefix=".waterology-report-", dir=target.parent))
    try:
        write_json(staged / "comparison.json", comparison)
        write_json(staged / "claims.json", {"claims": claims})
        # The render script expects a list, while write_json deliberately accepts objects.
        (staged / "claims.json").write_text(json.dumps(claims, indent=2) + "\n")
        (staged / "render.py").write_text(_RENDER_SCRIPT)
        (staged / "report.qmd").write_text("""---
title: "Experiment comparison"
format:
  html:
    embed-resources: true
    theme:
      light: flatly
      dark: darkly
---

The figures and table summarize the selected archived runs. Deltas are candidate
minus baseline. Unverified and incomparable runs remain visible in the table.
Numerical targets do not establish a scientific explanation.

{{< include figure.md >}}

{{< include results.md >}}

Only recorded uncertainty is available. No intervals are inferred from point
estimates. See `comparison.json` for evaluation contracts and archive identities.
""")
        (staged / "README.md").write_text("""# Regenerate this report

Run `python3 render.py`, then `quarto render report.qmd --to html`.
Install Waterology's reports extra for the interactive figure. The retained
CSV and table provide a static fallback. The bundle does not redistribute
research inputs. Archive checksums and contracts are recorded in provenance.json.
Re-export from the original project to refresh claim verification.
""")
        import sys

        subprocess.run([sys.executable, str(staged / "render.py")], check=True)
        files = {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in staged.iterdir()
            if p.is_file()
        }
        write_json(
            staged / "provenance.json",
            {
                "schema_version": 1,
                "baseline": baseline,
                "sources": [
                    {"run_id": r["run_id"], "archive_hash": r["source_hash"]}
                    for r in comparison["rows"]
                ],
                "files": files,
                "complete": complete,
                "render_status": "not_attempted",
            },
        )
        staged.replace(target)
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError):
        shutil.rmtree(staged)
        raise
    return {"path": relative, "complete": complete, "render_status": "not_attempted"}
