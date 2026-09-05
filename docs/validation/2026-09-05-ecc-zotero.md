# Project learning and Zotero validation

This extends the [managed-workflow validation](2026-09-05-managed-workflows.md)
and [ECC/Zotero implementation record](../superpowers/plans/2026-09-05-ecc-learning-zotero.md).
All changes remain in `feature/managed-research-workflows` in the existing
isolated worktree. No runtime plugin installation, merge or publication occurred.

## Verified behavior

Final checks on 2026-09-05:

| Check | Result |
| --- | --- |
| Full test suite | 540 passed in 76.00 seconds |
| Ruff | Passed |
| Generated runtime assets | Current |
| Repository constraints | 8/8 passed |
| Git diff whitespace check | Passed |

The [test log](2026-09-05-ecc-zotero-pytest.txt) retains the complete result.
Warnings were the existing Starlette/AnyIO deprecation and the expected missing
Zotero credential warning exercised during a local source-registration test.

- NestedText study input converts known numeric fields while retaining leading
  zeros in domain identifiers. Legacy JSON and explicit machine output work.
- Lessons require evidence and explicit support assessment. Edits to the lesson
  or evidence invalidate verification. Conflicting reuse of an ID is rejected.
- Managed study ticks capture outcome observations without converting numerical
  acceptance into scientific or behavioral support. Optional learning errors
  cannot prevent execution reconciliation or candidate-session cleanup.
- The research workflows and researcher agent check credential presence at entry.
  `ZOTERO_API_KEY` and `OPENALEX_API_KEY` are used when available and never returned
  by the check. Missing credentials produce warnings.
- DOI, provider IDs, stable locators and source URL aliases preserve reference
  identity. Later DOI enrichment reuses the same item and attachment keys and
  marks completed metadata pending for an update.
- Zotero sync preserves existing metadata and collection memberships, reports
  remaining work, and rotates attempted failures behind never-attempted records.
- Metadata and PDF success remain separate. Retry uses pinned local PDF bytes
  and reconciles matching remote attachment MD5 through the SDK adapter.
- Library destination changes, conflicting identity, changed PDF bytes, non-PDF
  responses and credential-bearing URLs are not silently accepted.
- Malformed optional Zotero settings do not erase a completed search. A rejected
  source does not prevent later valid sources from being queued.

## Local integration evidence

The isolated TORC 0.40 restart fixture passed with study
`study-291842e39d0b4e9b`, baseline `run-bce1784279ea437e` and candidate
`run-31773da44126449c`. Both evaluations completed through local TORC, with each
controller tick in a fresh process. The study reached its engineering target.
Two proposed learning observations were retained. The smoke script stopped its
own server after collection. These are synthetic plumbing results, not research
performance claims.

## Review

An independent reviewer checked the new learning, reference and format services
against the installed Pyzotero 1.15.1 source. The review drove fixes for optional
learning failure isolation, lesson fingerprints, attachment retry reconciliation,
source aliases, sync fairness/completeness, metadata URL privacy, optional capture
isolation and DOI enrichment scheduling. Regression tests cover these cases.

## Live access limits

The current tool process reported both API key variables absent after the user
said they had added them. Only availability was inspected, never values. The
location/environment mechanism is pending clarification, and no personal or
group library was selected. No authenticated Zotero request, collection creation
or live PDF upload was attempted. Offline gateway and SDK-adapter tests do not
establish live account readiness.

The integration uses Zotero's Web API and account sync, not direct desktop writes
or WebDAV. Network URL checks do not constitute complete hostile-network
isolation. Project lessons remain local state until explicitly preserved in an
archive or handoff. No global memory was updated.
