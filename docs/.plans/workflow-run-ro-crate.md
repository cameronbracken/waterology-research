# Workflow Run RO-Crate evaluation plan

Status: completed 2026-09-21

## Decision to make

Decide which Workflow Run RO-Crate profile a sealed Waterology run should
conform to, how the crate should relate to the sealed archive, and which
Waterology records need standard mappings or extensions.

The evaluation will recommend a starting profile and implementation boundary.
It will not implement an exporter or change the archive schema.

## Research questions

1. What does each Process Run Crate, Workflow Run Crate, and Provenance Run Crate
   profile require, and which profile matches one sealed Waterology execution?
2. How do Autosubmit, runcrate, COMPSs, Nextflow, Galaxy, StreamFlow, WfExS, and
   Sapporo emit or consume these profiles in practice?
3. Where do Waterology's declared outputs, source commit, environment evidence,
   input identities, metrics, TORC workflow and job identifiers, assessments,
   claims, and redaction state map into the standard model?
4. Which Waterology concepts lack a standard term and need a small extension?
5. Should `ro-crate-metadata.json` live inside each sealed archive, wrap an
   archive export, or be generated as a separate derived artifact?
6. How should Waterology retain `checksums.sha256` as the integrity source while
   avoiding claims that RO-Crate provides fixity or signing?
7. What interoperability is supported by validators, WorkflowHub, Zenodo,
   Galaxy, and Five Safes RO-Crate?

## Sources and evidence

Use primary material where available:

- Workflow Run RO-Crate profile specifications and profile collection.
- Workflow Run RO-Crate paper and official examples.
- RO-Crate specification and validator documentation.
- Autosubmit documentation and emitted example crate, read first among
  implementations.
- runcrate documentation, source, and emitted example crate.
- COMPSs, Nextflow `nf-prov`, Galaxy, StreamFlow, WfExS, and Sapporo
  documentation or repositories.
- WorkflowHub API/profile documentation and Five Safes RO-Crate profile.
- Waterology source models, tests, archive payloads, and workflow documentation.

Repository or documentation pages may establish implementation behavior. The
paper will support history and design claims, not substitute for current
profile requirements.

## Comparison dimensions

For each profile or implementation, record:

- profile version and conformance relationship;
- required and recommended entities;
- process, workflow, action, and step granularity;
- input, output, software, environment, agent, and time representation;
- scheduler or HPC identifiers;
- metrics and validation-result representation;
- checksum, signing, archive, redaction, and sensitive-data behavior;
- validator and example availability;
- downstream consumer support;
- fit, gaps, and migration cost for Waterology.

## Scale and ownership

This is a broad implementation survey. The normal deep-research route would use
separate researchers for specifications and implementations. This run remains
directly owned because delegation was not requested. Batched searches and
primary-source retrieval will keep the survey bounded. The implementation list
is broad, but Autosubmit and runcrate receive detailed inspection; the remaining
implementations establish corroborating patterns and interoperability.

## Planned artifacts

- `docs/.drafts/workflow-run-ro-crate-research-direct.md`: queries, source notes,
  and the comparison matrix.
- `docs/.drafts/workflow-run-ro-crate-draft.md`: uncited synthesis.
- `docs/.drafts/workflow-run-ro-crate-cited.md`: claim-to-source checked draft.
- `docs/.drafts/workflow-run-ro-crate-verification.md`: URL, claim, and scope
  checks with FATAL, MAJOR, and MINOR findings.
- `docs/workflow-run-ro-crate.md`: final decision record.
- `docs/workflow-run-ro-crate.provenance.md`: provenance and unresolved gaps.
- `ROADMAP.md`: mark the evaluation bullets complete only when the final record
  supports them. Preserve the user's uncommitted restructuring in the main
  checkout; integration will require reconciliation.

## Task ledger

| Task | Status | Evidence |
| --- | --- | --- |
| Inspect current Waterology records and archive model | Complete | `src/waterology/core/records.py`, `archive.py`, `claims.py`; workflow plan and validation record |
| Read profile specifications and paper | Complete | `docs/.drafts/workflow-run-ro-crate-research-direct.md` |
| Inspect Autosubmit and runcrate examples | Complete | Autosubmit metadata inspected locally; runcrate documentation and published example record inspected |
| Survey other implementations and downstream consumers | Complete | Implementation matrix and source list in direct research notes |
| Build Waterology mapping and gap analysis | Complete | Waterology mapping in direct research notes |
| Decide profile, crate placement, and extension boundary | Complete | Candidate decision in direct research notes |
| Draft, cite, verify, and revise | Complete | Final record and provenance sidecar |
| Run repository documentation checks | Complete | 633 tests, Ruff, render check, 8 constraints, and whitespace check passed |

## Verification log

- 2026-09-21: Confirmed the current checkout has unrelated uncommitted
  `ROADMAP.md` changes. Created isolated branch `research/ro-crate-evaluation`
  and worktree `.worktrees/research-ro-crate-evaluation` from commit `735e6c5`.
- 2026-09-21: `waterology research-access` found configured OpenAlex and Zotero
  credentials. Presence does not establish provider permission.
- 2026-09-21: Project lesson retrieval was unavailable because this repository
  is not initialized with `waterology.toml`. The failure does not block the
  evaluation.
- 2026-09-21: Confirmed that the current profile set is WRROC 0.6 with RO-Crate
  1.3 and Workflow RO-Crate 1.1. The 0.6 changelog marks the workflow and
  provenance profiles incompatible with the older 1.1/1.0 context pair.
- 2026-09-21: Downloaded and inspected the Autosubmit, Galaxy, and Sapporo
  example metadata. Larger published examples were bounded to their Zenodo
  records and official implementation documentation.
- 2026-09-21: The first full test run had 632 passes and one documentation-test
  failure because lowercase checked tasks are reserved for the six platform
  slices. Changed the five completed evaluation tasks to the equivalent `[X]`
  form; the focused regression test then passed.
- 2026-09-21: Final validation passed: 633 tests, Ruff, generated-asset check,
  all eight constraints, and `git diff --check`.

## Decision log

- 2026-09-21: Bound the work to evaluation and design. Export implementation is
  a later change requiring tests and archive-schema review.
- 2026-09-21: Use direct research rather than subagents because the operator did
  not authorize delegation.
- 2026-09-21: Give Autosubmit and runcrate deeper treatment than the secondary
  implementation survey, following the roadmap's stated priority.
- 2026-09-21: Adopt Process Run 0.6 as the universal baseline, add Workflow Run
  0.6 only for authoritative workflow definitions, defer Provenance Run, and
  place the unchanged sealed archive under `run/` in a derived crate wrapper.
