---
name: waterology-reports
description: >
  Default skill for creating, updating, or formatting technical, scientific,
  analysis, summary, and benchmark reports. Produces a self-contained, portable
  Markdown report bundle (`reports/<slug>-<YYYY-MM-DD>/`) with reproducible
  high-resolution figures, paired collapsible tables, and relative links unless
  an interactive HTML or LaTeX PDF format is explicitly requested.
---

<!-- Generated from skills/reports/SKILL.md. Do not edit. -->

# Reports (Standalone Markdown Report Bundle Default)

Use [writing-style](../waterology-writing-style/SKILL.md) for prose and Markdown delivery. Use this skill whenever asked to make, produce, create, or update an analysis, summary, or benchmark report (preserving an existing report's layout when extending one).

- If an **interactive HTML report** is explicitly requested, also read [interactive-reports.md](references/interactive-reports.md).
- If a **polished LaTeX PDF manuscript or white paper** is requested, use `rules/quarto-conventions.md` and [compile-latex](../waterology-compile-latex/SKILL.md).

---

## 1. Standalone Report Bundle Architecture

Place every technical, scientific, or benchmark report in `reports/<topic>-<YYYY-MM-DD>/`:

```text
reports/<topic>-<YYYY-MM-DD>/
├── <TOPIC>_REPORT.md           # Primary Markdown report
├── README.md                   # Synchronized copy of <TOPIC>_REPORT.md for Git folder rendering
├── <topic>_results.json        # Machine-readable single source of truth for metrics and series
├── COMPARISON_MODELS.md        # Optional companion reference for baseline equations and citations
└── figures/                    # 200-DPI Cairo PNG (or SVG) figures
    ├── fig1_<slug>.png
    └── ...
scripts/
└── plot_<topic>_figures.R      # Deterministic script regenerating figures from <topic>_results.json
```

1. **Single source of truth (`<topic>_results.json`):** Compute and save all metrics, tables, and diagnostic curves into `<topic>_results.json` (or `.yaml`), and read directly from it in plotting scripts (`scripts/plot_<topic>_figures.R` or `.py`) — never hardcode unverified numbers.
2. **Portable relative links:** Use relative paths (`figures/fig1_...png` and `../../src/...`) so the bundle works identically locally, on GitHub/GitLab, and in exports.
3. **Sync `README.md`:** Keep `README.md` identical to `<TOPIC>_REPORT.md` via `scripts/verify_report_bundle.py --sync-readme`.

---

## 2. Document Layout and Paired Collapsible Tables

Follow [`resources/report_template.md`](./resources/report_template.md):

1. **Header metadata block:** `# <Report Title>` followed by compact metadata lines (`**Date:**`, `**Primary Engine / Dataset:**`, `**Core Deliverables:**`).
2. **Executive summary:** Lead with 2 to 4 numbered findings linking to implementation files and headline metrics, separating observed results from interpretation and open work.
3. **1-to-1 pairing of numbered figures and collapsed `<details>` tables:**
   - Every table pairs with a sequentially numbered figure (`Figure 1` / `Table 1` .. `Figure N` / `Table N`).
   - Place the figure and caption first, followed immediately by its collapsed `<details>` table (no `open` attribute), using plain ASCII inside `<summary><strong>...</strong></summary>` (`R^2`, `RMSE`, `KGE`) and LaTeX math only inside captions/body:
     ```markdown
     ![Figure N: Concise Title]({{figures_dir}}/figN_descriptive_slug.png)
     **Figure N:** _(a) Panel A description. (b) Panel B description._

     <details>
     <summary><strong>Table N: Descriptive Table Title (Click to expand)</strong></summary>

     **Table N:** _Caption stating metrics, evaluation window, and sort key._

     | Method | Category | **Primary Metric (Sort Key)** | Secondary Metric |
     | :--- | :---: | :---: | :---: |
     | **`Method A`** | Proposed | **0.882** | 0.940 |

     </details>
     ```

---

## 3. Figure Design and Analytical Depth

Use [`resources/earth_tone_plot_template.R`](./resources/earth_tone_plot_template.R) and [figures](../waterology-figures/SKILL.md) (or [diagrams](../waterology-diagrams/SKILL.md) for conceptual TikZ flowcharts):

1. **Multi-panel 200-DPI figures with Earth-Tone palette:** Group related diagnostics into `(a)`, `(b)`, ... panels using Pine (`#2e6b4e`), Slate (`#3d6b82`), Ochre (`#c4842d`), Terracotta (`#b84a39`), Sage (`#6b9080`), Plum (`#7a5177`), Gold (`#d4a038`), Stone (`#8c857b`), and Charcoal (`#2b2b2b`).
2. **Bar-chart ordering:** Sort unordered categorical bars and paired table rows by the primary metric (`[Sort Key]`). For proposed-family (left) vs external-baseline (right) head-to-head charts split by a vertical red dashed line, sort the left side ascending (`Low -> High`) and the right side descending (`High -> Low`) so the strongest proposed and baseline methods meet at the divider.
3. **Visual inspection + mechanistic diagnostics:** Inspect every generated `.png` with `read_file` to confirm zero label collisions. Alongside aggregate scores (`RMSE`, `KGE`, `CRPS`, `F1`), include domain-appropriate physical, residual, regime, or horizon-decay diagnostics and proactively explain counterintuitive trade-offs using concise callouts (`> [!IMPORTANT]`, `> [!NOTE]`).

---

## 4. Verification

Run [`scripts/verify_report_bundle.py`](./scripts/verify_report_bundle.py) before finishing:

```sh
python3 <skill-directory>/scripts/verify_report_bundle.py path/to/reports/<topic>-<YYYY-MM-DD>/<TOPIC>_REPORT.md --sync-readme
```
