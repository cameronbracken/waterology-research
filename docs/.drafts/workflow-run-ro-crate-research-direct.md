# Workflow Run RO-Crate direct research notes

Date: 2026-09-21

## Search log

The source survey used these exact query groups:

1. `Workflow Run RO-Crate profiles Process Run Crate Workflow Run Crate Provenance Run Crate specification official`
2. `Autosubmit Workflow Run RO-Crate example Zenodo provenance HPC Slurm official`
3. `runcrate 0.5 Workflow Run RO-Crate reference implementation official`
4. `Workflow Run RO-Crate implementations COMPSs Nextflow Galaxy StreamFlow WfExS Sapporo official`
5. `site:github.com/ResearchObject/workflow-run-crate examples ro-crate-metadata.json Autosubmit`
6. `site:github.com/ResearchObject/runcrate ro-crate-metadata.json example`
7. `RO-Crate validator Workflow Run profile SHACL official profile validation`
8. `RO-Crate checksum BagIt signing integrity official`
9. `nf-prov Nextflow Provenance Run Crate 1.4.0 example official GitHub`
10. `StreamFlow Provenance Run Crate official documentation`
11. `Sapporo Workflow Run RO-Crate official documentation`
12. `Galaxy Workflow Run RO-Crate export official documentation`
13. `rocrateR CRAN package documentation RO-Crate create validate`
14. `WorkflowHub RO-Crate API Workflow Run Crate support official`
15. `Zenodo RO-Crate support upload metadata official`
16. `Five Safes RO-Crate Workflow Run profile official`

Primary pages were fetched directly after discovery. The Autosubmit, Galaxy,
and Sapporo Zenodo examples were downloaded and their
`ro-crate-metadata.json` files inspected locally. The larger COMPSs, StreamFlow,
WfExS, and runcrate example archives were not downloaded because they are about
1.1 GB, 50 MB, 15 GB, and 45 MB. Their Zenodo records and official
implementation documentation were inspected instead.

## Specification findings

### Current versions and compatibility

The current profile collection is version 0.6, published 2026-09-04. Version
0.6 aligns with RO-Crate 1.3 and Workflow RO-Crate 1.1. The profile changelog
states that Workflow Run Crate and Provenance Run Crate 0.6 are not backward
compatible with RO-Crate 1.1 and Workflow RO-Crate 1.0 because the JSON-LD IRI
mappings for `ComputationalWorkflow`, `FormalParameter`, `input`, and `output`
changed. The compatibility table pairs:

- RO-Crate 1.1, Workflow RO-Crate 1.0, and WRROC 0.1 through 0.5;
- RO-Crate 1.3, Workflow RO-Crate 1.1, and WRROC 0.6.

The roadmap and published 2023 examples mostly cite profile 0.5 or earlier. Any
Waterology implementation should target the coherent 1.3/1.1/0.6 set and keep
fixture tests for older examples separate from conformance tests.

Source: <https://www.researchobject.org/workflow-run-crate/profiles/changelog.html>

### Profile ladder

| Profile | Minimum model | Additional commitment | Waterology fit |
| --- | --- | --- | --- |
| Process Run Crate 0.6 | One or more software applications and their executions, represented by `SoftwareApplication` or related tool entities and `CreateAction` entities | Connect execution to inputs with `object`, outputs with `result`, times, agent, and status when available | Fits every sealed direct or TORC run without claiming a formal workflow definition |
| Workflow Run Crate 0.6 | Process Run Crate plus Workflow RO-Crate 1.1 | Requires a `ComputationalWorkflow` main entity typed as `File`, `SoftwareSourceCode`, and `ComputationalWorkflow`; the run action uses it as `instrument` | Fits named workflows and archived TORC workflow YAML when Waterology can identify one authoritative executable workflow file |
| Provenance Run Crate 0.6 | Workflow Run Crate plus internal execution provenance | Requires tool entities and `CreateAction` records for individual tool executions; workflow `hasPart` names those tools; step and engine actions add further detail | Does not fit current archives generally because Waterology lacks reliable tool identity and per-step input/output edges for every TORC job |

The profiles are intentionally cumulative, but the paper argues against forcing
the most complex profile on simple runs. Process Run Crate exists for executions
that are not coordinated by a formal workflow, Workflow Run Crate describes a
predefined workflow, and Provenance Run Crate describes internal step
executions.

Sources:

- <https://www.researchobject.org/workflow-run-crate/profiles/>
- <https://www.researchobject.org/workflow-run-crate/profiles/process_run_crate/>
- <https://www.researchobject.org/workflow-run-crate/profiles/workflow_run_crate/>
- <https://www.researchobject.org/workflow-run-crate/profiles/provenance_run_crate/>
- <https://doi.org/10.1371/journal.pone.0309210>

### Useful standard mappings

The profiles already provide homes for most portable run facts:

- `CreateAction`: run identity, start and end times, status, executor or agent,
  command description, inputs, and outputs.
- `SoftwareApplication`, `SoftwareSourceCode`, or `ComputationalWorkflow`: the
  executed command, script, or formal workflow.
- `File`, `Dataset`, `Collection`, and `PropertyValue`: file inputs and outputs,
  directories, grouped objects, and scalar values.
- `FormalParameter` plus `exampleOfWork`: optional declared input and output
  slots and their realized values.
- `environment`: environment variable values as `PropertyValue` entities.
- `containerImage`: container registry, name, tag, and digest.
- `softwareRequirements`: software dependencies.
- Engine traces: files such as logs and reports can use `about` to refer to the
  relevant action.
- Provenance Run Crate `buildInstructions`: environment files for workflow or
  step runtime environments.
- `resourceUsage`: resource observations represented as `PropertyValue`
  entities with stable `propertyID` identifiers and explicit units.

RO-Crate metadata is descriptive, not an exhaustive file manifest. The RO-Crate
1.3 structure specification explicitly leaves fixity to mechanisms such as
BagIt, OCFL, or Git.

Sources:

- <https://www.researchobject.org/workflow-run-crate/profiles/process_run_crate/>
- <https://www.researchobject.org/workflow-run-crate/profiles/workflow_run_crate/>
- <https://www.researchobject.org/workflow-run-crate/profiles/provenance_run_crate/>
- <https://www.researchobject.org/ro-crate/specification/1.3/structure.html>

## Implementation survey

| Implementation | Advertised profile and version | Observed pattern | Relevance and caveat |
| --- | --- | --- | --- |
| Autosubmit 4.0.100+ | Workflow Run | Archives an HPC experiment as a ZIP with top-level RO-Crate metadata, workflow configuration, logs, traces, source details, and outputs. The downloaded 2023 example used RO-Crate 1.1 and WRROC 0.1, one top-level `CreateAction`, 24 formal parameters, and no per-job actions. | Closest architecture. It shows that a scheduler-backed climate workflow can remain at Workflow Run granularity. Its example also exposed absolute local `file://` paths and recorded `startTime` later than `endTime`, so it is a design example, not a conformance fixture. |
| runcrate 0.6.2 | Provenance Run | Converts CWLProv to WRROC, reports across crates, and can rerun CWL workflow crates. | Reference implementation for the detailed profile. Rerun depends on workflow-language parameter mappings and a reconstructable runtime, so conformance alone does not guarantee replay. |
| COMPSs 3.4+ | Workflow or Provenance | Records file and directory accesses, directions, command arguments, source, workflow diagram, task statistics, and environment. Users may opt out of step detail. | Confirms that Provenance Run requires runtime-level step knowledge. Waterology should not infer equivalent detail from shell logs. |
| Nextflow `nf-prov` 1.4.0+ | Provenance Run | Emits all three profiles and exposes profile selection. Current releases document careful limits on copying local and remote inputs to avoid explosive transfers. | Supports a staged path from Workflow to Provenance. It also illustrates that source URL, revision, and local-path handling materially affect crate quality. |
| Galaxy 23.1.1+ | Workflow Run | Exports the workflow definition in several forms, invocation metadata, inputs, outputs, logs, and one workflow `CreateAction`. The inspected 2023 example used WRROC 0.1. | Shows a useful export built beside existing native invocation metadata rather than replacing it. |
| StreamFlow 0.2+ | Provenance Run | Converts its internal execution database into a crate with tool and step actions and intermediate outputs. It can bundle one run or a run history. | Demonstrates the evidence threshold for Provenance Run. The paper identifies distributed execution topology as a remaining model gap. |
| WfExS 0.10.1+ | Workflow Run | Captures staged workflows, containers, inputs, outputs, and retrospective metadata, with options to consume and produce crates. | Relevant for restricted or distributed inputs. The published example is about 15 GB, which supports making payload inclusion policy explicit. |
| Sapporo 1.5.1+ | Workflow Run | Generates `ro-crate-metadata.json` in the WES run directory. The inspected example contains one workflow action, outputs, logs, WES status, and service-specific context. | Closest service-layer pattern. It retains a service-specific `wesState` term while standard fields carry portable meaning. |

Sources:

- <https://autosubmit.readthedocs.io/en/latest/userguide/provenance.html>
- <https://doi.org/10.5281/zenodo.8144612>
- <https://www.researchobject.org/runcrate/usage.html>
- <https://github.com/ResearchObject/runcrate>
- <https://compss-doc.readthedocs.io/en/stable/Sections/04_Ecosystem/05_Workflow_Provenance.html>
- <https://github.com/nextflow-io/nf-prov>
- <https://galaxyproject.org/news/2023-02-23-structured-data-exports-ro-bco/>
- <https://doi.org/10.5281/zenodo.7785861>
- <https://streamflow.di.unito.it/documentation/0.2/guide/inspect.html>
- <https://www.researchobject.org/ro-crate/wfexs>
- <https://github.com/sapporo-wes/sapporo-service>
- <https://doi.org/10.5281/zenodo.10134581>

## Waterology mapping

| Waterology evidence | Standard mapping | Gap or policy |
| --- | --- | --- |
| `RunManifest.run_id` | `CreateAction.@id`, preferably a stable URI or local fragment derived from the run ID | Keep the Waterology ID as `identifier` even if a UUID URI is used for strict profile guidance. |
| Start, finish, terminal state | `startTime`, `endTime`, `actionStatus`; optional `error` | Map completed to `CompletedActionStatus`; failed, cancelled, and lost require explicit policy because the profile names completed and failed statuses but Waterology distinguishes more terminal states. Preserve the native manifest for exact state. |
| `command.json` | Human-readable `CreateAction.description`; command or script entity as `instrument` for Process Run | The profile warns that a displayed command is not necessarily re-executable. Keep structured arguments in the archive. |
| `manifest.json` declared and collected artifacts | `FormalParameter` declarations where a workflow interface exists; collected files as `result`; missing outputs remain native Waterology evidence | Do not emit absent files as results. A Waterology extension is unnecessary if the native manifest remains in the crate. |
| Workflow `input_files` and hashes | Input `File` entities linked through `object`; optional formal parameters | RO-Crate can record `sha256`, but Waterology remains authoritative for identity and access instructions. Restricted inputs may stay external. |
| `metrics.json` scientific metrics | `PropertyValue` entities, preferably grouped in a `Dataset.variableMeasured`; each metric needs a stable `propertyID`, numeric value, and unit when known | Metric names and values map cleanly. Estimand, tolerance, and comparison semantics need Waterology vocabulary or links to the study contract. |
| TORC resource metrics | Provenance Run `resourceUsage` `PropertyValue` entities with `propertyID` and QUDT or explicit units | Existing summaries lack stable semantic identifiers for every field. Define Waterology/TORC identifiers only for documented quantities. |
| `environment.json` environment-file hashes | Environment files as crate `File` entities; workflow or tool `buildInstructions`; software dependencies via `softwareRequirements` | Controller and worker evidence must remain distinct. Hash-only environment variable records cannot be represented as actual environment values without weakening redaction. Keep them in native evidence and describe only their presence. |
| `ExecutorReference` and `torc.json` | TORC as `SoftwareApplication`; workflow execution as `CreateAction`; optional engine `OrganizeAction`; engine traces use `about` | Workflow ID and job IDs have no dedicated WRROC property. Keep them in the native files initially or define narrow `waterology:` terms later. |
| `torc-workflow.yaml` and native TORC YAML | Workflow Run `mainEntity` when it is the authoritative executable workflow definition | Generated one-job wrappers are implementation scaffolding. A direct command archive should not be promoted to Workflow Run merely because TORC wrapped it. |
| `job-logs.json`, stdout, stderr, result report | Engine-specific trace files linked with `about` or `subjectOf` | Redacted logs must be labeled as redacted. Omitted large logs remain documented in native records. |
| Git commit and `source.tar.zst` | `SoftwareSourceCode`, `codeRepository`, and `version`; source archive as a crate file | The committed source tree is stronger than a remote URL alone. Preserve the original commit object and source checksums. |
| `checksums.sha256` | Separate fixity layer, included as a crate file and described as Waterology's archive manifest | Do not translate it into a claim that RO-Crate validates payload fixity. |
| `ClaimRecord` and assessments | No direct WRROC term for scientific claim support, JSON Pointer selection, or passport disposition | Keep native claim records and later define a Waterology profile only if external consumers exist. `CreativeWork`/`Claim` mappings alone would lose binding semantics. |
| Redaction configuration and output | No general WRROC redaction-state model | Keep native redaction evidence. Five Safes demonstrates derived, possibly redacted public crates but does not make ordinary WRROC a redaction audit format. |

Local evidence inspected:

- `src/waterology/core/archive.py`
- `src/waterology/core/claims.py`
- `src/waterology/core/config.py`
- `src/waterology/core/records.py`
- `src/waterology/core/reproduction.py`
- `src/waterology/torc/provider.py`
- `src/waterology/torc/runs.py`
- `src/waterology/torc/workflow.py`
- `docs/superpowers/plans/2026-09-06-workflow-reproducibility.md`
- `docs/validation/2026-09-06-workflow-reproducibility.md`

## Fixity and crate placement

RO-Crate 1.3 supports attached packages, detached metadata, ZIP files, BagIt,
OCFL, and repository deposits. Its metadata document is not an exhaustive
inventory. The implementation notes recommend BagIt for full payload checksums
and warn that BagIt detects corruption but not malicious replacement unless a
separate signature is used.

Waterology already seals the native archive with `checksums.sha256`. Replacing
that with BagIt would add packaging complexity without improving current
SHA-256 payload verification. A first exporter should:

1. verify the sealed archive before export;
2. create a new RO-Crate export directory or ZIP;
3. copy the sealed archive directory unchanged under `run/` in the crate;
4. add `ro-crate-metadata.json` at the crate root, outside the sealed `run/`
   directory;
5. describe `run/checksums.sha256` as the integrity manifest for the
   Waterology payload;
6. validate the crate metadata independently;
7. compute a digest for the final export as a transport checksum if desired.

This makes the crate a derived interoperability wrapper. It does not mutate a
sealed run and does not make mutable JSON-LD part of the original seal. An
inside-the-seal design would require generating the crate metadata before
sealing, couple archive schema changes to profile updates, and make later
metadata enrichment indistinguishable from evidence mutation. A crate that
contains only the sealed archive as one opaque ZIP or tar file would preserve
fixity but hide individual outputs from ordinary RO-Crate consumers. Nesting the
unchanged archive under `run/` lets the native verifier operate on that directory
without treating `ro-crate-metadata.json` as an unexpected archive member, while
RO-Crate can still describe each nested output as a data entity.

Sources:

- <https://www.researchobject.org/ro-crate/specification/1.3/structure.html>
- <https://www.researchobject.org/ro-crate/specification/1.3/appendix/implementation-notes.html>
- <https://www.ietf.org/rfc/rfc8493>

## Validation and downstream reach

- `rocrate-validator` supports base RO-Crate, Workflow RO-Crate, Process Run,
  Workflow Run, and Provenance Run profiles. It can validate directories, ZIP
  archives, and HTTP resources and can select required, recommended, or optional
  severity. Its documentation still labels the software work in progress.
- WorkflowHub accepts an RO-Crate ZIP through its submission API. Workflow Run
  and Provenance Run inherit Workflow RO-Crate, but registry usefulness still
  depends on a meaningful `ComputationalWorkflow` main entity and supported
  workflow language. Process-only crates should not be advertised as
  WorkflowHub workflow submissions.
- Zenodo accepts arbitrary record files and provides DOI and bit-level
  preservation. RO-Crate-specific metadata transfer requires separate tooling
  such as `rocrate-zenodo` or `rocrate-inveniordm`; Zenodo acceptance alone does
  not validate WRROC conformance.
- Galaxy can export and re-import workflow invocation crates. This is evidence
  of real workflow-run consumption, not a promise that Galaxy can execute a
  TORC workflow.
- Five Safes RO-Crate extends workflow metadata for request, approval,
  execution, disclosure control, and derived public redaction in trusted
  research environments. It is a downstream profile to monitor, not a reason to
  include sensitive values in a general Waterology crate.
- `rocrateR` 0.1.0 creates, reads, bags, and validates general RO-Crates from R.
  Strict profile validation uses the Python validator. It does not remove the
  need for Waterology's own WRROC mapping and conformance fixtures.

Sources:

- <https://github.com/crs4/rocrate-validator>
- <https://rocrate-validator.readthedocs.io/en/stable/>
- <https://about.workflowhub.eu/developer/ro-crate-api/>
- <https://about.workflowhub.eu/Workflow-RO-Crate/1.1/>
- <https://help.zenodo.org/docs/deposit/about-records/>
- <https://github.com/ResearchObject/ro-crate-zenodo>
- <https://www.researchobject.org/ro-crate/galaxy>
- <https://w3id.org/5s-crate/>
- <https://cran.r-project.org/package=rocrateR>

## Candidate decision

Adopt a tiered export:

1. Every eligible sealed run exports as Process Run Crate 0.6.
2. A run additionally declares Workflow Run Crate 0.6 only when its archive
   identifies and contains an authoritative `ComputationalWorkflow` main
   entity. Named native TORC workflows qualify; ad hoc direct commands and
   generated one-job wrappers do not.
3. Do not declare Provenance Run Crate until Waterology records tool identity,
   per-step actions, and input/output edges as structured evidence rather than
   inferring them from logs.
4. Wrap the unchanged sealed payload in a derived RO-Crate export. Keep
   `checksums.sha256` authoritative for payload fixity.
5. Use RO-Crate 1.3, Workflow RO-Crate 1.1, and WRROC 0.6 together. Validate
   required and recommended rules in CI with pinned validator fixtures.
6. Start with standard terms and native Waterology files. Delay a Waterology
   JSON-LD profile until at least claim, metric, or scheduler fields have a real
   external consumer.

Confidence: high for the profile and placement decision; medium for downstream
behavior beyond documented upload, inspection, and re-import paths because no
live WorkflowHub, Zenodo, or Galaxy submission was performed.
