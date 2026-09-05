# OpenResearch functionality for Waterology

Status: implemented on `feature/managed-research-workflows`, with local
qualification completed on 2026-09-05. Remote execution and real unattended
model sessions remain unverified. See [usage](../../managed-studies.md) and
[validation evidence](../../validation/2026-09-05-managed-workflows.md).

The design and inspection notes below preserve the approved implementation
scope. The implementation uses shared core services with thin CLI, MCP and
dashboard adapters. Its remaining qualification limits are recorded explicitly
in the validation evidence rather than treated as completed acceptance checks.

Build a connected workflow around Waterology's existing experiment, execution,
and evidence services. First make autonomous execution consistent and resumable.
Then add trustworthy comparisons, research artifacts and workspace navigation.

## User refinement: autonomous research and engineering

The user needs unattended loops for scientific questions and for building models
or tools to meet a purpose, specification or resource constraint. Repeated
permission requests and changing execution methods defeat that purpose. TORC
must be the standard evaluation path for these managed loops, including local
compute. This requirement moves execution reliability ahead of comparison and
reporting features.

Use one durable loop engine with two explicit objective modes. Keep
`autoresearch` as the familiar entry point initially. A separate engineering
alias can be added later without creating a second controller or evidence store.

| Mode | Objective contract | Acceptance and stopping |
| --- | --- | --- |
| Research | Question, estimand, competing explanations, design, uncertainty and evidence needed | Stop on sufficient evidence or a declared limit. Negative or inconclusive findings are valid outcomes. A lower error alone does not establish a scientific explanation. |
| Engineering | Intended behavior, acceptance tests, hard constraints, adjustable components, performance target and regression limits | Establish feasibility first, then optimize the declared objective. Stop when the specification is met or a declared limit is reached. Retain the strongest feasible candidate. |

A study may contain both kinds of work. Give each phase its own objective and
acceptance contract while retaining shared execution and lineage. Record an
explicit transition instead of silently changing what success means. Tree
search and a numeric improvement objective are options, not universal rules.
Engineering can use cumulative implementation steps and multiple tests.

### Observed integration gaps

Source inspection on 2026-09-05 found:

- `skills/autoresearch/SKILL.md` requests an environment and describes raw
  local/SSH/Slurm choices, but does not route evaluations through Waterology or
  TORC. It lists a branch and a Pixi environment alongside execution targets,
  conflating source isolation, dependency setup and scheduling.
- `src/waterology/cli.py` resolves an omitted run profile from the project
  configuration. `services.start_run` and MCP `start_run` default to `direct`.
  Calling MCP without a profile can therefore bypass a configured TORC default.
- Remote profile trust already persists in machine configuration. This is host
  trust, not a complete authorization contract for a bounded autonomous loop.
- The skill asks for initial confirmation and asks resume versus fresh when
  files exist. Neither requires approval every iteration, but neither provides
  durable executable loop state that prevents redundant questions after resume.

These are source findings, not a reproduced diagnosis of past user sessions.

### Package 0: reliable managed loop execution

Implement this before package 1. Own shared profile resolution, a minimal durable
loop record, execution routing, focused tests and one autoresearch skill update.
Defer advanced candidate selection and parallel orchestration to package 5.

Before launch, resolve and save the objective mode, allowed edits, evaluation
command, environment identity, input identity, compute profile and resources,
concurrency, iteration/time budgets, retry limits, acceptance rules and stop
behavior. Separate allowed candidate configuration changes from the fixed
evaluation harness. Store a non-secret fingerprint of the resolved execution
configuration so a changed profile cannot silently redirect a resumed run.

Record authorization once for that scope, including authorization already given
in conversation. Continue iterations, bounded retries and unchanged resumes
without asking again. An extension of compute, budget, targets or allowed edits
requires new authority. Host trust is a prerequisite and is not loop authority.

Route every managed evaluation through one Waterology service using the pinned
TORC profile. CLI, MCP and dashboard must resolve defaults identically. Local
TORC and remote TORC use the same submission, status and artifact contract.
Never fall back to direct execution, ad hoc SSH, a different host or a different
environment when TORC fails. Retry within the declared policy or persist a
blocked state with the exact recovery action. Retain explicit direct execution
for separately configured workflows outside this managed-loop contract.

Separate editing and lightweight local validation from candidate evaluation.
Declare which checks may run locally and their resource limits. Performance
measurements and acceptance evaluations must use the pinned execution path.
Agents propose changes and inspect evidence. The controller owns submission,
budget accounting, retry handling, result collection and checkpoint transitions.

Save submission intent before contacting TORC and reconcile ambiguous outcomes
before retrying. Persist job IDs and distinguish failed jobs from unavailable
status. Resume only after checking active jobs and archive identity. Count
retries against their own cap and all compute against applicable total budgets.
Specify whether a stop drains or cancels active jobs. Neither mode launches new
work after a stop request.

This contract does not bypass runtime sandbox or tool approval policies. Check
the actual unattended launch path before starting, and report an incompatible
permission setup at preflight rather than promising uninterrupted operation.
Do not grant broad machine access as a shortcut to managed execution.

Exit: regression tests cover omitted-profile parity across interfaces, explicit
overrides outside managed loops, rejection of overrides inside a pinned loop,
unchanged authorized resume, changed profile detection, bounded retries, TORC
unavailability without fallback, and crash recovery without duplicate launch.
Run a short local TORC loop through multiple iterations and a controller restart.
Verify every evaluation has the expected profile, command and artifact record.
Test remote execution separately on a selected, authorized host before claiming
remote unattended readiness. Skill wording checks alone cannot prove routing or
absence of interactive prompts.

## Inspection basis

Inspected on 2026-09-05:

- Waterology: `ce2699fc1dd487e55dd3cbe86a154c71414e855c`.
- [OpenResearch](https://github.com/alphaXiv/OpenResearch/tree/95b2d961966c128b27f9d49753e227791a01c909):
  `95b2d961966c128b27f9d49753e227791a01c909`.
- Upstream code and instructions were read, not executed. Feature presence does
  not establish reliability or cross-platform operation.
- Waterology's [roadmap](../../../ROADMAP.md) records the platform slices as
  complete. The repository AGENTS scope paragraph still calls them later work.
  Reconcile that wording when implementing a platform extension.

The current upstream [LICENSE](https://github.com/alphaXiv/OpenResearch/blob/95b2d961966c128b27f9d49753e227791a01c909/LICENSE)
is MIT, copyright 2026 alphaXiv. Preserve historical attribution for earlier
adaptations. Add a separate pinned entry and file headers when adapting new
instructions or code. This proposal links sources without copying their code.

## Capability inventory

Paths in the upstream column are relative to the pinned OpenResearch revision.
Waterology paths refer to the inspected revision. Gaps are conclusions from
source inspection, not results of runtime comparison tests.

| Capability | Upstream evidence | Waterology today | Proposed treatment |
| --- | --- | --- | --- |
| Experiment lineage and frozen runs | `agent-skills/orx-experiment-tree/SKILL.md`, `src/local/experiments.rs` | `core/experiments.py`, `core/archive.py`, tree skill and assessment tests | Extend existing services. Do not rebuild the tree or archive store. |
| Evidence inspection | `agent-skills/orx-evidence/SKILL.md` | `core/evidence.py`, `EvidenceRecord`, run metrics and assessments | Add structured measurement and immutable claim references. Logs supplement archived data. |
| Literature discovery | `agent-skills/orx-lit-review/SKILL.md`, `src/commands/discover.rs` | Literature skills and bibliography validation, no discovery CLI/MCP entry in inspected interfaces | Add a reusable search record and provider interface. Start with OpenAlex and DOI resolution. |
| Paper and report artifacts | `agent-skills/orx-paper/SKILL.md`, `agent-skills/orx-reports/SKILL.md` | Quarto report instructions, passports, figure rules, artifact registration | Generate reports from explicit run selections and evidence manifests. |
| Tree, files, artifacts and diffs in one workspace | `ui/src/components/{TreeView,ArtifactsTab,BranchChanges,FileViewer}.tsx` | Dashboard lists experiments, artifacts, sessions, archived metrics and logs | Add linked tree and comparison views on existing services. |
| Agent conversations and model selection | `ui/src/components/{ChatPanel,ModelPicker,SubagentTab}.tsx`, `src/local/harness/` | Three runtime adapters, supervised attempts, native resume, owned worktrees | Add bounded study orchestration first. Defer embedded chat until it solves a demonstrated workflow need. |
| Remote execution | `src/jobs/`, `agent-skills/orx-compute/` | Direct execution plus TORC providers and reconciliation | Keep TORC responsible for scheduling. Improve study-level status and recovery. |
| Project creation | `agent-skills/orx-create/SKILL.md` | Project init, experiment creation, environment skills | Add a small optional study scaffold after its record format stabilizes. |
| Figure recipes | `agent-skills/orx-figures/` | Figure composer, style rules and Plotly layout checks | Add recipes only for an unmet use case, such as uncertainty and paired site comparisons. |
| Desktop distribution, hosted compute, Overleaf, analytics | `macos/`, `src/jobs/openresearch.rs`, `ui/src/components/OverleafPanel.tsx`, `src/commands/telemetry.rs` | Python CLI, runtime plugins, local dashboard and Quarto | Defer. No demonstrated need for a second scheduler, desktop wrapper or hosted account. |

Waterology source modules above live under `src/waterology/`.

The old arXiv-only explanation in ROADMAP Slice 1.7 describes an earlier
upstream snapshot. Current OpenResearch includes OpenAlex discovery and a
bioRxiv path through OpenAlex. Preserve the historical entry and record this
change explicitly. Choose sources for journal, agency, data and software
coverage relevant to hydrology and energy. Do not make popularity a proxy for
scientific support.

## Waterology behavior

Keep the CLI and portable artifacts useful without a dashboard. Use Python,
R and Quarto with the project's existing environment manager. Local execution
is sufficient for all initial acceptance cases.

An experiment needs a scientific question as well as a command: estimand,
baseline, input identities, evaluation sites and periods, units, seeds,
uncertainty method, allowed changes and stop conditions. Distinguish
reconstruction, conditional hindcast, free run and forecast. These fields are
Waterology additions, not claims about upstream behavior.

A completed process is an operational outcome. Scientific validity, claim
support and usefulness remain separate. Keep failed and unfavorable runs.
Do not rank incomparable protocols, change a frozen test set, or turn missing
evidence into a successful assessment. Domain fields are required when
applicable, with an explicit reason when a field is not applicable.

Existing authorization persists within its stated scope. Store the authorized
compute, concurrency and stopping limits once. Ask again only when the next
action exceeds them. Selection of an experimental candidate does not authorize
publication, production deployment, deletion or an expanded compute budget.

## Ordered implementation packages

### 1. Study contracts and comparable measurements

Own new contract/comparison modules, related records and focused core tests.
Extend `core/config.py`, `core/records.py`, `core/archive.py` and `services.py`
only where needed. Expose the result through CLI and MCP before the dashboard.

Define a versioned study contract and fingerprint. Record baseline, estimand,
data hashes or immutable accession versions, split/site/period definitions,
units, seeds, metric direction, uncertainty method and promotion rule. Keep
fixed evaluation identity separate from the allowed candidate configuration.
Existing runs without these fields remain readable and explicitly lack a
verified comparison contract. Never infer one from a matching metric name.

Create a comparison export from selected sealed archives. Preserve every
requested run, its validity, missing values and exclusion reasons. Compute
deltas only for compatible measurements. Record confidence intervals or MCSE
only when the declared method and available replicates support them.

Exit: fixtures cover a valid paired comparison, mismatched units, changed
evaluation data, changed candidate configuration allowed by the contract,
missing metrics, failed runs, legacy records and archive tampering. Equivalent
CLI and MCP requests return the same result. Export hashes identify inputs.

### 2. Claims tied to immutable evidence

Depends on package 1. Own evidence records, evidence services, index repair,
passport integration and their tests.

Today `EvidenceRecord` stores claim text, kind, an optional path, and optional
run/session IDs. Extend this with a versioned reference to an archive member,
content hash and selector, such as a table row and column or a JSON pointer.
Keep observation, inference and proposed analysis distinguishable. Preserve
contradictory evidence and append assessments rather than overwriting history.

Reuse the passport's status vocabulary through an explicit mapping. Do not
invent an incompatible second set of audit states. Mutable working files
must be snapshotted or clearly marked as unsealed evidence. An existing path
alone does not verify a number or prove it came from a particular run.

Exit: test changed content, missing selectors, wrong run associations,
contradictory support, legacy evidence and repair from durable records.
Archived claims remain stable after edits to the working copy.

### 3. Recorded literature discovery

Can proceed independently after the shared record conventions are chosen.
Own a small literature service, source records, fixtures and CLI/MCP routes.
Adapt `literature-review` only after the service behavior is validated.

Record exact queries, providers, dates, filters, returned identifiers, retrieval
time and inclusion/exclusion notes. Preserve provider-specific provenance when
deduplicating a DOI. Keep full-text access separate from metadata access.
Use OpenAlex first and existing Crossref/DOI validation where appropriate.
Support local reports and agency sources without forcing them into arXiv IDs.

Exit: offline fixtures cover duplicate identifiers, incomplete metadata,
provider failure, date filters and restricted full text. A small authorized
network smoke test is separate from deterministic tests. Claim no recall or
ranking improvement without an independently judged query set.

### 4. Reproducible report bundles

Depends on packages 1 and 2. Own report export/scaffold code, templates and
focused tests. Adapt `paper-writing` one skill at a time.

Generate a Quarto source, comparison data and provenance manifest from explicit
run selections. Include `.bib` inputs when scholarly claims need them. Preserve
the user's report layout: standalone HTML, Flatly/Darkly, concise explanatory
prose, interactive figures when useful, units and uncertainty, no hand-typed
computed results. Keep figure data and code with the report. Dataset identities
and access instructions stand in for redistributing restricted inputs.

Exit: a small local fixture produces a standalone report with one unfavorable
and one incomplete run visible. Verify references, numeric values, offline
assets, desktop/narrow layout and a useful static or tabular fallback. Missing
inputs produce an explicit incomplete report status, not invented results.

### 5. Bounded study orchestration

Depends on packages 1 and 2. Own a study controller, supervised state records,
integration tests and relevant session/TORC service extensions.

Build on current runtime adapters and TORC. Persist the experiment cap,
authorized compute, active ownership, elapsed budget, decisions and stop state.
Token/cost limits are enforceable only where usage is observable. Otherwise
report unknown usage and use an explicit measurable limit. Launch no duplicate
run when a controller resumes. Choose the next experiment only after evidence
and the declared promotion criteria are available.

Exit: fake executors prove interruption/resume, exhausted budgets, duplicate
submission prevention, lost workers, failed preflight and rejected promotion.
Follow with a bounded local smoke test. Real remote tests require a selected
host/profile and authorized budget. Do not assume a historical host is ready.

### 6. Connected research workspace

Depends on packages 1, 2 and 4. Own dashboard routes, templates and interaction
tests. Use the existing Python service layer and dashboard stack.

Provide tree navigation and a baseline comparison view linking hypothesis,
protocol, code change, run evidence and rendered artifacts. Show operational
state separately from scientific assessment. Keep incomplete and rejected
branches visible. Reuse service comparison results rather than recomputing
metrics in JavaScript. Handle active HTML artifacts in an isolated preview.

Exit: keyboard and narrow-screen checks, readable light/dark themes, stable
links to sealed evidence, safe artifact previews and CLI/dashboard parity.
Embedded agent chat, a general code editor and a desktop app remain deferred.

## First delivery and validation

Start with package 0 and its unattended local TORC demonstration. Next deliver
package 1 as a small CLI/MCP feature. Its demonstration should compare
two local reservoir-model variants under one fixed evaluation protocol, showing
metric units, evidence paths and reasons a run cannot be ranked. Use an explicit
synthetic fixture rather than private project inputs or claimed research results.

Before implementation, read applicable skills, establish the isolated worktree
and run baseline checks. Add a failing behavioral test for the selected package,
then implement and validate that package before expanding scope. Skill changes
are behavior changes and must be edited and validated one at a time. Update
attribution and regenerate runtime assets when adapting instructions.

Repository verification commands for implementation:

```bash
pixi run pytest
pixi run ruff check .
pixi run waterology render --check
python3 constraints/check-all.py .
git diff --check
```

Check cross-platform path handling and record compatibility. Add fresh native
platform smoke evidence before claiming platform support for a new executable
path. Pause expansion when a package cannot preserve old records, immutable
evidence or the user's protocol. Record the failure and next decision instead
of relaxing the acceptance criteria.

The initial reconnaissance did not execute upstream. Implementation now has
deterministic tests, a local TORC restart smoke test, a rendered synthetic report,
browser checks and a bounded OpenAlex request. Upstream runtime trials,
research benchmarks and remote launches remain unattempted. No feature parity
or scientific performance claim is made.
