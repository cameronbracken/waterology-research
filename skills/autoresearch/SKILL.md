---
name: autoresearch
description: >
  Bounded autonomous research and engineering loop through TORC that evaluates
  committed candidates against a saved objective and constraints. Use when the user asks to
  optimize a research metric, run an experiment loop, or iteratively improve
  model, retrieval, or forecast performance.
metadata:
  claude-command:
    name: autoresearch
    argument-hint: <idea>
---

# Autoresearch

Use `writing-style` for summaries and `research-software-quality` for changes.
Read [token-discipline.md](references/token-discipline.md) for long runs.

## Start and continue by default

Treat an explicit autoresearch invocation with an actionable objective as a
request to start the bounded workflow, not as a request to explain it. Begin in
the same turn. Inspect existing state, establish or resume the saved contract,
configure the bounded driver when authorized, and run it without waiting for a
second prompt.

When the host provides a durable goal or continuation mechanism, create or use
it automatically for the study objective and stopping condition. Do not ask the
user to issue a separate goal command. Keep advancing across ordinary turn
boundaries, candidate failures, and successful iterations while the saved
budgets allow useful work. Stop only at a recorded acceptance or budget boundary,
an explicit stop request, or a material blocker that requires new information or
authority.

Infer reversible setup details from project instructions, existing study state,
and checked configuration when one reasonable choice is available. A missing
detail is not a reason to pause if work within the current authority can resolve
it. Durable continuation does not expand authority for compute, retries,
deployment, publication, or destructive actions.

## Enter the managed workflow

Use `waterology init` for an uninitialized Git project. It creates a small
configuration without importing native tasks. Inspect available definitions with
`waterology config refresh --check`. Register only the intended task with
`waterology workflow register NAME --task TASK`, or register an explicit definition
with `waterology workflow register NAME --definition FILE` when the native task is
ambiguous or needs outputs, metrics or input identities. Use `waterology config refresh`
only when importing every unambiguous discovery is appropriate. Commit the resulting
execution configuration with the project code.

Put `workflow: NAME` in the saved study contract. `waterology study create`
registers the contract reference and creates a baseline experiment when the
contract omits `baseline_experiment`. The study driver carries the same workflow
into candidate experiments. For manually created candidates, use
`waterology experiment create --workflow NAME`. The CLI and MCP services own
registration, execution and evidence collection; no skill is required to run them.

Use `waterology workflow run NAME --profile PROFILE` for an ordinary evaluation
that does not need a bounded candidate loop. It waits for TORC and collects results.
After interruption, use `waterology workflow watch RUN_ID` to resume collection.
Do not recreate run records or copy metrics into a parallel agent log.

After selecting the final result explicitly, use `waterology deliverable register`
and `waterology reproduce` to verify the exported source and declared outputs in
an isolated directory. See `docs/workflow-execution.md` in the Waterology source
for complete CLI examples and `waterology config schema` for configuration fields.

## Choose the objective

Use one managed loop with an explicit mode:

- __Engineering:__ build to a specification, optimize performance or efficiency,
  or solve a problem under constraints. Define acceptance tests, hard limits,
  regression criteria and a stopping target. Feasibility comes before speed.
- __Research:__ answer a scientific question. Define the estimand, evaluation
  design, uncertainty and evidence needed. A negative or inconclusive result is
  valid. A numeric improvement alone does not establish an explanation.

Keep `autoresearch` as the entry point for both. Do not force engineering work
into a hypothesis narrative or require tree search for cumulative implementation.
For tree search, read [experiment-tree.md](references/experiment-tree.md).

## Establish authority once

Read the existing study record and relevant project instructions first. If the
user asks to continue or resume an existing loop, resume it. Do not ask whether
it should start fresh unless there is a real ambiguity about which study.

Resolve the objective, allowed paths, evaluation/input identities, seeds, units,
acceptance rules, environment, TORC profile, concurrency, iteration/time budget,
retry cap and drain/cancel stop behavior. Record authority already given by the
user. Ask only for missing decisions or an action outside that authority.
Do not request permission again for each iteration, an allowed retry, or an
unchanged resume. Host trust and bounded study authorization are separate.

Write the contract as NestedText (`.nt`), then use the installed Waterology CLI or equivalent
MCP study tools:

```bash
waterology study create study-contract.nt --profile local --authorized-by "user approved this contract"
waterology study show STUDY_ID
waterology study enqueue STUDY_ID EXPERIMENT_ID
waterology study advance STUDY_ID
waterology study watch STUDY_ID
waterology study driver STUDY_ID --runtime codex --max-proposals 10
waterology study run STUDY_ID
waterology study stop STUDY_ID
```

Replace the profile and identifiers with resolved values. The authorization
text must accurately describe authority already given, not invent approval.
`create` queues the baseline experiment. `watch` drives queued evaluations and
waits for new candidates until a stopping condition. It does not generate code
or scientific conclusions by itself. The active agent owns candidate proposals unless the user authorizes a bounded
driver. `driver` records that choice and `run` resumes supervised candidate
sessions plus the TORC controller. Choose the runtime and proposal cap from the
existing authorization. Driver configuration does not grant runtime permissions.
A failed or ambiguous submission remains blocked until its identity is resolved.

Human-facing managed commands emit NestedText. Automation can request
`waterology --output-format json ...`; MCP and archived evidence retain their
typed machine format. Existing JSON contracts remain readable.

If these commands are unavailable, report the missing Waterology capability.
Do not replace managed execution with a shell loop or ad hoc remote commands.

## Standard execution

Every candidate evaluation uses the study's pinned TORC profile, including
local compute. Use the same committed project command and environment identity.
Never fall back to direct execution, SSH scripts, another host or a different
resource request when TORC fails. Retry within the saved policy or retain a
blocked state with the exact recovery action.

Source isolation, dependency setup and scheduling are separate choices: use
owned Git worktrees for candidates, the project's environment manager for
software, and TORC for evaluation. Lightweight local checks must be named and
bounded in the contract. They cannot substitute for the acceptance benchmark.
Check runtime permissions and the exact unattended execution path before a
long run. Do not bypass runtime safeguards to avoid prompts.

## Iterate within the contract

1. Read the current study and the latest archived evidence.
2. Choose one scoped candidate change consistent with the objective mode.
3. Create an owned experiment branch, edit only allowed paths, run declared
   lightweight checks, and commit the candidate. Preserve unrelated changes.
4. Queue it through `study enqueue` and advance the controller. Do not edit a
   queued, running, unknown or collecting candidate.
5. Read archived measurements and assessments. Keep failed and unfavorable
   runs. Do not promote incomparable evidence or change acceptance criteria.
6. Propose the next candidate while the saved budgets allow. Persist a concise
   handoff with the study ID and next decision at meaningful milestones.

The controller owns TORC submissions, retries, collection and checkpoint state.
Use its durable records as the execution authority. Existing `autoresearch.md`,
`autoresearch.jsonl` and `autoresearch.sh` are legacy records, not a second live
controller. Preserve them when resuming old work and explicitly migrate the
contract before launching a managed study.

Stop new work when asked to stop. Apply the saved drain/cancel policy to active
jobs. Stop also at the budget or acceptance boundary. Never extend limits,
change test data, deploy a candidate, publish results or delete history without
corresponding authority. Report the stopping reason and exact saved study ID.

Output: durable `.waterology/studies/` records, sealed run archives, and a
concise project handoff. Use `waterology compare-runs` for measurements and
`waterology report` for a portable Quarto bundle.
