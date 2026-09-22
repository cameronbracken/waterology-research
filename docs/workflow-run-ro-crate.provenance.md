# Workflow Run RO-Crate evaluation provenance

## Run record

- Date: 2026-09-21
- Branch: `research/ro-crate-evaluation`
- Base commit: `735e6c5dd476a19c217dec0545ba7145c16e367c`
- Research rounds: specification and paper; Autosubmit and runcrate; secondary
  implementations; fixity and validation; downstream consumers; Waterology
  source mapping; claim and URL verification.
- Verification: PASS for the evaluation decision and cited record.
- External service qualification: BLOCKED because no Waterology exporter exists
  to submit, publish, or import.

## Artifacts

- Plan: `docs/.plans/workflow-run-ro-crate.md`
- Direct research notes: `docs/.drafts/workflow-run-ro-crate-research-direct.md`
- Uncited draft: `docs/.drafts/workflow-run-ro-crate-draft.md`
- Cited draft: `docs/.drafts/workflow-run-ro-crate-cited.md`
- Verification: `docs/.drafts/workflow-run-ro-crate-verification.md`
- Final record: `docs/workflow-run-ro-crate.md`

## Accepted sources

Primary specifications and standards:

- Workflow Run RO-Crate profile collection and 0.6 changelog.
- Process Run Crate 0.6, Workflow Run Crate 0.6, and Provenance Run Crate 0.6.
- Workflow RO-Crate 1.1.
- RO-Crate 1.3 structure and implementation notes.
- BagIt RFC 8493.

Paper and scholarly metadata:

- Leo et al. 2024, _Recording provenance of workflow runs with RO-Crate_,
  <https://doi.org/10.1371/journal.pone.0309210>.
- OpenAlex metadata lookup for the paper DOI.

Implementations and examples:

- Autosubmit provenance documentation and Zenodo example 8144612.
- runcrate usage documentation and repository.
- COMPSs workflow provenance documentation.
- Nextflow `nf-prov` repository and release documentation.
- Galaxy structured export documentation and Zenodo example 7785861.
- StreamFlow provenance documentation.
- WfExS RO-Crate use case.
- Sapporo repository and Zenodo example 10134581.

Validation and downstream use:

- CRS4 `rocrate-validator` repository and documentation.
- WorkflowHub Workflow RO-Crate profile and submission API.
- Zenodo records documentation and `ro-crate-zenodo` repository.
- Galaxy RO-Crate use case.
- Five Safes RO-Crate profile.
- CRAN `rocrateR` package documentation.

Local Waterology evidence:

- Archive, records, configuration, claims, comparison, reproduction, workflow,
  TORC provider, TORC run, and TORC workflow source modules.
- Workflow reproducibility implementation plan and validation record.

## Consulted but not used as authority

- Search-result summaries, which were used only to locate primary material.
- GitHub issues and pull requests discussing resource usage, paths, and
  implementation bugs. They informed caveat checks but do not establish profile
  requirements.
- Older profile pages and early examples. They support implementation history,
  not current conformance.
- Secondary package-index and tutorial mirrors when official project pages were
  available.

## Rejected or bounded sources

- The published COMPSs example archive was not downloaded because it is about
  1.1 GB. Official COMPSs documentation and the Zenodo record were sufficient
  for the implementation survey.
- The published WfExS example archive was not downloaded because it is about
  15 GB. Official WfExS documentation and the Zenodo record were sufficient.
- The StreamFlow and runcrate example archives were not downloaded because the
  profile specification, paper, documentation, and records supplied the needed
  design evidence.
- No live WorkflowHub, Zenodo, Galaxy, or validator service result was treated
  as available. Documented interfaces are not equivalent to Waterology
  qualification.

## Verification evidence

- All 28 distinct external URLs in the final cited draft returned HTTP 200 on
  2026-09-21.
- The Autosubmit, Galaxy, and Sapporo example metadata files were inspected
  locally after download from their Zenodo records.
- Four decision-critical claims were checked against fetched primary passages.
  Automated semantic scoring was unavailable, so support was reviewed manually.
- A review found and corrected the original wrapper layout. The final design
  nests the sealed archive under `run/`, preserving native verification while
  keeping crate metadata outside the seal.
- The first full test run had 632 passes and one failure caused by the roadmap's
  lowercase checked-marker invariant. The evaluation checklist now uses
  equivalent uppercase markers, and the focused regression test passed.
- Final repository validation passed: 633 tests, Ruff, generated-asset check,
  all eight constraints, and `git diff --check`.

## Unresolved gaps

- No independent reviewer was used because delegation was not authorized.
- Validator behavior against a generated Waterology crate cannot be checked
  until an exporter and fixtures exist.
- WorkflowHub language recognition for native TORC YAML requires live or source
  qualification before claiming useful registry ingestion.
- Provenance Run conformance remains out of scope until Waterology records
  structured per-step tool and dataflow evidence.
