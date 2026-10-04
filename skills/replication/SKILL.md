---
name: replication
description: >
  Plan a replication of a paper, claim, or benchmark, and execute only after an
  explicit environment choice. Use when the user asks to replicate results,
  reproduce an experiment, verify a claim empirically, or build a replication
  package.
metadata:
  claude-command:
    name: replicate
    argument-hint: <paper>
---

# Replication

Use `writing-style` for the plan, claim ledger, and report. For a complete
delegated task, use `replication-coordinator` with the target, owned worktree,
existing plan and run identities, environment choice, compute authority, budgets,
and delegation permissions. An agent already coordinating this task retains
ownership rather than delegating to another coordinator. Direct work remains
valid for a small task or when delegation is unavailable.

## Scope and durable plan

Identify whether the task reproduces an existing Waterology deliverable or
implements a new replication from a paper, benchmark, or claim. Preserve the
fixed source and comparison definition of an existing deliverable.

Read the target sources, linked code, and relevant `CHANGELOG.md` entries.
Delegate broad implementation extraction to `researcher` when useful. Record
what was inspected and distinguish missing access from contradictory evidence.

Write `docs/.plans/<slug>-replication.md` and a claim ledger at
`docs/.drafts/<slug>-replication-claims.md`, or use the assigned existing paths.
Unless broader coverage was requested, focus on the main illustrative claim.
Each claim records its source and locator, target result, metric and comparison
criteria, observed result and uncertainty, run or artifact identity, assessment,
substitutions or downscaling, and compute cost. Missing results stay unmeasured.

For training or dataset-heavy targets, extract the data, method, hyperparameters,
compute assumptions, and implementation recipe before execution. Record access
conditions and input identities. Resolve material ambiguity in targets, metrics,
or criteria before dependent work. Preserve frozen protocols and distinguish a
planned approximation from a faithful implementation.

Plan the code, data, environment, authorized checks, budgets, and handoff.
For substantial new implementation, `engineer` may implement a bounded
specification with fixed targets and allowed checks. The execution owner, not
that specialist, submits the registered production workflow.

## Environment and execution authority

Require an explicit environment choice before execution. Record separately:

- Execution location and owned checkout or worktree.
- The project's software environment, language toolchain, and dependency manager.
- Compute profile, authorized commands, and runtime and storage budgets.
- Whether the user requested plan-only work with no execution.

Reuse decisions and authority already recorded for the current scope. Match the
project setup before creating an environment. Do not install packages, run
training, or execute experiments until the user confirms the environment, unless
that confirmation is already recorded. Use `setup-environment` only within the
chosen scope when scaffolding is needed. An environment choice does not grant
unlimited compute or authorize an otherwise unapproved remote action.

Name exactly one execution owner, either the parent or coordinator. If the parent
owns execution, return the ready request and prerequisites rather than launching
it as well. Plan-only work ends with the plan and checks explicitly not attempted.

## Execute through the existing services

For an existing Waterology deliverable, use the CLI reproduction workflow within
the selected environment and existing compute authority:

```console
waterology reproduce final NEW_DIRECTORY --profile PROFILE
waterology reproduce final NEW_DIRECTORY --path EXPORTED_BUNDLE --bundle --profile PROFILE
```

The service restores the selected source and environment, verifies input
identities, executes through TORC, and checks fresh outputs. Record the actual
destination, source revision, run identities, and result. After an interrupted
or blocked attempt, inspect its saved reason and use `--resume` with the same
directory when continuation is authorized. Do not replace the source, reference
outputs, input identities, or tolerances to obtain a pass.

For a new replication, initialize records with `waterology init` when needed,
inspect native tasks with `waterology config refresh --check`, and register the
selected task or evaluation definition with:

```console
waterology workflow register replicate --task TASK
waterology workflow register replicate --definition workflow.yaml
```

Commit source and execution configuration before
`waterology workflow run replicate --profile PROFILE`. TORC owns jobs and
dependencies; Waterology collects run evidence. Record the actual run identity
and use `waterology workflow watch RUN_ID` to resume collection. Unknown status
requires reconciliation before submission, not a replacement run. Do not bypass
the registered workflow with another launcher or an independent retry loop.

When authorized, proceed claim by claim. Preserve failed attempts, seeds, RNG
kind, commands, scripts, raw outputs, and substitutions. New attempts, changed
profiles, or environment repairs need remaining authority and separate evidence.
Select and export a resulting deliverable with `waterology deliverable register`
and `waterology deliverable export` when that handoff is in scope. Output
agreement and support for the paper's claims are separate assessments.

## Assess and audit

Assess each claim as `aligned`, `partially aligned`, `inconclusive under this setup`,
or `not attempted`. State the comparison results and uncertainty supporting that
assessment. For a mismatch, report what this setup observed without inferring
that the paper's general claim is wrong. Do not call an outcome replicated unless
its planned comparison checks pass. A completed task can report disagreement.

At handoff, use `reproducibility-auditor` when delegation is available and
appropriate. Supply the source revision, input identities, selected environment,
execution and comparison records, claim ledger, report candidate, and a distinct
audit path such as `quality_reports/<slug>-reproducibility-audit.md`. Use inspection
mode if no run was attempted, or reproduction evidence review when records exist.
The auditor reports gaps and the environment and outputs checked; it does not
launch another run. The named execution owner retains control through the
existing reproduction or registered workflow. When independent delegation is
unavailable, perform the scoped audit directly and disclose that limitation.

Include content fingerprints or immutable snapshot references in specialist
briefs and require the returned results to identify the inputs inspected.
Compare dispatched, returned, and current versions before accepting work. Bind
the audit to the claim ledger, report, and execution artifacts. Changes invalidate
affected checks; missing version records leave them unverified. Reaudit affected
claims after report corrections, and require a new authorized run for changes
that invalidate execution evidence. Do not erase previous findings or attempts.

## Resume and deliver

Keep a task ledger in the plan with task identifiers, owners, brief paths,
dependencies, launch identities, inputs, outputs, statuses, and blockers. This
ledger references service records; it does not replace execution state. Reconcile
unknown worker or run status before dispatching again. A coordinator unable to
launch specialists returns ready briefs for parent dispatch and resumes from
the returned artifacts. Do not bypass runtime restrictions with a CLI agent
launcher.

Append concise `CHANGELOG.md` entries after meaningful progress, failed attempts,
major checks, and before stopping. Record the objective, changes, evidence,
unresolved decisions, and next step. Do not claim work will continue after a
turn unless a continuation mechanism was actually scheduled.

Write `docs/<slug>-replication.md` or the assigned report. Lead with the observed
outcome and claim ledger; include figures only when supported by results. Link
raw outputs, comparison evidence, audit, and remaining work. Identify the actual
environment, source revision, commands, and applicable randomization records.
Include inspected source URLs and local artifact paths. A plan-only, partial,
blocked, or budget-exhausted task still leaves its plan, ledger, and report with
unperformed checks labeled. Finishing the report does not establish alignment.

Coordinator for a delegated task: `replication-coordinator`.
Specialists when appropriate: `researcher`, `engineer`, `reproducibility-auditor`.
Output: plan, claim ledger, implementation and raw results when executed, report,
audit, and a `CHANGELOG.md` trail.
