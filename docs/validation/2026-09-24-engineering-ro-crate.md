# Engineering and RO-Crate validation

Validated on 2026-09-24 in the isolated `docs/workflow-guide` worktree, based on
`05c2637`. This record covers the uncommitted implementation and documentation
changes in that worktree. It does not describe a release or installed plugin refresh.

## Scope and results

| Check | Result | Scope |
| --- | --- | --- |
| Default test suite | PASS: 669 passed, 2 skipped | CLI, services, study controller, packaging, MCP, dashboard, and regression tests |
| Pinned external validator | PASS: 2 tests | Process Run and Workflow Run acceptance, plus deliberate invalid-metadata rejection |
| Local TORC engineering smoke | PASS | Two synthetic evaluations, controller restart between ticks, acceptance stop, and report export |
| Engineering status on smoke evidence | PASS | Completed study and one accepted run with verified archived metrics |
| Smoke run crate validation | PASS: 55 required checks | Workflow Run 0.5 with inherited Process Run 0.5, Workflow RO-Crate 1.0, and RO-Crate 1.1 |
| Ruff | PASS | Whole repository |
| Generated assets | PASS | Runtime adapters current, including engineer role and engineering command |
| Constraints | PASS | Changed applicable paths |
| Documentation | PASS | Local links and anchors checked; six Mermaid diagrams rendered and inspected |
| Independent review | Resolved | Diagnostic-write failure, Slurm definition selection, and runtime/source version attribution corrected |

The default suite skips the two tests requiring the optional validator environment.
They were run separately with `roc-validator==0.11.4`. The default run reported two
existing warnings: an upstream Starlette deprecation and missing Zotero credentials
in a test. Neither warning prevented the checks above.

The first expanded suite exposed the new engineer agent missing from the required
runtime inventory. Adding it and regenerating adapters resolved the packaging
failures. Real validation also rejected nested metric objects; flattened graph
entities now pass. These failures were fixed without weakening acceptance checks.

## Repeat the checks

```console
pixi run pytest -q
pixi run ruff check .
pixi run waterology render --check
pixi install -e rocrate --locked
WATEROLOGY_TEST_ROCRATE=1 pixi run -e rocrate pytest tests/core/test_rocrate.py -k real_validator -q
pixi run python scripts/smoke-managed-study.py NEW_EMPTY_DESTINATION
```

Run constraints on changed applicable paths. The smoke test starts an isolated
loopback TORC server and needs `torc` and `torc-server` on PATH. Its data and
metrics are synthetic, and its destination must not already exist. External
validator checks may need network access to retrieve JSON-LD contexts.

The smoke study was `study-7a673c2468364976`, with runs
`run-6717f76cdec6416a` and `run-9687d6f7200448d5`. The second run satisfied the
saved specification. A fresh manual crate export from that run passed all
55 REQUIRED checks. The adjacent JSON record retains the validator statistics
without local paths or raw environment details.

## Boundaries

- RO-Crate 1.3 / Workflow Run 0.6 remains an upgrade target; the pinned validator
  supports the older compatible set used here.
- No live WorkflowHub, Zenodo, or Galaxy import was attempted.
- Remote and Slurm execution were not launched. Slurm definition selection has
  a regression test, not a new live cluster qualification.
- Candidate sessions use the engineer role in controller tests. No unattended
  model session was launched by this validation.
- Engineering acceptance checks declared metrics. It does not establish that a
  user's acceptance suite covers every required behavior, or authorize deployment.
