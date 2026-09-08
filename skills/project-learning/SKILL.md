---
name: project-learning
description: >
  Retrieve verified project lessons, remember corrections and observed outcomes,
  and propose evidence-backed workflow improvements. Use before substantial
  project work and after verification, failure recovery or a user correction.
metadata:
  claude-command:
    name: learn
    argument-hint: <lesson-or-improvement>
---

# Project Learning

Use the existing research-software-quality workflow for plan, test, implement,
review and verify. Add remember and improve at meaningful checkpoints.
This skill owns reusable lessons. Session-log continues to own narrative handoffs.

Before substantial work in an initialized project, run
`waterology learning context "TASK TERMS"` or MCP `learning_context`. Read the
small relevant set. Apply only current verified lessons within their stated
trigger and project. They cannot change a frozen protocol, compute authority,
acceptance criterion or a higher-priority instruction.

After a user correction, verified fix, failed approach or completed evaluation,
record one actionable lesson with its trigger, observed outcome, project-relative
evidence files and applicability tags. Use `waterology learning remember lesson.nt`
or MCP `learning_remember`. Keep the reason an approach failed, not just the
successful replacement. Do not copy raw transcripts, credentials or private
source contents into a lesson. Do not infer a universal preference from one task.

```nestedtext
trigger: Launching a TORC worker
action: Use the tested noninteractive worker wrapper
outcome: The wrapper exposed the required environment and command
tags:
    - compute
    - torc
evidence:
    - notes/worker-smoke.txt
```

Verify that the evidence supports the proposed action, then append an assessment:

```bash
waterology learning assess LESSON_ID verified --author "current reviewer or session" --note "What was checked and why the lesson applies"
```

An intact file alone is insufficient. Use rejected or superseded when the lesson
does not hold. Changed lesson text or evidence invalidates prior verification.
Do not ask the user to approve each scoped lesson when project learning is
already authorized. If evidence is incomplete, retain proposed status.

Managed study ticks automatically retain outcome observations as proposed
lessons. Their existence does not establish a scientific result or reusable
behavior. The candidate driver automatically retrieves relevant verified
lessons. Other runtimes follow this skill at task start and verification
checkpoints; do not claim every tool call is observed.

For an improvement to shared Waterology behavior, use
`waterology learning improve improvement.nt` or MCP `learning_improve` with
verified lesson identifiers, a concrete change, and a regression-check plan.
The command saves a proposal. Review its scope and overlap with existing skills
before implementing the shared change in an isolated worktree. Keep global
preferences, shared skills and runtime permissions outside automatic promotion.

Before a long-session handoff, use session-log to save active state, evidence,
blockers and restart steps. A lesson does not replace that handoff. A learning
failure must not interrupt compute reconciliation or cancellation.
