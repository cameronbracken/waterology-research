# Workflow Run RO-Crate evaluation

For usage, read [RO-Crate integration](ro-crate.md). Automatic and manual exports
are implemented. This evaluation describes the recommended profile design; the
[implementation boundary](#implementation-boundary) below distinguishes current
behavior from that recommendation.

## Design target

Current exports use the compatible RO-Crate 1.1 / Workflow Run 0.5 set supported
by the pinned validator. The newer set below is an upgrade target, not the
implemented declaration.

The longer-term profile target is to export every eligible sealed run as a
[Process Run Crate 0.6](https://www.researchobject.org/workflow-run-crate/profiles/process_run_crate/)
and add
[Workflow Run Crate 0.6](https://www.researchobject.org/workflow-run-crate/profiles/workflow_run_crate/)
conformance only when the archive contains an authoritative, executable workflow
definition. It should not claim
[Provenance Run Crate 0.6](https://www.researchobject.org/workflow-run-crate/profiles/provenance_run_crate/)
conformance from current TORC logs or job identifiers.

The export should wrap an unchanged sealed archive payload in a new RO-Crate
directory or ZIP. Waterology's `checksums.sha256` remains the payload integrity
source. The RO-Crate metadata provides description and interoperability, not a
replacement seal. The RO-Crate specification states that its metadata document
is not an exhaustive manifest and is designed to coexist with fixity systems
such as BagIt, OCFL, and Git
([RO-Crate 1.3 structure](https://www.researchobject.org/ro-crate/specification/1.3/structure.html)).

Use the current compatible version set: RO-Crate 1.3, Workflow RO-Crate 1.1,
and Workflow Run RO-Crate 0.6. The WRROC 0.6 changelog states that the profile
updated its JSON-LD mappings for RO-Crate 1.3 and is not backward compatible
with the older RO-Crate 1.1 and Workflow RO-Crate 1.0 context pair
([WRROC changelog](https://www.researchobject.org/workflow-run-crate/profiles/changelog.html)).
Do not copy version declarations from the older published examples.

## Why this profile boundary fits

A sealed Waterology run always identifies an executed command or tool, its start
and finish, state, declared and collected artifacts, environment evidence, and
logs. Process Run Crate represents this with a software entity and a
`CreateAction`, connected to inputs through `object` and outputs through
`result`. It does not require Waterology to claim that every run was coordinated
by a formal workflow
([Process Run Crate](https://www.researchobject.org/workflow-run-crate/profiles/process_run_crate/)).

Workflow Run Crate adds a `ComputationalWorkflow` main entity described under
Workflow RO-Crate. That model fits a named workflow backed by native TORC YAML.
It does not fit an ad hoc direct command merely because Waterology generated a
one-job TORC wrapper around it. The executable research workflow, not scheduler
scaffolding, must be the main entity
([Workflow Run Crate](https://www.researchobject.org/workflow-run-crate/profiles/workflow_run_crate/);
[Workflow RO-Crate 1.1](https://about.workflowhub.eu/Workflow-RO-Crate/1.1/)).

Provenance Run Crate requires structured records for the tools executed inside
a workflow and the inputs and outputs of those executions. Waterology retains
TORC workflow and job identifiers, resource summaries, and bounded job logs,
but it does not always know which tools a shell job invoked or how every
intermediate moved between jobs. Inferring those facts from logs would create
false precision. Provenance Run conformance should wait for structured step
evidence
([Provenance Run Crate](https://www.researchobject.org/workflow-run-crate/profiles/provenance_run_crate/)).

The profile boundary follows the collection's intended progression. The
reference paper defines Process Run for generic computations, Workflow Run for
computations orchestrated by a predefined workflow, and Provenance Run for
internal step executions. It also argues that separate profiles avoid forcing
the most complex model on simple use cases
([Leo et al. 2024](https://doi.org/10.1371/journal.pone.0309210)).

## Evidence from existing implementations

[Autosubmit](https://autosubmit.readthedocs.io/en/latest/userguide/provenance.html)
is the closest analogue because it manages climate and weather experiments
across HPC schedulers. Its Workflow Run export packages configuration, source
information, logs, traces, and selected outputs under one top-level workflow
action. It does not claim tool-level provenance for every job. This supports
Waterology's proposed Workflow Run boundary. The downloaded
[Autosubmit example](https://doi.org/10.5281/zenodo.8144612) used older WRROC
0.1 metadata, exposed absolute local `file://` paths, and recorded `startTime`
later than `endTime`. It is a useful architecture example, not a conformance
fixture.

[Galaxy](https://galaxyproject.org/news/2023-02-23-structured-data-exports-ro-bco/)
and [Sapporo](https://github.com/sapporo-wes/sapporo-service) follow a similar
pattern. They retain native invocation or service metadata while adding a
standard workflow action, inputs, outputs, and logs. The inspected
[Galaxy](https://doi.org/10.5281/zenodo.7785861) and
[Sapporo](https://doi.org/10.5281/zenodo.10134581) examples also target early
profile versions.

COMPSs, StreamFlow, runcrate, and Nextflow reach Provenance Run because their
runtimes have structured access to tool or process executions:

- [COMPSs](https://compss-doc.readthedocs.io/en/stable/Sections/04_Ecosystem/05_Workflow_Provenance.html)
  records file access direction, task statistics, source, and environment and
  lets users select Workflow or Provenance detail.
- [StreamFlow](https://streamflow.di.unito.it/documentation/0.2/guide/inspect.html)
  converts its execution database into a provenance archive with internal run
  detail.
- [runcrate](https://www.researchobject.org/runcrate/usage.html) converts
  CWLProv, reports on actions, and can rerun qualifying CWL crates.
- [Nextflow `nf-prov`](https://github.com/nextflow-io/nf-prov) 1.4.0 and later
  can emit all three profiles.

The contrast supports a scientific boundary: step-level conformance should
follow recorded runtime facts, not the existence of a scheduler graph alone.
The implementations also expose operational limits. WfExS documents staged
workflow, container, input, and output capture, while its published example can
be many gigabytes
([WfExS use case](https://www.researchobject.org/ro-crate/wfexs)). Nextflow's
implementation discussion limits automatic local input copying to avoid
unbounded transfers. Waterology therefore needs current-version conformance
tests, path and redaction checks, and an explicit payload inclusion policy.

## Waterology mapping

| Waterology evidence | RO-Crate mapping | Initial policy |
| --- | --- | --- |
| `RunManifest` identity and times | `CreateAction` with `@id`, `startTime`, and `endTime` | Preserve `run_id` as an identifier. |
| Terminal state | `actionStatus` and optional `error` | Map completed and failed portably; retain cancelled and lost exactly in `manifest.json`. |
| `command.json` | Process tool as `instrument`; command display in `description` | Keep structured arguments because the profile warns that a displayed command is not necessarily re-executable. |
| Declared and collected artifacts | Optional `FormalParameter` declarations and collected `result` entities | Do not emit absent files as results. Keep missing-output evidence native. |
| Input files and hashes | `File` or `Dataset` entities in `object` | Retain Waterology hashes and access instructions for restricted inputs. |
| Scientific metrics | `PropertyValue`, preferably under `Dataset.variableMeasured` | Require stable `propertyID` and unit when known. Keep estimand and tolerance semantics in the study contract. |
| TORC resource summaries | Provenance `resourceUsage` values | Add only quantities with documented identifiers and units. |
| Environment evidence | Environment files, `buildInstructions`, `softwareRequirements`, and optional environment values | Keep controller and worker evidence distinct. Do not expose hashed secret values as if they were environment settings. |
| TORC reference and logs | TORC `SoftwareApplication`, optional engine action, and trace files linked with `about` | Keep workflow and job IDs in native files until an external consumer justifies extension terms. |
| Native TORC workflow YAML | Workflow `mainEntity` for qualifying named workflows | Generated one-job wrappers do not qualify by themselves. |
| Git source and commit | `SoftwareSourceCode`, `codeRepository`, `version`, and source archive file | Preserve the source tree and original commit object. |
| `checksums.sha256` | Described file containing the Waterology payload manifest | Do not equate crate validation with archive verification. |
| Claims and assessments | Native Waterology records included as files | WRROC has no direct equivalent for JSON Pointer evidence binding or passport dispositions. |
| Redaction and omitted logs | Native Waterology records and descriptive metadata | Label redacted output; never reconstruct omitted content. |

The standard already covers environment variables, container images, software
dependencies, engine-specific traces, and resource measurements
([Process Run Crate](https://www.researchobject.org/workflow-run-crate/profiles/process_run_crate/);
[Workflow Run Crate](https://www.researchobject.org/workflow-run-crate/profiles/workflow_run_crate/);
[Provenance Run Crate](https://www.researchobject.org/workflow-run-crate/profiles/provenance_run_crate/)).
The exporter should use these terms before defining a Waterology context. A
Waterology profile is justified only when an external consumer needs semantics
that the native files currently preserve better.

## Archive placement and fixity

RO-Crate supports attached directories, detached metadata, ZIP files, BagIt,
OCFL, and repository deposits
([RO-Crate 1.3 structure](https://www.researchobject.org/ro-crate/specification/1.3/structure.html)).
Its BagIt guidance recommends cryptographic manifests but warns that a manifest
detects corruption, not deliberate replacement of both content and checksums
([RO-Crate implementation notes](https://www.researchobject.org/ro-crate/specification/1.3/appendix/implementation-notes.html);
[BagIt RFC 8493](https://www.ietf.org/rfc/rfc8493)). Waterology's existing
SHA-256 manifest therefore remains a valid, separate integrity layer.

Generating `ro-crate-metadata.json` inside the original archive after sealing
would break the seal. Generating it before sealing would couple an immutable
scientific archive to evolving profile metadata and make later annotation a
payload mutation. An opaque archive file inside a crate would preserve the seal
but hide outputs from standard consumers.

Use a derived wrapper instead:

1. Verify the sealed Waterology archive.
2. Create a new RO-Crate directory or ZIP.
3. Copy the sealed archive directory unchanged under `run/`.
4. Add `ro-crate-metadata.json` at the wrapper root.
5. Describe `run/checksums.sha256` as the manifest for the copied native payload.
6. Validate RO-Crate metadata independently.
7. Optionally compute a transport digest for the finished export.

This design preserves standard entity paths and the original seal. The native
verifier can inspect `run/` without treating crate metadata as an unexpected
archive member. The exporter must never present RO-Crate validation as payload
integrity verification.

## Downstream value and limits

[WorkflowHub's submission API](https://about.workflowhub.eu/developer/ro-crate-api/)
accepts RO-Crate ZIP files. Workflow Run inherits Workflow RO-Crate, so a
Waterology Workflow Run export can be a candidate deposit when its main entity
is a real workflow definition in a language WorkflowHub can interpret. A
Process-only crate remains useful for archiving and inspection but should not be
advertised as a WorkflowHub workflow.

Zenodo accepts research-object files, assigns DOIs, and provides bit-level
preservation, but ordinary file acceptance is not semantic validation
([Zenodo records](https://help.zenodo.org/docs/deposit/about-records/)). Separate
[RO-Crate Zenodo tooling](https://github.com/ResearchObject/ro-crate-zenodo)
can transfer selected metadata and warns that not all fields map correctly.

Galaxy can export and re-import workflow invocation crates
([Galaxy RO-Crate use case](https://www.researchobject.org/ro-crate/galaxy)).
This demonstrates consumption of the model, not execution of TORC workflows.
[Five Safes RO-Crate](https://w3id.org/5s-crate/) shows how a later profile can
add request, approval, disclosure, and derived-publication state for sensitive
settings. It is not a reason to expose sensitive values in a general export.

The [RO-Crate validator](https://github.com/crs4/rocrate-validator) covers base,
Workflow, Process Run, Workflow Run, and Provenance Run profiles and can check
required, recommended, or optional rules. Its documentation labels the tool
work in progress. Waterology should pin its version and retain small reviewed
fixtures. [`rocrateR`](https://cran.r-project.org/package=rocrateR) can create,
read, bag, and validate general crates from R, but strict profile validation
also relies on the Python validator.

## Implementation boundary

The exporter creates an automatic derived crate when sealing a run, with manual
copies through `waterology archive export-crate RUN_ID DEST`. It emits Process
Run 0.5 on RO-Crate 1.1. Workflow Run 0.5 and Workflow RO-Crate 1.0 declarations
are added only when an executor reference identifies an archived submitted TORC
definition. For Slurm this is the generated Slurm definition. Command-backed
registrations without that evidence remain Process Run crates.

This supported version set is deliberate: pinned `roc-validator==0.11.4` implements
these profiles but not the newer set recommended above. The optional integration
selects the profile and REQUIRED severity explicitly, verifies the validator
version, and retains a structured success, failure, skipped, or error record.
Real positive and negative fixture checks cover both exported profiles.

Automatic packaging failure is isolated from the sealed execution result, and
manual failure leaves diagnostics for inspection. Metadata uses archived evidence
without falling back to current project configuration or exporting the local
repository URI. See the [usage guide](ro-crate.md#profiles-and-validation) for the
validation boundary and recovery instructions.

Provenance Run remains out of scope until archive records capture per-step tool
identity, action status, inputs, outputs, and intermediates without log
inference. Live WorkflowHub, Zenodo, and Galaxy qualification should be separate
release checks because this evaluation inspected documented interfaces but did
not publish or import a Waterology crate.

## Sources

- <https://www.researchobject.org/workflow-run-crate/profiles/>
- <https://www.researchobject.org/workflow-run-crate/profiles/changelog.html>
- <https://www.researchobject.org/workflow-run-crate/profiles/process_run_crate/>
- <https://www.researchobject.org/workflow-run-crate/profiles/workflow_run_crate/>
- <https://www.researchobject.org/workflow-run-crate/profiles/provenance_run_crate/>
- <https://doi.org/10.1371/journal.pone.0309210>
- <https://www.researchobject.org/ro-crate/specification/1.3/structure.html>
- <https://www.researchobject.org/ro-crate/specification/1.3/appendix/implementation-notes.html>
- <https://www.ietf.org/rfc/rfc8493>
- <https://autosubmit.readthedocs.io/en/latest/userguide/provenance.html>
- <https://doi.org/10.5281/zenodo.8144612>
- <https://www.researchobject.org/runcrate/usage.html>
- <https://compss-doc.readthedocs.io/en/stable/Sections/04_Ecosystem/05_Workflow_Provenance.html>
- <https://github.com/nextflow-io/nf-prov>
- <https://streamflow.di.unito.it/documentation/0.2/guide/inspect.html>
- <https://galaxyproject.org/news/2023-02-23-structured-data-exports-ro-bco/>
- <https://doi.org/10.5281/zenodo.7785861>
- <https://www.researchobject.org/ro-crate/wfexs>
- <https://github.com/sapporo-wes/sapporo-service>
- <https://doi.org/10.5281/zenodo.10134581>
- <https://github.com/crs4/rocrate-validator>
- <https://about.workflowhub.eu/developer/ro-crate-api/>
- <https://about.workflowhub.eu/Workflow-RO-Crate/1.1/>
- <https://help.zenodo.org/docs/deposit/about-records/>
- <https://github.com/ResearchObject/ro-crate-zenodo>
- <https://www.researchobject.org/ro-crate/galaxy>
- <https://w3id.org/5s-crate/>
- <https://cran.r-project.org/package=rocrateR>
