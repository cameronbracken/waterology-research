---
name: experiment-tree
description: >
  Git-native experiment-tree discipline for multi-round studies: a frozen
  baseline, one branch for each hypothesis, a fixed run contract, and a tree
  that fans within a round then descends onto the winner.
paths:
  - "**/autoresearch.md"
  - "**/autoresearch.jsonl"
---

<!-- Adapted from openresearch-cli (alphaXiv/openresearch-cli, MIT per Cargo.toml). See ATTRIBUTION.md. -->

# Experiment-tree discipline

For multi-round experiment studies: calibration campaigns, Stan model
variants, hyperparameter searches, forecast-skill optimization. A study is a
**tree of git branches**. The root (**baseline**) holds the starting code and
the run command; every other node is a branch off a parent, testing one
change against it. The `/autoresearch` command's linear mode covers a single
metric with a handful of sequential edits; switch to this tree discipline
when the study spans several distinct design decisions.

## Cardinal rules

Breaking any of these silently invalidates results. They are not style
preferences.

1. **Freeze the baseline.** The root branch is the control every variant is
   measured against. Once it has produced a recorded result, never edit it.
   To try an idea, branch a child and edit the child.
2. **The run command and environment are a fixed contract.** Every node runs
   the same benchmark command in the same environment. Do not vary behavior
   through command flags or environment variables (`LR=3e-4 Rscript ...` is
   the anti-pattern). The only thing that differs between nodes is committed
   code and config, so results stay comparable.
3. **Vary code, not knobs in the command.** Encode each hyperparameter,
   prior, or model option in a committed file and branch one child for each
   variant.
4. **Grow the tree downward, not sideways.** Fan a small set of siblings
   within a round (the options of one decision), then descend onto that
   round's winner for the next round.
5. **Never merge or rebase a branch that has a recorded result.** Its history
   is the code its result came from. To combine two ideas, create a child and
   put the merge commit there.

## Shape: stacked bushes, not a flat fan or a noodle

```
FLAT FAN (wrong)         NOODLE (wrong)         STACKED BUSHES (right)
base                     base                   base
+ a + b + c ... + n      + a                    + prior-sweep        round 1:
                           + b                    + prior A          options of one
                             + c                  + prior B          decision
                               + d ...              + winner: obs-model   round 2 descends
                                                       + model A          onto round 1's
                                                       + model B          winner
```

- **Flat fan** (the whole sweep off the baseline): every result is measured
  against the start, so wins never accumulate.
- **Noodle** (a long single-child chain): depth without progress; steps do
  not actually build on each other.
- **Stacked bushes** (right): width is the open options of one decision, and
  depth is decisions already resolved, stacked one level down for each winner
  kept.

The test before making X a child of Y: name what Y established that X builds
on. If you can ("Y is the winning prior; X keeps it and changes the
observation model"), X is a child. If you cannot, because X and Y are options
tried at the same time, they are siblings in the same bush.

## The loop

1. **Baseline** — run the benchmark once on the frozen root for reference
   numbers, with the seed recorded.
2. **Round** — form the options of a single decision. Do not mix decisions
   from different rounds into one batch; that is what produces the flat fan.
3. **Branch and edit** — one branch for each option, forked off the round's
   parent. The branch diff is the hypothesis. Name branches
   `exp/<round>-<idea>` so the tree reads from `git branch`.
4. **Run** — the fixed command on each branch. Record metric, seed, branch,
   and parent in `autoresearch.jsonl`.
5. **Decide** — each result gets one of three moves: **refill** (inconclusive
   result, try the next option in the round), **promote** (a clear win; this
   node becomes the parent of the next round), or **stop** (goal met or the
   line is exhausted, typically after about 3 consecutive failed rounds).
   Comparisons need to clear noise: a win within run-to-run variation is a
   refill, not a promote.
6. **Record** — write what each node established into `CHANGELOG.md` before
   moving on. Findings not written down are lost.

## Write-up

When a study concludes, write the tree up as a short report: lead with the
strongest result figure, then the path through the tree (each round's
decision, its winner, and the margin), then what failed and why it was
abandoned. Include a provenance table mapping each claim to its branch, exact
run command, seed, and metric. Copy commands verbatim; do not abbreviate
them to pseudocode.
