# Testing and Debugging

## Behavior changes

- Define the observable behavior before implementation.
- Prefer a focused failing test first for clear behavior changes. Confirm that
  it fails for the missing behavior, then make the smallest change that passes.
- Add a regression test for a bug when practical.
- Test driven development is not required for documentation, exploratory
  analysis, generated files, configuration-only changes, or trivial edits.
  These changes still need a relevant check.
- Test real behavior. Avoid assertions that only freeze wording or mirror the
  implementation.

## Failures and unexpected behavior

1. Read the complete error and reproduce the symptom.
2. Inspect recent changes, inputs, environment, and component boundaries.
3. Trace the bad state to its source. Compare with a nearby working example.
4. State one hypothesis and test it with the smallest useful change.
5. Implement the fix at the source and rerun the reproducer plus related tests.

Do not stack speculative fixes. If three distinct fixes fail, pause and reassess
the architecture with the user before trying another.

## Long runs

Use progress output for long computations. Preserve logs, command arguments,
environment details, seeds, and artifacts needed to reproduce a failure.
