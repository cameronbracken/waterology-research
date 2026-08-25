# Attribution

`waterology` is original work by Cameron Bracken, but its methodology and
several components are adapted from open-source Claude Code projects. This
ledger records what was borrowed and from whom. Files that derive from a
source carry a one-line credit at the top; this page is the canonical list.

## Sources

### edwinhu/workflows — methodology

- **Author:** Edwin Hu
- **Repo:** <https://github.com/edwinhu/workflows>
- **License:** MIT *(asserted in the project README; no standalone `LICENSE`
  file is present in the repo as of June 2026 — cited in good faith)*
- **What we adapt:** the `PHILOSOPHY.md` methodology — the
  *constraints-vs-conventions* distinction and its pass/fail litmus test, the
  paired `foo.md` + `foo.py` constraint pattern with an auto-discovering
  `check-all.py` runner, hook-enforced phase gates, independent verification
  (the implementer never reviews its own work), and "evidence over claims."
- **Credit string:** *Methodology adapted from Edwin Hu, "Workflow Philosophy,"
  edwinhu/workflows (MIT, per README).*

### pedrohcgs/claude-code-my-workflow — reproducibility + R/simulation

- **Author:** Pedro H. C. Sant'Anna
- **Repo:** <https://github.com/pedrohcgs/claude-code-my-workflow>
- **License:** MIT — © 2026 Pedro H. C. Sant'Anna
- **What we adapt (planned / in progress):** the reproducibility **passport**
  (`audit-reproducibility` skill, `passport.yaml` schema, `claim-reconcile.py`
  STALE-detection hook), the Monte Carlo trio (`simulation-study` +
  `sim-reviewer` + simulation conventions), the `r-reviewer` agent (esp. its
  numerical-discipline checks), `r-package-check` (CRAN `--as-cran` gate), and
  `capture-environment`. Stata- and econ-specific material is stripped.
- **Credit string:** *Adapted from pedrohcgs/claude-code-my-workflow (MIT,
  © 2026 Pedro H. C. Sant'Anna).*
- **Note:** Sant'Anna credits the "passport" concept itself to
  `Imbad0202/academic-research-skills` ("Material Passport") — carried forward.

### flonat/claude-research — reproducibility auditor + bibliography

- **Author:** Florian Burnat
- **Repo:** <https://github.com/flonat/claude-research>
- **License:** MIT — © 2026 Florian Burnat
- **What we adapt (planned / in progress):** the `reproducibility-auditor`
  agent and its 12-row PASS/FAIL checklist, bibliography / DOI validation via
  the free OpenAlex + Crossref path, the `myst_to_quarto.py` converter, LaTeX
  `latexmk` / overfull-box handling, and the `no-hardcoded-results` rule.
- **Credit string:** *Adapted from flonat/claude-research (MIT, © 2026 Florian
  Burnat).*

### companion-inc/feynman — research agents, skills, and workflows

- **Author:** Companion, Inc.
- **Repo:** <https://github.com/companion-inc/feynman>
- **License:** MIT — © 2026 Companion, Inc. *(standalone `LICENSE` file present)*
- **What we adapt:** the four research subagents (`researcher`, `writer`,
  `verifier`, `reviewer`), the general-research skills (`deep-research`,
  `literature-review`, `paper-writing`, `paper-narrative`, `paper-code-audit`,
  `research-review`, `source-comparison`, `figure-composer`, `figure-style`,
  `replication`, `pdf-explore`, `eli5`, `ml-training-recipe`, `session-log`,
  `watch`, `autoresearch`), and the matching slash-command workflows
  (`/deepresearch`, `/lit`, `/draft`, `/review`, `/audit`, `/compare`,
  `/replicate`, `/recipe`, `/autoresearch`, `/watch`, `/log`, `/summarize`).
  Feynman's tool names (`web_search`, `fetch_content`, alphaXiv `alpha_*`, the
  `subagent` dispatcher, Hugging Face `hf_*`) are remapped to Claude Code
  equivalents (`WebSearch`/`WebFetch`, the Consensus MCP + OpenAlex/arXiv, the
  `Task` tool); the computational-biology model wrappers and Feynman
  product-internal skills are dropped; figures, papers, and examples are
  retargeted to the R / Quarto / hydrology-energy stack.
- **Credit string:** *Adapted from Feynman (companion-inc/feynman, MIT).*

### alphaXiv/openresearch-cli — experiment tree + research-loop refinements

- **Author:** alphaXiv
- **Repo:** <https://github.com/alphaXiv/openresearch-cli>
- **License:** MIT *(declared in `Cargo.toml`; no standalone `LICENSE` file is
  present in the repo as of July 2026 — cited in good faith)*
- **What we adapt:** the experiment-tree discipline from the `orx` agent
  skills and system prompt (`rules/experiment-tree.md` and `/autoresearch`
  tree mode) — frozen baseline, fixed run contract, vary-code-not-knobs, one
  branch for each hypothesis, "stacked bushes" tree shaping, no merge or
  rebase of branches with recorded results; the multi-hop literature-search
  protocol from its `lit-review` template (in `/lit`); and the
  claim-by-claim replication ledger, fixed assessment vocabulary, careful
  divergence language, and evidence-first report layout from its
  `reproduce-paper` template (in `/replicate`). Everything coupled to the
  `orx` CLI, its hosted API, compute backends, evidence database, and the
  marimo/molab publishing path is dropped; branch mechanics are retargeted
  to plain git and the R / Stan / hydrology-energy stack.
- **Credit string:** *Adapted from openresearch-cli (alphaXiv/openresearch-cli,
  MIT per Cargo.toml).*

### William Strunk Jr. - concise prose principles

- **Author:** William Strunk Jr.
- **Source:** <https://www.gutenberg.org/ebooks/37134>
- **License:** Public domain in the United States, as recorded by Project
  Gutenberg.
- **What we adapt:** a compact summary of relevant composition principles in
  `skills/writing-style`. The complete book is not bundled.
- **Credit string:** *Prose principles adapted from William Strunk Jr., The
  Elements of Style (1918, public domain).*

### Cameron Bracken - published scientific voice

- **Author:** Cameron Bracken and coauthors
- **Sources:** <https://doi.org/10.1002/2015JD023205>,
  <https://doi.org/10.1016/j.renene.2023.119550>,
  <https://doi.org/10.1029/2024EF005313>, and
  <https://doi.org/10.1038/s41597-025-05097-3>
- **What we adapt:** an original analysis of recurring structure, claim
  calibration, quantitative scope, limitations, and reproducibility details in
  four first-author papers. No paper passages are copied. Collaborative and
  publisher editing limits any inference about sole-author style.
- **Credit string:** *Scientific prose guidance informed by an original
  analysis of Cameron Bracken's published work.*

### obra/superpowers - proportional software quality

- **Author:** Jesse Vincent
- **Repo:** <https://github.com/obra/superpowers>
- **Version:** 6.3.0
- **License:** MIT - Copyright (c) 2025 Jesse Vincent
- **What we adapt:** evidence-first debugging, focused regression testing,
  fresh verification before completion claims, risk-based independent review,
  and Git worktree safety from `systematic-debugging`,
  `test-driven-development`, `verification-before-completion`,
  `requesting-code-review`, and `using-git-worktrees`. Waterology replaces the
  mandatory ceremony with a proportional workflow and a clear worktree cutoff.
- **Credit string:** *Software quality guidance adapted from Superpowers 6.3.0
  (obra/superpowers, MIT).*

## Original to this plugin

Fortran support (discovery globs, `gfortran` runner, reproducibility header,
conventions), the Quarto-as-document conventions, and all tuning to the
hydrology / energy-systems / extremes toolchain are original work.
