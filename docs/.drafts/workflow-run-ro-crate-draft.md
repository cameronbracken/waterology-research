# Workflow Run RO-Crate evaluation

## Decision

Waterology should export a sealed run as a Process Run Crate by default and add
Workflow Run Crate conformance only when the archive contains an authoritative,
executable workflow definition. It should not claim Provenance Run Crate
conformance from current TORC logs or job identifiers.

The export should wrap an unchanged sealed archive payload in a new RO-Crate
directory or ZIP. Waterology's `checksums.sha256` remains the payload integrity
source. The RO-Crate metadata provides description and interoperability, not a
replacement seal.

Use the current compatible version set: RO-Crate 1.3, Workflow RO-Crate 1.1,
and Workflow Run RO-Crate 0.6. Do not copy version declarations from the older
published examples.

## Why this profile boundary fits

A sealed Waterology run always identifies an executed command or tool, its start
and finish, state, inputs or declared outputs, collected artifacts, environment
evidence, and logs. Process Run Crate represents this with a software entity and
a `CreateAction`. It does not require Waterology to claim that every run was
coordinated by a formal workflow.

Workflow Run Crate adds a `ComputationalWorkflow` main entity. That model fits a
named workflow backed by native TORC YAML. It does not fit an ad hoc direct
command merely because Waterology generated a one-job TORC wrapper around it.
The executable research workflow, not scheduler scaffolding, must be the main
entity.

Provenance Run Crate requires structured records for the tools executed inside
a workflow and the inputs and outputs of those step executions. Waterology
retains TORC workflow and job identifiers, resource summaries, and bounded job
logs, but it does not always know which tools a shell job invoked or how every
intermediate moved between jobs. Inferring those facts from logs would create
false precision. Provenance Run conformance should wait for structured step
evidence.

## Evidence from existing implementations

Autosubmit is the closest analogue because it manages climate and weather
experiments across HPC schedulers. Its Workflow Run export uses one top-level
workflow action and packages configuration, source information, logs, traces,
and selected outputs. It does not claim tool-level provenance for every job.
This supports Waterology's proposed Workflow Run boundary.

Galaxy and Sapporo follow a similar pattern. They retain native invocation or
service metadata while adding a standard workflow action, inputs, outputs, and
logs. COMPSs, StreamFlow, runcrate, and Nextflow reach Provenance Run because
their runtimes have structured access to tool or process executions. The
contrast is evidence that step-level conformance should follow recorded runtime
facts, not the existence of a scheduler graph alone.

The implementation examples also show limits. Published examples often target
old profile versions. Some retain absolute local paths, and one Autosubmit
example has inconsistent times. Large workflow crates can reach gigabytes.
Waterology needs current-version conformance tests, path and redaction checks,
and an explicit payload inclusion policy rather than treating example output as
a template to copy.

## Waterology mapping

The standard model covers the portable core without a Waterology extension:

- the run manifest becomes a `CreateAction`;
- the direct command, script, or workflow becomes its `instrument`;
- known inputs become `object` entities;
- collected outputs become `result` entities;
- start, finish, and success or failure become action properties;
- environment files, source snapshots, logs, and reports become file entities;
- scalar scientific and resource metrics become `PropertyValue` entities with
  stable identifiers and units;
- TORC can be represented as the workflow engine, with native engine traces
  linked to the run action.

Some facts should remain in native Waterology records for the first version:

- exact cancelled and lost states;
- hashes of allowlisted environment variable values;
- missing declared outputs;
- TORC workflow and job identifiers;
- scientific claim bindings and assessment dispositions;
- redaction and log-omission evidence;
- comparison tolerances and estimand definitions.

The exporter should include and describe those native files rather than flatten
semantics into unregistered JSON-LD terms. A Waterology profile is justified
only when an external consumer needs those fields.

## Archive placement and fixity

RO-Crate metadata is not a complete payload inventory. RO-Crate is designed to
work with fixity systems such as BagIt, OCFL, and Git. BagIt manifests detect
corruption but do not prove that an active attacker did not replace both a file
and its checksum. Waterology's existing SHA-256 manifest therefore remains a
valid, separate integrity layer.

Generating `ro-crate-metadata.json` inside the original archive after sealing
would break the seal. Generating it before sealing would couple an immutable
scientific archive to evolving profile metadata and make later annotation a
payload mutation. An opaque archive file inside a crate would preserve the seal
but hide outputs from standard consumers.

The practical design is a derived wrapper. Verify the sealed archive, copy its
directory unchanged under `run/`, add `ro-crate-metadata.json` at the export
root, and validate the resulting crate. `run/checksums.sha256` still verifies the
original payload, and the native verifier can inspect `run/` without treating
crate metadata as an unexpected archive member. The export may receive a
separate transport digest. The exporter must never present RO-Crate validation
as payload integrity verification.

## Downstream value and limits

WorkflowHub accepts RO-Crate ZIP submissions, and Workflow Run inherits the
Workflow RO-Crate model. A Waterology Workflow Run export can therefore be a
candidate workflow deposit when its main entity is a real workflow definition
in a language WorkflowHub can understand. A Process-only crate remains useful
for archiving and inspection but should not be advertised as a WorkflowHub
workflow.

Zenodo can preserve the crate and assign a DOI, but ordinary file acceptance is
not semantic validation. Galaxy can export and re-import its own workflow-run
crates, which demonstrates consumption of the model but not execution of TORC
workflows. Five Safes RO-Crate shows how a later profile can add request,
approval, disclosure, and redacted-publication state for sensitive settings.
That extension should not cause a general Waterology export to reveal sensitive
values.

The Python RO-Crate validator covers the three run profiles and distinguishes
required, recommended, and optional checks. It is still described as work in
progress. Waterology should pin the validator version and retain its own small,
reviewed conformance fixtures. `rocrateR` can support R-side creation and BagIt
work, but its strict profile validation also relies on the Python validator.

## Implementation boundary

A later implementation should proceed in four increments:

1. Export completed and non-completed sealed runs as Process Run Crate 0.6,
   preserving exact native state and redaction evidence.
2. Add Workflow Run Crate 0.6 only for qualifying named workflow archives.
3. Validate required and recommended rules against pinned local fixtures, then
   inspect one export with runcrate and the RO-Crate validator.
4. Add Provenance Run only after archive records capture per-step tool identity,
   action status, inputs, outputs, and intermediates without log inference.

Live WorkflowHub, Zenodo, and Galaxy qualification should be separate release
checks because this evaluation inspected documented interfaces but did not
publish or import a Waterology crate.
