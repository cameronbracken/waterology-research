---
name: autoresearch
description: >
  Bounded research experiment loop that tries hypotheses, measures benchmark
  evidence, keeps what works, and records what fails. Use when the user asks to
  optimize a research metric, run an experiment loop, or iteratively improve
  model, retrieval, or forecast performance.
metadata:
  claude-command:
    name: autoresearch
    argument-hint: <idea>
---

# Autoresearch

<!-- Adapted from companion-inc/feynman, skills/autoresearch/SKILL.md at commit
8ad8d5582fc5acb855fb83f972f0f3121d1aa423 (MIT), with tree guidance from
alphaXiv/openresearch-cli, agent-skills/orx-experiment-tree/SKILL.md at commit
13049867497de8fd5e15253cd818462629edd690 (MIT per Cargo.toml). See
ATTRIBUTION.md. -->

Use `writing-style` for experiment summaries, decision notes, and reports.

If `autoresearch.md` and `autoresearch.jsonl` exist, ask whether to resume or
start fresh. Read recent relevant `CHANGELOG.md` entries before resuming.

Before a new run, collect:

- Optimization target and benchmark command.
- Metric name, unit, and whether higher or lower is better.
- Files allowed to change.
- Maximum number of iterations, defaulting to 20.
- Linear or tree loop shape.

Linear mode uses one working branch and keeps or reverts each loop owned edit.
Tree mode applies when the study spans several design decisions. Read and follow
[experiment-tree.md](references/experiment-tree.md) for the entire tree run.

Require an execution environment: local, a new Git branch, a Pixi environment,
or remote SSH or Slurm. Then present the target, command, files, environment,
iteration cap, and loop shape. Do not run the baseline or edit code without the
user's explicit confirmation of that plan.

Create `autoresearch.md`, `autoresearch.jsonl`, and `autoresearch.sh`. Record a
seed and RNG details, run the baseline, then repeat:

1. State one hypothesis and make one scoped change.
2. Run the fixed benchmark.
3. Append the metric, evidence, and decision to `autoresearch.jsonl`.
4. Keep the change, revert only the loop owned edit, or record the failed
   hypothesis. Preserve unrelated user changes.
5. Append concise `CHANGELOG.md` entries after the baseline and meaningful
   milestones.

Stop when interrupted, explicitly stopped, or the iteration cap is reached. Do
not silently extend the cap. Report progress during long runs.

In tree mode, a round tests sibling options for one decision. Log each node with
its branch and parent, then refill, promote, or stop as the rule describes. The
baseline stays frozen and the benchmark command never changes. Only committed
code or configuration varies. The cap counts benchmark runs rather than rounds.

Treat a request to `stop` or `off` as ending the loop while retaining state and
results.
Treat a request to `clear` as permission to remove only the resolved
`autoresearch.md`, `autoresearch.jsonl`, and `autoresearch.sh` files before a
fresh start. Verify those exact paths first and preserve code, results, and
unrelated files.

Output: `autoresearch.md`, `autoresearch.jsonl`, `autoresearch.sh`.

---
*Adapted from Feynman (companion-inc/feynman, MIT); tree mode from
openresearch-cli (alphaXiv/openresearch-cli, MIT per Cargo.toml). See
`ATTRIBUTION.md`.*
