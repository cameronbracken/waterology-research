# Roadmap

### TODO: complete documentation site with examples

- [ ] Build a searchable documentation site with installation and upgrade guides,
  CLI and MCP reference, and runnable examples for experiments, managed studies,
  literature and Zotero workflows, project learning, and report exports. Include
  sample inputs, expected outputs, and troubleshooting. Check example commands
  and documentation links in CI.

### TODO: add explicit uninstall support

- [ ] Add an explicit uninstall command for each supported runtime and scope.
  Remove only files managed by Waterology, preserve user-owned configuration and
  data, support a dry run, and report anything that requires manual cleanup.
  Document and test install, upgrade, and uninstall round trips.

### TODO: detect and handle upgrades

- [ ] Before installing Waterology, detect an existing installation in the
  requested runtime and scope. If one exists, run the uninstall path before
  installing the new version. Remove only files managed by Waterology. Never
  delete or overwrite user configuration files. Test upgrades across supported
  versions, runtimes, and scopes, including interrupted upgrade recovery.

### TODO: evaluate alternatives to Pixi

- [ ] Compare practical alternatives to Pixi for development, testing, packaging,
  and contributor setup. Evaluate cross-platform support, reproducible locking,
  conda-forge and PyPI dependency handling, task execution, maintenance burden,
  and migration cost. Record whether Waterology should retain Pixi, supplement it,
  or replace it before changing the project environment.

### TODO: download papers through the browser

- [ ] Add a browser download fallback when direct HTTP or API requests hit bot
  protection, including for open-access papers. Open the publisher's paper page,
  use its PDF download controls, and support user handoff for interactive checks.
  Verify that the downloaded file is a PDF rather than a challenge page. Retain
  the source URL, DOI, retrieval time, and file hash, then connect the download to
  the literature record and Zotero attachment workflow.

### TODO: qualify expanded Zotero workflows

- [ ] Complete live account qualification for the optional Pyzotero integration,
  including library pagination, attachment upload and retry, and collection
  preservation. The read-only API smoke predates this integration. Offline SDK
  tests passed, but authenticated library writes and PDF uploads remain
  unverified. Evaluate local Zotero access only when a concrete workflow needs it.
  See the [validation record](docs/validation/2026-09-05-ecc-zotero.md) and
  [Pyzotero documentation](https://pyzotero.readthedocs.io/en/latest/).

## Research feature roadmap

The existing research roadmap follows. Each entry records upstream material,
what to port, and what to omit. Adapted work needs a file header and an
`ATTRIBUTION.md` entry.

### TODO: graded reproducibility conformance and claim anchors

Investigated 2026-09-20. Two candidate artifact formats were compared: the ARA
protocol from [XScientist](https://github.com/smileformylove/XScientist)
(arXiv [2607.12301](https://arxiv.org/abs/2607.12301), Apache-2.0) and
[RO-Crate](https://www.researchobject.org/ro-crate/) with its
[Workflow Run](https://www.researchobject.org/workflow-run-crate/) profiles.

Decision: do not adopt ARA as a storage format. It has one producer, one
author, and no independent consumers, and its agent layer is a modified fork of
AI-Scientist-v2 that we do not want. Adopt its design ideas internally and keep
RO-Crate as the export target, where the community, the validator, and the
archive integrations already exist. The two are complementary: RO-Crate
describes and packages, ARA grades and binds. Waterology already holds the
fixity layer that RO-Crate leaves to BagIt.

- [ ] __Conformance ladder.__ Give `archive verify` and the passport a named
  level instead of a single checksum verdict: `index` (records are present and
  schema valid), `trace` (every claim resolves to recorded evidence), `replay`
  (code, data, environment, seed and command suffice to rerun), `verify` (an
  independent check passed). Levels are one way and higher levels inherit lower
  blockers. A blocked level is a scientific gap to report, not a failure to
  retry. Extend `templates/passport.yaml` and `audit-reproducibility`.
- [ ] __Manuscript claim anchors.__ `ClaimRecord` already binds run, archive
  member, JSON pointer, member hash and value, which is stronger evidence
  binding than ARA carries. What is missing is the manuscript side: a no-op
  LaTeX macro and a Quarto shortcode that mark where a claim is asserted, so the
  passport reports coverage rather than inferring it. Write unresolved anchors
  with a resolved flag so intent stays visible. This turns `no-hardcoded-results`
  from a scanner into a binding.
- [ ] __Stdout metric marker.__ Accept a `WATEROLOGY_METRIC={...}` line, last
  match wins, alongside the declared `[[metrics]]` extractors. Extractors need
  per-project configuration and a parseable output file. A stdout marker works
  unchanged from R, Fortran and Python, which matters for mixed pipelines.
- [ ] __Seal state.__ Archives seal with `checksums.sha256`, which detects drift
  but cannot separate a later legitimate annotation from tampering. Record the
  seal hash and append post-seal edits, then report `clean`, `revised`,
  `tampered` or `unlocked` with distinct exit codes.
- [ ] __Typed run diff.__ `compare_archived_runs` reports metric deltas. Add the
  cause: which of code, environment, data or seed actually moved.
- [ ] __RO-Crate export.__ Emit a Workflow Run RO-Crate from a sealed archive so
  results are readable by Galaxy, Nextflow, WorkflowHub and Zenodo without
  Waterology. Validate with [rocrate-validator](https://github.com/crs4/rocrate-validator).
  [rocrateR](https://cran.r-project.org/package=rocrateR) covers the R side.

Not adopted from XScientist: the tree search over Python code nodes, the
LLM-authored manuscript pipeline, and the self-evolution and signed-promotion
stack. All assume one node equals one Python script and one metric equals one
scalar to maximize, which does not fit R, Fortran and Quarto work. Its
Docker-only executor boundary also conflicts with TORC and Slurm.

Worth keeping from its framing: ARA explicitly declines bit-for-bit
reproducibility and targets same claim, same code, comparable metric. That is
the honest standard for HPC output and a better promise for the passport.

### TODO: evaluate Workflow Run RO-Crate as the run provenance model

- [ ] Study the [Workflow Run RO-Crate](https://www.researchobject.org/workflow-run-crate/)
  working group output and decide which of its three profiles a sealed
  Waterology run should conform to. The
  [profile collection](https://www.researchobject.org/profiles) defines Process
  Run Crate, Workflow Crate and Provenance Crate at increasing granularity.
  Process Run Crate is implementable outside a workflow engine and is the likely
  starting point, since one sealed archive is one process execution. Specs are
  Apache-2.0 and examples are CC0. Reference paper: Leo et al. 2024, PLoS ONE
  19(9) e0309210, [doi:10.1371/journal.pone.0309210](https://doi.org/10.1371/journal.pone.0309210).
- [ ] Survey the existing implementations before designing anything. Each one
  publishes a Zenodo example crate, so the profiles can be read as emitted
  output rather than prose:
  - [Autosubmit](https://autosubmit.readthedocs.io/) 4.0.100+ (Workflow) is the
    closest analogue to our setup. It is the BSC HPC workflow manager for
    climate and Earth system models and it submits through Slurm, so it shows
    how a scheduler-backed run maps onto the model. Read this one first.
  - [runcrate](https://www.researchobject.org/runcrate/) 0.5.0+ (Provenance) is
    the reference implementation and CLI.
  - [COMPSs](https://github.com/bsc-wdc/compss) 3.4+, also BSC and HPC, emits
    either profile.
  - [Nextflow](https://github.com/nextflow-io/nf-prov) 1.4.0+, Galaxy 23.1.1+,
    [StreamFlow](https://streamflow.di.unito.it/),
    [WfExS](https://wfexs-backend.readthedocs.io/) and
    [Sapporo](https://github.com/sapporo-wes/sapporo) cover the rest.
- [ ] Check how far the profiles carry the things we already record: declared
  outputs, environment files and variable hashes, metric extraction, TORC
  workflow and job identifiers, redaction. Record what has no home in the model
  and would need a Waterology extension, and what we should drop because the
  standard covers it better.
- [ ] Decide where the fixity layer sits. RO-Crate leaves checksums to BagIt and
  the working group has no signing story yet, so our sealed archive stays the
  integrity source. Check whether the crate should live inside the archive or
  wrap it.
- [ ] Note the downstream reach before committing effort: the Workflow and
  Provenance profiles extend the
  [Workflow RO-Crate](https://w3id.org/workflowhub/workflow-ro-crate/) profile
  that [WorkflowHub](https://about.workflowhub.eu/developer/ro-crate-api/)
  accepts, and [Five Safes RO-Crate](https://w3id.org/5s-crate/) extends them
  again for sensitive-data environments. The
  [Galaxy training tutorial](https://training.galaxyproject.org/training-material/topics/fair/tutorials/ro-crate-workflow-run-ro-crate/tutorial.html)
  is the fastest introduction. The group runs biweekly meetings and a `#ro-crate`
  Slack channel if a TORC profile question needs an answer from them.


## Previous work:
## Managed workflow expansion

The [ECC/Zotero extension](docs/superpowers/plans/2026-09-05-ecc-learning-zotero.md)
adds project lesson assessment and retrieval, shared improvement proposals,
automatic reference capture and human-authored NestedText contracts. No
overlapping ECC agents or runtime hooks are imported.

The [implementation plan](docs/superpowers/plans/2026-09-05-openresearch-expansion.md)
and [user guide](docs/managed-studies.md) cover shared research/engineering
contracts, pinned TORC execution, bounded candidate sessions, archive comparisons,
claim assessments, recorded discovery, report bundles and connected views.
See the plan's validation record for completed checks and qualification limits.

## Platform roadmap

Each platform slice preserves a working Claude plugin and receives its own
implementation plan and review checkpoint.

- [x] **Slice 1: cross runtime foundation**

  Package Waterology for Claude Code, Codex, and OpenCode. Keep canonical root
  skills and agent definitions, generate runtime adapters, and preserve Claude
  compatibility commands.

- [x] **Slice 2: research methods**

  Move durable research workflows into runtime neutral skills, generate Claude
  compatibility commands, add portable delegation guidance and bounded source
  summarization, remove product assumptions, and complete pinned attribution.

- [x] **Slice 3: experiment core**

  Add project configuration, experiment trees, Git worktrees, direct execution,
  immutable archives, SQLite indexing, CLI JSON output, and index repair.


- [x] **Slice 4: TORC integration**

  Add TORC workflow generation, compute profiles, state reconciliation, remote
  confirmation, artifact collection, and TORC dashboard or TUI links.

- [x] **Slice 5: agent sessions and MCP**

  Add runtime process adapters, parallel worktree ownership, resume support,
  session logs, and the Waterology MCP server.

- [x] **Slice 6: research dashboard**

  Add the local research dashboard on the established service layer, including guarded actions,
  server rendered views, live summary events, theme support, and remote access controls.


## ✅ Slice 1 — Foundation + conventions (done 2026-06-29)

Manifests, LICENSE, ATTRIBUTION, README, CLAUDE.md, `check-all.py` runner,
constraints `no-absolute-paths` + `deterministic-seed`, rules for R / Python /
Fortran / Quarto-LaTeX, `project-conventions` entry-point skill. Runner tested.

## ✅ Slice 1.5 — session-mined skills and rules (done 2026-07-19)

Original workflow guidance, with personal context supplied by local configuration
(no attribution needed). Landed:

- `skills/setup-environment` — pixi-first scaffolding, rv/renv split, lockfile
  hygiene, and relocation pitfalls.
- `skills/publish-blog-post` — configured blog workflow, media preparation,
  content-type verification, and rendered-page checks.
- `rules/native-build-conventions.md` — parallel-safe Makevars, PKG_FFLAGS in
  explicit rules, stale-`.o` ABI hazard, `-ffp-contract=off` + configure
  probe, and CI guards.
- `rules/stan-conventions.md` — diagnostics order, full-warmup cost rule (the
  48x lesson), reparameterization levers, exploration-script pattern.
- `rules/r-conventions.md` gained a targets/crew debugging section.
- Constraint `pixi-r-task-dollar` — deno_task_shell expands `$` inside single
  quotes, so R one-liners in pixi tasks must avoid it.

Deferred candidates from the same mining pass: an upstream-sync skill (census
is a lower bound, diff classification is the worklist; revisit when multiple
projects need it), and
user-level habits (mdp review gates, SSH signing, ask-before-push) that stay
in global CLAUDE.md rather than the plugin.

## ✅ Slice 1.6 — research agents, skills, and workflows (done 2026-07-21)

**Source:** `companion-inc/feynman` (MIT, © 2026 Companion, Inc.). The general
research subset, retargeted to this stack. Landed:

- `agents/` — the four subagents `researcher`, `writer`, `verifier`, `reviewer`.
  Frontmatter converted to Claude Code (`name`/`description`/`tools`; dropped
  Feynman's `thinking`/`output`/`defaultProgress`). `reviewer` generalized from
  "AI research reviewer" to cover hydrology, extremes, and Monte Carlo artifacts
  (coverage-vs-estimate, dropped non-converged reps) — a lightweight cousin of
  the planned `sim-reviewer` (Slice 3), not a replacement.
- `commands/` — 12 slash workflows: `/deepresearch`, `/lit`, `/draft`,
  `/review`, `/audit`, `/compare`, `/replicate`, `/recipe`, `/autoresearch`,
  `/watch`, `/log`, `/summarize`. The repeated Feynman "Tool Discipline"
  preamble collapsed to a short tools note; `$@` -> `$ARGUMENTS`.
- `skills/` — 16 skills: 11 thin routers to their command plus 5 self-contained
  (`eli5`, `paper-narrative`, `figure-composer`, `figure-style`, `pdf-explore`).
  Figure skills retargeted to ggplot2 / patchwork / Okabe-Ito + viridis, light
  for print, vector output, and the `dataviz` skill.

**Remapped:** `web_search`->`WebSearch`/Exa, `fetch_content`->`WebFetch`,
alphaXiv `alpha_*`->Consensus MCP + OpenAlex/arXiv, `hf_*`->dropped, `subagent`
JSON->the `Task` tool, `schedule_prompt`->the `loop` skill / cron,
Modal/RunPod->Local / git branch / Pixi / SSH-Slurm.

**Stripped:** the ~15 computational-biology model wrappers (AlphaFold,
ProteinMPNN, Boltz, scGPT, Evo2, etc.) and the Feynman product-internal skills
(`self-awareness`, `product-self-knowledge`, `customize`, `contributing`, ...).

**Possible follow-ups:** a `paper-search`/OpenAlex helper shared with the
planned Slice 5 bib-validate path; wiring the `figure-style` provenance rule
(never hand-type a computed number) to the Slice 7 `no-hardcoded-results` check.

## ✅ Slice 1.7 — experiment tree + research-loop refinements (done 2026-07-22)

**Source:** `alphaXiv/openresearch-cli` (MIT per `Cargo.toml`, no LICENSE
file — cited in good faith). The portable prompt content only; the `orx` CLI,
its hosted API, compute backends, evidence DB, and marimo/molab publishing
were all dropped. Landed:

- `skills/autoresearch/references/experiment-tree.md` - Git experiment tree
  discipline for multi-round studies: frozen baseline, fixed run contract
  (vary committed code, never command flags or env vars), one branch for each hypothesis,
  "stacked bushes" shaping (fan within a round, descend onto the winner), no
  merge/rebase of branches with recorded results, refill/promote/stop
  decisions, and a provenance-first write-up section.
- `/autoresearch` gained a **tree mode** (linear stays the default); the
  skill router documents both shapes.
- `/lit` gained the multi-hop search protocol (build next-hop queries from
  each hop's citations, authors, and terminology until a hop surfaces
  nothing new), organize-by-theme synthesis, and a "start here" reading list.
- `/replicate` gained a claim ledger (paper result vs observed result,
  downscaling, compute cost), a fixed assessment vocabulary (`aligned` /
  `partially aligned` / `inconclusive under this setup` / `not attempted`),
  the divergence-language rule (quantify; never call the claim wrong), and
  an evidence-first report step.

**Skipped deliberately:** alphaXiv search itself (arXiv-only corpus — poor
hydrology/AGU coverage; Consensus + OpenAlex is better here), the
GPU-saturation wait loop (revisit if `/autoresearch` grows a parallel Slurm
mode), and `paper-to-marimo` (the interactive-tutorial idea could someday
translate to Quarto, but that is a new build, not a port).

## Slice 2 - Reproducibility passport (done 2026-08-25)

**Source:** `pedrohcgs/claude-code-my-workflow` (MIT, Copyright 2026 Pedro H.
C. Sant'Anna). The Material Passport concept remains credited to
`Imbad0202/academic-research-skills`.

Landed:

- `skills/audit-reproducibility/` provides a runtime neutral six phase audit.
  It extracts numeric manuscript claims, inspects current outputs, records
  match confidence, applies tolerances, and writes an evidence status report.
- `templates/passport.yaml` and the installed schema reference define the
  required source and output provenance fields, claim tolerances, audit
  dispositions, and lifecycle states.
- Defaults require exact counts, point estimate differences below 0.01,
  standard error differences below 0.05, the same p-value significance level,
  and percentage differences no larger than 0.1 percentage points. Claim
  overrides remain authoritative.
- `FAIL` blocks. `EXPLAINED` requires a concrete named alternative in the claim
  notes. `UNMATCHED`, `STALE`, and `UNVERIFIED` remain incomplete evidence.

Stata specific formats and estimator examples were removed. R, Python,
Fortran, `.dat`, `.csv`, fixed-width, and log outputs are covered. The skill
does not assume a dedicated monitoring tool. An authorized long rerun uses a
background process, a retained log, and polling.

## Slice 3 - Monte Carlo review (done 2026-08-26)

**Source:** `pedrohcgs/claude-code-my-workflow` (MIT).

Landed the canonical `r-reviewer` and `sim-reviewer` agents, the
`simulation-study` skill, simulation conventions, and the `mc-has-mcse`
constraint. The portable workflow derives truth from DGP parameters, assigns a
deterministic stream to each replication, reports MCSE, retains failed runs,
and saves raw results. DiD and TWFE examples were removed. Domain review now
covers hydrology, energy, statistics, units, and physical assumptions.

## Slice 4 - Reproducibility auditor and environment capture (done 2026-08-26)

**Sources:** `flonat/claude-research` (MIT, Copyright 2026 Florian Burnat) +
`pedrohcgs` `capture-environment`.

Landed a fresh context `reproducibility-auditor` with six dimensions, a 12-row
evidence checklist, and GREEN/YELLOW/RED verdicts. `capture-environment`
preserves the project's declared R and Python package managers. Its Fortran
path records compiler version, flags, linked libraries, architecture, and a
small qualification case. Missing runtimes, restricted inputs, and checks not
run remain UNVERIFIED.

## Slice 5 - Bibliography and DOI validation (done 2026-08-26)

**Source:** `flonat/claude-research` (MIT).

Landed `bib-validate`, its standard library validator, and the
`no-hallucinated-citations` rule. Local checks compare document keys with
BibTeX, classify edit distance 1 and 2 candidates, and restrict `--fix` to one
unambiguous citation key. Optional network checks use OpenAlex and Crossref.
DOI and metadata writes remain manual. Paid databases and Paperpile coupling
were removed.

## Slice 6 - Fortran pipeline tooling (done 2026-08-26)

The `pipeline-manifest` skill now maps scripts, inputs, outputs, build edges,
and document artifacts, including `.f90`, `.F90`, `.f95`, `.F95`, and `.f`.
It requires a topological run order and reports cycles, missing inputs,
duplicate producers, and orphans. The `run-all.sh` template includes Python,
R, and gfortran. The opt-in `conservation-tol` constraint checks project
evidence against a declared physical tolerance without assuming variable
names or units.

## Slice 7 - Quarto and LaTeX build helpers (done 2026-08-26)

**Sources:** `flonat/claude-research` + `pedrohcgs` (both MIT).

Landed the `myst-to-quarto` converter and skill, `compile-latex`, a reusable
latexmk configuration, the `overfull-boxes` constraint, and the
`no-hardcoded-results` convention and scanner. Conversion covers citations,
cross references, callouts, figures, and code fences. LaTeX verification uses
box-specific log parsing, not a generic warning count. The result scanner is
deliberately narrow and documents an explicit reviewed exception marker.

## Optional — phase gates (edwinhu pattern)

If workflows get heavier, add `hooks/phase-gate-guard.py`: a PreToolUse hook
matching `Write|Edit|Agent` that blocks until a `.planning/<GATE>_COMPLETE.md`
marker with `status: APPROVED` (containing the reviewer's actual output) exists.
Useful to gate analysis/plotting behind a data-validation phase. Adopt only if
the lightweight constraints prove insufficient — keep the plugin lean.
