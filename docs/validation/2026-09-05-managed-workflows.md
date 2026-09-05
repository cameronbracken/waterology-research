# Managed workflow validation, 2026-09-05

Implemented from the approved [expansion plan](../superpowers/plans/2026-09-05-openresearch-expansion.md)
on `feature/managed-research-workflows`, based on
`ce2699fc1dd487e55dd3cbe86a154c71414e855c`.
Changes remain in the isolated worktree. Runtime plugin installation, merge and
publication are separate from this implementation.

## Delivered behavior

| Package | Implementation |
| --- | --- |
| Managed execution | Once-recorded authority, pinned TORC routing, durable submission intent, bounded retries and concurrency, deadline, stop marker, candidate ownership and unchanged resume |
| Contracts and comparison | Research/engineering modes, protected evaluation identity, input hashes, acceptance thresholds, feasible candidate promotion, comparisons retaining missing and incompatible runs |
| Claims | Hashed archived JSON references and selectors, separate reference integrity and prose assessment, append-only assessment history and contradictory records |
| Literature | One bounded OpenAlex request, date filters, DOI deduplication provenance, inclusion decisions, local and agency source records |
| Reports | New portable Quarto bundle with retained measurements, figure code, claim checks, checksums, static table and embedded interactive assets |
| Orchestration | Existing supervised runtime adapters generate bounded sequential proposals; TORC evaluates committed candidates; recorded launch ambiguity does not cause duplicate launch |
| Workspace | Study and comparison pages linked to experiment tree, archived evidence, code changes and safe artifact downloads |

The `evaluation` object retains domain-specific design fields. The controller
does not validate the scientific adequacy of an estimand, period, site split or
uncertainty method. Research conclusions require assessed references and can
be negative or inconclusive. Numeric acceptance alone never completes research.

## Executed checks

Final checks on the implemented source:

| Check | Result |
| --- | --- |
| `pixi run pytest` | 519 passed in 46.79 seconds; one upstream Starlette/AnyIO deprecation warning |
| `pixi run ruff check .` | Passed |
| `pixi run waterology render --check` | Generated assets current |
| `python3 constraints/check-all.py .` | 8/8 passed |
| `git diff --check` | Passed |

The retained [test log](2026-09-05-managed-workflows-pytest.txt) records the full
suite result. Temporary dashboard and report servers were stopped after QA.

The suite covers CLI/MCP comparison parity and dashboard evidence links as well
as the existing archive, runtime, configuration, packaging and TORC behavior.

The managed tests exercise unchanged resume, ambiguous submission, profile drift,
stale outputs, generic execution bypass, candidate ownership before enqueue,
session cancellation ambiguity, research conclusions after exhausted budgets,
explicit claim assessment, archive tampering and missing evidence.

### Local TORC restart smoke

`scripts/smoke-managed-study.py` started its own loopback TORC 0.40.0 server and
evaluated two synthetic reservoir fixtures. Every controller tick ran in a fresh
CLI process. Both evaluations used profile `local` and command `python3 model.py`.
The script stopped its own server after collecting both archives.

| Evidence | Value |
| --- | --- |
| Study | `study-1dd893511d1b4b92` |
| Baseline | `run-b74aef4b515f4545`, synthetic error 2.0 m, acceptance failed |
| Candidate | `run-5ba4534814b94442`, synthetic error 0.5 m, acceptance passed |
| Budget | Two attempts, 180 seconds, one evaluation slot |
| Result | Complete, two TORC workflow identities, no duplicate submission |

These fixed values test execution and acceptance plumbing. They are not model
performance results. The smoke output directory retains study-result.json,
server logs, the project, both archives and report bundles. The script can
recreate the fixture in a new directory.

With `torc` and `torc-server` 0.40 or later available on PATH, run:

```bash
pixi run -e reports python scripts/smoke-managed-study.py NEW_DESTINATION
```

Use a new destination path outside the source checkout. The script creates the
directory and starts only its own local synthetic jobs.

### Report and dashboard

Quarto 1.9.38 rendered a standalone HTML report containing both real synthetic
archives and a deliberately missing third run. The missing row remains visible
and the export is marked incomplete. Browser inspection verified the values,
delta -1.5 m, units, visible exclusion reason, embedded Plotly controls and no
external script URLs. Desktop and 768-pixel layouts were inspected. The report
and dashboard both rendered readable light and dark themes. The report figure
retains its light publication-style background in dark mode.

The Plotly layout scanner does not recognize native Plotly HTML in this bundle
and reported `no Plotly layouts found`; it is not a passed chart validation.
Browser inspection verified the chart axes, labels and layout directly.

### Literature

One live OpenAlex query, `reservoir operations`, with dates 2020-01-01 through
2026-09-05 and limit two completed and retained two source records in
`search-dd773d850a49466e`. Offline fixtures cover provider failure and duplicate
identifiers. This establishes request/record plumbing, not retrieval quality.

## Review dispositions

An independent read-only reviewer inspected execution, evidence and driver
changes. Findings addressed during implementation included:

- Save execution configuration for collection and reject unchanged prior output.
- Preserve unresolved submission identity and prevent index repair from losing it.
- Cancel active work before drift validation and save stop intent outside long locks.
- Guard generic execution for candidates reserved by the driver.
- Reconcile saved session attempts without relaunching after an ambiguous response.
- Recheck stop and deadline immediately before each external launch.
- Preserve cancellation uncertainty rather than reporting a clean stop.
- Apply candidate cleanup to research conclusions and allow evidence-only conclusions after budget exhaustion.
- Prevent an existing conclusion from being overwritten during cleanup.
- Keep claim support separate from archive integrity and preserve incomplete reports.
- Reject exports into control directories and escape evidence values in report prose.

## Remaining qualification limits

- Remote TORC: unverified. No host or budget was selected for a remote smoke.
- Real unattended model generation: unverified. Driver tests use controlled
  session doubles. Existing runtime process tests pass, but they do not establish
  this combined workflow's permission behavior with a real model session.
- Windows/Linux native smoke: unattempted for the new executable path.
- The deadline is wall-clock time from authorization. Drain permits already
  authorized work to finish. CPU-hours, token usage and monetary cost are not metered.
- Local checks and domain design are declared instructions, not OS resource or
  scientific-validity enforcement. Runtime sandbox policy remains authoritative.
- Worktree/configuration/output checks detect known drift. They do not establish
  a fully immutable runtime filesystem or detect every transient write and revert.
- Intervals/MCSE are not inferred from point estimates. Claim selectors currently
  address JSON evidence. Scholarly bibliography validation remains the existing
  workflow and is not synthesized from these numeric comparison bundles.
- Export records `render_status: not_attempted`. A subsequent external Quarto
  render does not rewrite that export-time provenance record.

No historical remote host state is used as current readiness evidence.
