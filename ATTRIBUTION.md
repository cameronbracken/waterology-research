# Attribution

## ECC project learning adaptation, 2026-09-05

- Source: [affaan-m/ECC](https://github.com/affaan-m/ECC/tree/e04ea0b9cc8248686edf5ac751cadff550e162b8),
  commit `e04ea0b9cc8248686edf5ac751cadff550e162b8`.
- Adapted concepts: project-scoped atomic lessons, evidence retention and
  improvement proposals from `skills/continuous-learning-v2/SKILL.md`.
  Checkpoint guidance in `skills/strategic-compact/SKILL.md` informed additions
  to the existing session-log skill.
- Waterology files: `skills/project-learning/SKILL.md`, generated `commands/learn.md`,
  `core/learning.py` and the session-log checkpoint extension. Existing planning,
  review, research, retrieval and orchestration capabilities were retained.
- No ECC executable scripts, observer hooks or agent definitions were copied.

MIT License, copyright (c) 2026 Affaan Mustafa:

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

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
- **Pinned revisions:** `cb38a277840fd0ee0c0a6ea61ddc2bceb940efc6`
  (passport), `9d371f0bf8a8bc99569feca3210ef5133af28d33` (review and build tools)
- **License:** MIT — © 2026 Pedro H. C. Sant'Anna
- **Original paths:** `.claude/skills/audit-reproducibility/SKILL.md`,
  `.claude/hooks/claim-reconcile.py`, `templates/passport-template.yaml`,
  `.claude/agents/{r-reviewer,sim-reviewer}.md`,
  `.claude/rules/simulation-conventions.md`, and
  `.claude/skills/{simulation-study,capture-environment,compile-latex}/SKILL.md`.
- **What we adapt:** the reproducibility **passport**
  (`audit-reproducibility` skill, `passport.yaml` schema, and the
  `claim-reconcile.py` STALE detection hook). The portable version adds
  Fortran and fixed-width outputs, removes Stata specific material, and keeps
  the hook specific to the Claude plugin. The Monte Carlo trio
  (`simulation-study`, `sim-reviewer`, and simulation conventions), the
  `r-reviewer`, environment capture, and LaTeX compile workflow are also
  adapted. Stata, economic estimator examples, and product specific control
  flow are stripped. `r-package-check` was not ported.
- **Credit string:** *Adapted from pedrohcgs/claude-code-my-workflow (MIT,
  © 2026 Pedro H. C. Sant'Anna).*
- **Note:** Sant'Anna credits the "passport" concept itself to
  `Imbad0202/academic-research-skills` ("Material Passport") — carried forward.

### flonat/claude-research — reproducibility auditor + bibliography

- **Author:** Florian Burnat
- **Repo:** <https://github.com/flonat/claude-research>
- **Pinned revision:** `e7007d0b1e465ef96de7338599ca04079e83a972`
- **License:** MIT — © 2026 Florian Burnat
- **Original paths:** `.claude/agents/reproducibility-auditor.md`,
  `skills/pipeline-manifest/SKILL.md`, `skills/shared/overfull-boxes.md`,
  `rules/doi-verification.md`, and `rules/no-hardcoded-results.md`.
- **What we adapt:** the `reproducibility-auditor` and its 12-row checklist,
  pipeline traceability, bibliography and DOI validation through OpenAlex and
  Crossref, box-specific LaTeX diagnostics, and the no hardcoded results rule.
  The pinned tree no longer contains the roadmap's named `myst_to_quarto.py`,
  so Waterology implements that recorded conversion contract without copying
  unavailable source.
- **Credit string:** *Adapted from flonat/claude-research (MIT, © 2026 Florian
  Burnat).*

### companion-inc/feynman — research agents, skills, and workflows

- **Author:** Companion, Inc.
- **Repo:** <https://github.com/companion-inc/feynman>
- **Pinned revision:** `8ad8d5582fc5acb855fb83f972f0f3121d1aa423`
- **License:** MIT — © 2026 Companion, Inc. *(standalone `LICENSE` file present)*
- **Original paths:** `.feynman/agents/{researcher,reviewer,verifier,writer}.md`,
  `skills/*/SKILL.md`, and `prompts/{audit,autoresearch,compare,deepresearch,
  draft,lit,log,recipe,replicate,review,summarize,watch}.md`.
- **What we adapt:** the four research subagents (`researcher`, `writer`,
  `verifier`, `reviewer`), the general-research skills (`deep-research`,
  `literature-review`, `paper-writing`, `paper-narrative`, `paper-code-audit`,
  `research-review`, `source-comparison`, `figure-composer`, `figure-style`,
  `replication`, `pdf-explore`, `eli5`, `ml-training-recipe`, `session-log`,
  `watch`, `autoresearch`, `source-summarization`), and the matching
  slash-command workflows
  (`/deepresearch`, `/lit`, `/draft`, `/review`, `/audit`, `/compare`,
  `/replicate`, `/recipe`, `/autoresearch`, `/watch`, `/log`, `/summarize`).
  Feynman's tool names and product assumptions are replaced with capability
  descriptions that work in Claude Code, Codex, and OpenCode. Durable workflow
  behavior now lives in canonical skills.
  The `commands/` files are generated Claude compatibility shims.
  Computational biology model wrappers and Feynman
  product internal skills are dropped. Figures, papers, and examples are
  retargeted to the R, Quarto, hydrology, and energy stack.
- **Credit string:** *Adapted from Feynman (companion-inc/feynman, MIT).*

### alphaXiv/openresearch-cli — experiment tree + research-loop refinements

- **Author:** alphaXiv
- **Repo:** <https://github.com/alphaXiv/openresearch-cli>
- **Pinned revision:** `13049867497de8fd5e15253cd818462629edd690`
- **Replication revision:** `5412465c112b4f81033420db7ff7267ec88106c6`
- **License:** MIT *(declared in `Cargo.toml`; no standalone `LICENSE` file is
  present in the repo as of July 2026 — cited in good faith)*
- **Original paths:** `agent-skills/orx-agent-delegation/SKILL.md`,
  `agent-skills/orx-experiment-tree/SKILL.md`,
  `agent-skills/orx-lit-review/SKILL.md`, `SYSTEM_PROMPT.md`, and
  `src/local/skills.rs` at the replication revision.
- **What we adapt:** the portable delegation contract for independent task
  boundaries, standalone briefs, worktree ownership, explicit compute
  authorization, output paths, and return contracts; the experiment-tree
  discipline from the `orx` agent
  skills and system prompt (`skills/autoresearch/references/experiment-tree.md`
  and `/autoresearch`
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

### alphaXiv/OpenResearch - connected research workflow design

- **Repository:** <https://github.com/alphaXiv/OpenResearch>
- **Inspected revision:** `95b2d961966c128b27f9d49753e227791a01c909`
- **License:** MIT, Copyright (c) 2026 alphaXiv, verified in the current LICENSE.
- **Design references:** `agent-skills/orx-evidence/SKILL.md`,
  `agent-skills/orx-lit-review/SKILL.md`, `agent-skills/orx-reports/SKILL.md`,
  `agent-skills/orx-agent-delegation/SKILL.md` and `ui/src/components/`.
- **Use:** source comparison informed the connected study, evidence and report
  plan. New Python services and managed research/engineering contracts are
  original Waterology implementations. No upstream runtime code or UI assets
  are copied. Earlier adapted skill content retains its historical credit above.
- **Current difference:** OpenResearch now includes OpenAlex discovery. The
  arXiv-only rationale in the historical roadmap applies to the earlier snapshot.

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

### NatLabRockies/torc - managed execution integration

- **Organization:** National Laboratory of the Rockies
- **Repo:** <https://github.com/NatLabRockies/torc>
- **License:** BSD 3-Clause
- **What we use:** TORC is an optional external integration target. Waterology
  generates workflow specifications and invokes the public TORC CLI for local,
  remote worker, and Slurm execution. TORC retains responsibility for
  scheduling, workers, retries, resource accounting, its TUI, and its
  dashboard. No TORC source code is copied into this repository.
- **Credit string:** *Managed execution integrates with TORC
  (NatLabRockies/torc, BSD 3-Clause).*

## Original to this plugin

Fortran support (discovery globs, `gfortran` runner, reproducibility header,
conventions), the Quarto-as-document conventions, and all tuning to the
hydrology / energy-systems / extremes toolchain are original work.
