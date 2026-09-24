---
name: engineering-workflow
description: Build or repair software to an explicit specification, or optimize it under fixed constraints, using bounded Waterology studies and archived acceptance evidence. Use when the user requests managed engineering iteration or an engineering workflow.
metadata:
  claude-command:
    name: engineering
    argument-hint: <specification-or-optimization-target>
---

# Engineering workflow

Start with required behavior, acceptance checks, allowed changes, and a stopping
condition. Engineering does not require a scientific question or literature
review. Research needed to resolve a design choice remains scoped to that choice.
Use `research-software-quality` for implementation and verification.

## Establish the contract

Inspect the project and existing study before creating anything. Resume authorized
work rather than duplicating its controller or evaluation. Register the project's
qualification command as a named workflow with its outputs, metric extractors,
environment restoration, and protected inputs.

Use `waterology engineering init CONTRACT.nt` to draft a contract. It requires
`--objective`, `--workflow`, one or more `--allow-path`, `--max-iterations`, and
`--max-seconds`. Edit the draft before creating the study:

- For build or repair, map required behavior to protected acceptance tests. The
  draft expects a `failed_checks` count with zero required for acceptance. Change
  metric names and rules to match the actual evaluator, not to relax the target.
- For optimization, supply `--target-seconds` to add an elapsed-time requirement,
  or author the actual performance metric. Keep correctness, regression limits,
  workload identity, and timing uncertainty explicit. All rules must pass.
- Keep acceptance tests, specification, environment locks, and fixed inputs outside
  allowed candidate paths. Record input hashes where needed.

The build draft uses `candidate_strategy: latest_completed` for cumulative changes.
It starts from the most recent completed, assessed candidate, even if requirements
remain unmet. `best` uses the accepted feasible candidate selected by the shared
engine, or the baseline when none exists. Neither strategy promotes unresolved
runs. Ancestry is not acceptance.

## Execute within existing authority

Save the contract, commit the qualification workflow and protected files, and use
`waterology engineering create CONTRACT.nt --profile PROFILE --authorized-by TEXT`.
TEXT records actual authorization already given. Missing material decisions need
clarification; do not invent compute authority, targets, or budgets.

Use `engineering enqueue` and `engineering watch` for manually proposed candidates.
Use `engineering driver STUDY_ID --runtime RUNTIME --max-proposals N`, then
`engineering run STUDY_ID` when bounded candidate generation is authorized. These
commands use the same study records and TORC controller as research studies.
Configure a driver only once, then resume it. Candidate sessions use the engineer
role and may run only declared lightweight checks; the controller owns evaluation.

Inspect `waterology engineering show STUDY_ID` for each requirement, observed value,
threshold, archive integrity, and accepted runs. Continue within the saved bounds
until acceptance, exhaustion, a stop request, or a recorded blocker. Retain failed
checks and measurements. Never rewrite evaluation rules to make a candidate pass.

## Close the work

Use `engineering stop` to apply the saved drain or cancel policy. Report the study
ID, candidate commit, requirement outcomes, and unrun checks. Completion of a job
or existence of an RO-Crate does not establish acceptance.

Select the final run explicitly before registering a deliverable and reproducing
its declared outputs. Deployment, publication, or merging remains a separate action
within the user's authority. The Waterology source guide `docs/engineering.md`
contains CLI examples for build and optimization workflows.
