# Experiment tree discipline

<!-- Adapted from alphaXiv/openresearch-cli,
agent-skills/orx-experiment-tree/SKILL.md at commit
13049867497de8fd5e15253cd818462629edd690 (MIT per Cargo.toml). See
ATTRIBUTION.md. -->

For multi-round experiment studies, use a tree of Git branches. The root
baseline holds the starting code and run command. Every other node branches
from a parent and tests one change against it. The `autoresearch` skill's
linear mode covers a single metric with a handful of sequential edits. Use
this tree discipline when the study spans several distinct design decisions.

## Cardinal rules

Breaking these rules silently invalidates results.

1. _Freeze the baseline._ Once the root has a recorded result, never edit it.
   Branch a child for each idea.
2. _Fix the run contract._ Every node uses the same benchmark command and
   environment. Do not vary behavior through command flags or environment
   variables. Only committed code and configuration may differ.
3. _Vary code, not command options._ Encode each hyperparameter, prior, or
   model option in a committed file and branch one child for each variant.
4. _Grow downward._ Fan a small set of siblings within one round, then descend
   from that round's winner for the next decision.
5. _Preserve recorded history._ Never merge or rebase a branch with a recorded
   result. To combine ideas, create a child and put the merge commit there.

## Shape: stacked bushes

```text
FLAT FAN (wrong)         NOODLE (wrong)         STACKED BUSHES (right)
base                     base                   base
+ a + b + c ... + n      + a                    + prior-sweep
                           + b                    + prior A
                             + c                  + prior B
                               + d ...              + winner: obs-model
                                                       + model A
                                                       + model B
```

- A flat fan measures every option against the start, so wins never
  accumulate.
- A noodle adds depth without testing competing options.
- Stacked bushes use width for the open options of one decision and depth for
  the decisions already resolved.

Before making X a child of Y, name what Y established that X retains. If X and
Y are options tried for the same decision, they are siblings.

## Loop

1. Run the benchmark once on the frozen root and record the seed.
2. Form options for one decision. Do not mix decisions in one round.
3. Fork one branch from the round's parent for each option. Name branches
   `exp/<round>-<idea>`.
4. Run the fixed command on each branch. Record metric, seed, branch, and
   parent in `autoresearch.jsonl`.
5. Give each result one move: _refill_ for an inconclusive result, _promote_
   for a clear win that becomes the next parent, or _stop_ when the goal is
   met or the line is exhausted. A result within run-to-run noise is a refill.
6. Record what each node established in `CHANGELOG.md` before moving on.

## Write-up

Lead with the strongest result figure. Then report the path through the tree,
each round's decision, the winner and margin, and what was abandoned. Include
a provenance table mapping every claim to its branch, exact run command, seed,
and metric. Copy commands verbatim.
