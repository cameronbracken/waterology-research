---
name: agent-delegation
description: >
  Prepare and interpret delegated agent work with explicit task boundaries,
  worktree ownership, compute authorization, output paths, and return contracts.
  Use before assigning independent work to another agent or accepting its result.
---

# Agent Delegation

Delegate only work with a clean independent boundary, such as surveying an
unfamiliar code area, gathering a distinct evidence set, or writing from
completed results. Keep dependent decisions, central synthesis, and an active
experiment loop with the lead agent.

## Write a standalone brief

Assume the receiving agent has no conversation context. Include:

- Project and relevant branch or worktree.
- Objective and why the task is separate.
- Files or evidence scope the agent owns.
- Metric or decision criteria when applicable.
- Constraints, authorization boundaries, and allowed compute.
- Expected output path and return format.
- A concrete definition of done.

Keep short launch messages when the detail already lives in a written brief.

## Protect ownership and compute

- Never assign a branch or worktree that another writing agent owns.
- Do not edit a frozen experiment node.
- State which benchmark, remote, GPU, or long-running commands are authorized.
  When none are authorized, say so explicitly.
- Do not assume the receiving agent may push, publish, merge, or modify remote
  state. Nothing merges automatically.
- Permit nested delegation only when the runtime supports it and the brief
  assigns distinct ownership. Otherwise the receiving agent completes the work
  itself or reports the blocker.

## Interpret the return

Require the agent to save its artifact to the assigned output path and return a
short status with that path, checks performed, evidence produced, and blockers.
Inspect the artifact rather than treating the closing message as evidence.
Integrate edits only after checking ownership, diff, and verification results.
