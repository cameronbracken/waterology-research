---
name: reports
description: >
  Default skill for creating, updating, or formatting technical, scientific,
  analysis, summary, and benchmark reports. Activate whenever the user asks to
  "make a report on x", "produce a report of x", "create a report on x",
  "write a report on x", "generate a report for x", or similar wording. Produces
  a self-contained, portable Markdown report bundle (`reports/<slug>-<YYYY-MM-DD>/`)
  with reproducible high-resolution publication figures, paired collapsible
  tables, and relative code/data links that can be shared as a standalone folder
  or rendered to PDF/HTML, unless the user explicitly requests an "interactive
  report" or another dedicated deliverable format. Distinct from brief notes
  and code documentation.
---

# Reports (Standalone Markdown Report Bundle Default)

Use [writing-style](../writing-style/SKILL.md) for prose. Read
[Markdown delivery](../writing-style/references/markdown-artifacts.md) for
Markdown output. Read optional local guidance with
`waterology config context reports`, or use the
[local resolver](../project-conventions/references/local-preferences.md).

Use this skill by default whenever the user asks to **make, produce, create, or
update a report**. Establish the question, audience, scope, and intended
decision from the request and project context, and preserve existing project
templates when extending an established report. Use
[interactive-reports](../interactive-reports/SKILL.md) when the user explicitly
requests an `"interactive report"` (standalone HTML with interactive graphics),
and use LaTeX (`rules/quarto-conventions.md`) when the user explicitly requests
a polished PDF manuscript or white paper.

---

## 1. Standalone Report Bundle Architecture

Every technical, scientific, or benchmark report lives in a self-contained
directory under `reports/<topic>-<YYYY-MM-DD>/` so it can be browsed on
GitHub/GitLab, shared as a standalone archive, or compiled directly to
PDF/HTML:

```text
reports/<topic>-<YYYY-MM-DD>/
├── <TOPIC>_REPORT.md           # Primary Markdown report
├── README.md                   # Exact copy of <TOPIC>_REPORT.md for automatic folder rendering
├── <topic>_results.json        # Machine-readable single source of truth for all metrics & series
├── COMPARISON_MODELS.md        # Optional companion reference for baseline/model math & citations
└── figures/                    # High-resolution 200-DPI Cairo PNG (or SVG) figures
    ├── fig1_<slug>.png
    ├── fig2_<slug>.png
    └── ...
scripts/
└── plot_<topic>_figures.R      # Deterministic script that regenerates all figures from <topic>_results.json
```

### Core Reproducibility Rules
1. **Single Source of Truth (`<topic>_results.json`):** Never hardcode unverified numbers in prose or plotting scripts. Compute and save all evaluation metrics, tables, and diagnostic curves into `<topic>_results.json`, and have the plotting script (`scripts/plot_<topic>_figures.R` or `.py`) read directly from that JSON.
2. **Portable Relative Links inside the Report:** Inside `<TOPIC>_REPORT.md`, use **relative links** (`figures/fig1_...png` for embedded images and `../../src/...` for source files) so the report renders identically in local Markdown previewers, Git web UIs, and PDF/HTML exports.
3. **Sync `README.md`:** Always copy `<TOPIC>_REPORT.md` to `README.md` inside the report bundle directory so opening the folder in a repository viewer displays the full report automatically.

---

## 2. Document Layout, Numbering, and Collapsible Table Pairing

Follow the structure template in [`resources/report_template.md`](./resources/report_template.md):

1. **Header Metadata Block:**
   Begin with `# <Report Title> (<run-id>)`, followed by compact metadata lines (`**Date:**`, `**Report ID:**`, `**Primary Simulator / Engine:**`, `**Core Deliverables:**`, `**Companion Reference Document:**`).
2. **Section 1 - Executive Summary:**
   Lead with findings. Summarize the 2-4 core contributions in a numbered list with bold lead-ins, clickable relative links to implementation files, and bold headline metrics. Distinguish completed work, observed results, interpretation, and remaining work.
3. **Strict 1-to-1 Pairing of Figures and Collapsible Tables:**
   - **Every table must be accompanied by a figure**, and **every figure and table must be sequentially numbered and captioned** (`Figure 1` / `Table 1` through `Figure N` / `Table N`).
   - Place the figure and its bold/italic caption first:
     ```markdown
     ![Figure N: Concise Title]({{figures_dir}}/figN_descriptive_slug.png)
     **Figure N:** *(a) Description of Panel A...; (b) Description of Panel B...*
     ```
   - Immediately follow the figure with its paired **collapsible table (collapsed by default)** using `<details>` **without** the `open` attribute:
     ```markdown
     <details>
     <summary><strong>Table N: Descriptive Table Title (Click to expand)</strong></summary>

     **Table N:** *Detailed caption explaining the metrics, evaluation window, and sorting key.*

     | Model / Method | Category | **Primary Metric (Sort Key)** | Secondary Metric |
     | :--- | :---: | :---: | :---: |
     | **`Method A`** | Family 1 | **0.8825** | 0.9396 |

     </details>
     ```
   - **Formatting rule for `<summary>`:** Keep text inside `<summary><strong>...</strong></summary>` plain text/ASCII (`R^2`, `KGE(Q)`, `J_multi`) rather than LaTeX `$...$` so HTML `<summary>` headers render cleanly across all Markdown engines. Use full LaTeX math (`$\text{KGE}(Q)$`, `$J_{\text{multi}}$`) inside the table body, captions, and prose.

---

## 3. Publication Figure Design and Ordering Conventions

Use the reusable R plotting template in [`resources/earth_tone_plot_template.R`](./resources/earth_tone_plot_template.R) (or equivalent Python/Matplotlib styling):

1. **Multi-Panel Cairo PNGs (`200 DPI`):**
   - Group related diagnostics into 2-panel (`1x2`, `width = 3100-3250, height = 1180-1250, res = 200, type = "cairo"`) or 4-panel (`2x2`, `width = 3100, height = 1850, res = 200`) figures with panel titles prefixed by `(a)`, `(b)`, `(c)`, `(d)`.
   - Use the **Earth-Tone Palette**:
     - Pine (`#2e6b4e`), Slate (`#3d6b82`), Ochre (`#c4842d`), Terracotta (`#b84a39`), Sage (`#6b9080`), Plum (`#7a5177`), Gold (`#d4a038`), Stone (`#8c857b`), Charcoal (`#2b2b2b`).
2. **Mandatory Bar-Chart Ordering Rules:**
   - **General Bar Charts (Single, Grouped, or Stacked):** Whenever categories do **not** have a fixed chronological, tier, or horizon axis, **sort the bars** by a primary bar metric (and annotate `[Sort Key]` in the legend or title). Order the paired Markdown table using the exact same sort key.
   - **Cross-Family Head-to-Head Bar Charts (Divided by a Vertical Red Dashed Line):**
     When comparing a proposed family (on the **left** of a vertical red dashed line) against external Statistical/ML and Literature baselines (on the **right** of the red line):
     - Order the **left side ascending (`Low -> High`)** by the primary metric;
     - Order the **right side descending (`High -> Low`)** by the primary metric.
     This forms a visual peak at the red divider line, placing the best proposed method and the best baseline method directly adjacent for immediate comparison.
3. **Direct Value Labels and Visual Inspection Gate:**
   - Annotate bars and heatmap cells with compact numeric values (`add_bar_labels`).
   - **Mandatory Visual Inspection:** After running the plotting script, always view the generated `.png` files with `read_file` to verify that no bar labels, axis labels, or legends collide or clip.

---

## 4. Analytical Depth and Scientific Rigor

1. **Answer Reviewer "Why" Questions Proactively:**
   - Include dedicated subsections and GitHub callout alerts (`> [!IMPORTANT]`, `> [!NOTE]`, `> [!TIP]`) explaining *why* counterintuitive results occur (for example, structural parameterization differences between synthetic and real regimes, horizon crossover between autoregressive ML and structural policies, or how objective function weights were normalized and allocated).
2. **Domain-Specific Physical Visuals:**
   - Alongside aggregate skill scores (`KGE`, `RMSE`, `F1`), include physical domain diagnostics such as recovered rule or guide curves across hydrologic tiers (`Dry`, `Normal`, `Wet`), 52-week operating-rule binding climatologies (`Week 1..52`), regime-shift operational signature timelines with permutation null scans, and re-initialization horizon decay curves (`1d -> 7d -> 30d -> Annual -> Open-Loop`).
3. **Separate Heavy Baseline Taxonomies into a Companion Doc:**
   - When comparing against many external models (`Stat/ML`, `Literature`, `Optimization Methods`), document the full mathematical equations, input feature vectors, and citations in a companion file (`COMPARISON_MODELS.md`) in the same report folder and link to it from the header.

---

## 5. Verification and Conditional Guidance

Before finishing any report bundle, run the verification script [`scripts/verify_report_bundle.py`](./scripts/verify_report_bundle.py) (resolved relative to this skill directory):

```sh
python3 <skill-directory>/scripts/verify_report_bundle.py path/to/reports/<topic>-<YYYY-MM-DD>/<TOPIC>_REPORT.md --sync-readme
```

The script verifies:
1. Sequential numbering and 1-to-1 pairing of `Figure 1..N` and `Table 1..N`;
2. Every table is wrapped in `<details>` (collapsed by default, no `open` attribute) with a `<summary><strong>Table N: ...</strong></summary>` header;
3. Every linked image file (`figures/fig*.png`) exists on disk and is non-empty;
4. `README.md` is synchronized with `<TOPIC>_REPORT.md`.

Load additional guidance only for work the report actually needs:

| Work requested | Additional skill or rule |
| --- | --- |
| Create or revise data figures | [data-visualization](../data-visualization/SKILL.md) |
| Create or revise conceptual diagrams | [diagrams](../diagrams/SKILL.md) |
| Interactive report | [interactive-reports](../interactive-reports/SKILL.md) |
| Quarto or LaTeX source | [document conventions](../../rules/quarto-conventions.md) |

Reusing a finished figure does not require its creation workflow. A brief note
or todo list uses [markdown-notes](../markdown-notes/SKILL.md); instructions that accompany code
use [documentation](../documentation/SKILL.md). Follow these alternatives only
when they describe the requested deliverable.
