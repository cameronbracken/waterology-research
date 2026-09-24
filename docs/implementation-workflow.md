# RO-Crate and engineering workflow implementation

Scope: repair derived provenance export and make engineering specifications a
first-class entry to the existing managed study engine. Preserve the documentation
work in this branch and leave other worktrees unchanged.

## Acceptance

- Export valid profile metadata using compatible contexts and real file entities.
  Claim Workflow Run only when an archived executable workflow is available.
- Keep metadata tied to archived configuration. Do not expose the local repository
  URI or infer an input payload from a hash.
- Run a pinned validator with an explicit profile and requirement level. Retain
  failures and timeouts without turning sealed computation into failed execution.
- Exercise successful and invalid fixtures with the real validator, and cover
  destination confinement, immutable payloads, and retry inspection.
- Provide a specification-first engineering entry, acceptance evidence, and
  engineering candidate guidance through the shared CLI/MCP/service state.
- Preserve existing research contracts and acceptance semantics. Demonstrate both
  implementation-to-specification and optimization-under-constraints workflows.
- Update guides, examples, and diagrams to match verified behavior. Run the full
  development checks and an independent review before completion.

## Verification

Implementation and review are complete within the scope above. See the
[validation record](validation/2026-09-24-engineering-ro-crate.md) for passing
checks, adverse findings resolved, and execution environments not tested.
