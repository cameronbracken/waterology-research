# Workflow Run RO-Crate evaluation verification

Date: 2026-09-21

## Checks performed

- Retrieved the current Process Run, Workflow Run, and Provenance Run profile
  pages and the profile changelog directly.
- Checked the four decision-critical claims against exact primary-source
  passages: version compatibility, profile granularity, RO-Crate fixity scope,
  and validator coverage.
- Resolved DOI `10.1371/journal.pone.0309210` through OpenAlex and confirmed the
  title, year, DOI, and author list.
- Downloaded the Autosubmit, Galaxy, and Sapporo Zenodo example archives and
  inspected their JSON-LD contexts, declared profiles, entity types, workflow
  entities, and action entities.
- Inspected Waterology's archive, run, workflow, TORC, environment, metric,
  claim, and reproduction models in source.
- Requested every external URL in the cited draft with redirects enabled. All
  28 distinct URLs returned HTTP 200 on 2026-09-21.
- Compared every main recommendation with the cited profile requirements or
  local source evidence. Inferences are labeled as design decisions rather than
  standard requirements.
- Read the cited draft for unsupported claims, version mixing, path behavior,
  redaction implications, and overstatement of downstream interoperability.

## FATAL findings

None.

## MAJOR findings

### Fixed: completed checklist syntax conflicted with a packaging invariant

The first full test run had 632 passes and one failure. A packaging test reserves
lowercase `- [x]` markers for the six completed platform slices and asserts that
there are exactly six. Marking the five evaluation tasks with the same syntax
raised the count to 11. The evaluation tasks now use Markdown's equivalent
uppercase `- [X]` checked form. The focused regression test passed after the
change.

Evidence: `tests/packaging/test_docs.py::test_roadmap_marks_platform_and_research_slices_complete`.

### Fixed: wrapper layout would have invalidated native verification

The initial research note proposed copying archive members directly into the
RO-Crate root and adding `ro-crate-metadata.json`. Waterology's verifier treats
files absent from `checksums.sha256` as unexpected. A root-level metadata file
would therefore make native archive verification fail when run at the wrapper
root.

The recommendation now nests the unchanged sealed archive under `run/` and
places `ro-crate-metadata.json` at the wrapper root. Standard RO-Crate entities
can reference `run/artifacts/...`, while Waterology verifies `run/` exactly as
before.

Evidence:

- `src/waterology/core/archive.py`, `verify_archive`
- `docs/.drafts/workflow-run-ro-crate-cited.md`, "Archive placement and fixity"

### Open: live repository interoperability is not qualified

The evaluation verifies documented WorkflowHub upload, Zenodo preservation, and
Galaxy export/import behavior. It does not submit, publish, or import a
Waterology crate. The final text limits those claims and makes live
qualification a separate release check.

This is not a blocker for the design decision. It remains a blocker for any
future claim that a Waterology export is accepted or executable by a named
service.

## MINOR findings

- Most published implementation examples declare WRROC 0.1 with RO-Crate 1.1,
  while the current coherent target is WRROC 0.6 with RO-Crate 1.3 and Workflow
  RO-Crate 1.1. The final record distinguishes architecture examples from
  conformance fixtures.
- The inspected Autosubmit example records `startTime` later than `endTime` and
  includes absolute `file://` paths. The final record does not generalize these
  details as recommended practice.
- `rocrate-validator` documents the needed profiles and input forms but labels
  itself work in progress. The recommendation pins its version and keeps local
  fixtures rather than treating validator success as sufficient evidence.
- A native TORC YAML file can satisfy Waterology's internal workflow identity
  boundary, but WorkflowHub usefulness still depends on language support and
  meaningful workflow metadata. The final record says "candidate deposit" and
  does not promise WorkflowHub interpretation.
- The automated source-check tool returned `unclear` because semantic scoring
  was unavailable. Manual review of the fetched primary passages supported the
  four checked claims.

## Repository validation

Final validation passed on 2026-09-21:

- `pixi run pytest`: 633 passed, with one upstream AnyIO deprecation warning.
- `pixi run ruff check .`: passed.
- `pixi run waterology render --check`: generated assets are current.
- `python3 constraints/check-all.py .`: 8 of 8 constraints passed.
- `git diff --check`: passed.

## Review status

Citation and review were performed directly. No reviewer subagent was launched
because delegation was not authorized for this task. The remaining limitation
is independent review, not missing primary-source support.

Verification: PASS for the evaluation decision and cited record. Live external
service qualification remains BLOCKED until an exporter exists.
