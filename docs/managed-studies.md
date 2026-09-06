# Autonomous research and engineering

A managed study records the objective, authority and execution contract once.
All evaluations use its pinned TORC profile, including local evaluations. CLI,
MCP and dashboard run requests resolve the same configured default profile.
Generic run commands cannot bypass an active managed study's ownership.

Use research mode to answer a scientific question. Use engineering mode to meet
a specification under constraints. Engineering acceptance requires every declared
threshold to pass. Research mode retains the measurements and requires an explicit
conclusion supported by assessed claims. Neither mode equates process completion
with scientific support.

## Prepare a contract

Initialize the project and configure a TORC profile using
[configuration](configuration.md) and [TORC execution](torc.md). Create a committed
baseline experiment with the evaluation command, environment files, outputs and
metric extractors in `waterology.toml`. Generated outputs should be ignored by
Git and kept inside declared artifact roots. The existing experiment API requires
a committed variant after the experiment's base commit.

Keep evaluation code, test data and dependency locks outside allowed candidate
paths. Allowed paths name files or directory prefixes, not shell globs.
For local input files, record SHA-256 identities in `input_files`. For external
or restricted inputs, put immutable accession/version identifiers and access
limitations in `evaluation`. Those declarations do not prove remote input access.

Save a NestedText contract as `study-contract.nt`, for example:

```nestedtext
mode: engineering
objective: Reduce model runtime while preserving numerical parity
baseline_experiment: exp-baseline
allowed_paths:
    - src/model
evaluation:
    benchmark: fixed qualification cases v1
    seed: 42
    prediction_task: not applicable, implementation parity
acceptance:
    -
        name: max_error
        unit: m
        direction: minimize
        threshold: 0.000001
    -
        name: elapsed
        unit: s
        direction: minimize
        threshold: 30
promotion_metric: elapsed
promotion_margin: 0.5
max_iterations: 10
max_seconds: 1800
max_retries: 1
max_parallel: 1
stop_behavior: cancel
local_checks:
    - declared lightweight syntax check
uncertainty: not estimated, deterministic qualification cases
```

The numbers above are illustrative settings, not measured results. Choose the
thresholds and budgets for the actual task. `max_iterations` counts all submitted
attempts, including retries. `max_retries` additionally bounds retries of each
candidate. Only a sealed, terminal failed evaluation can be retried. Its commit
must remain unchanged. Unknown outcomes never trigger a new submission.

`max_seconds` is a wall-clock study deadline from authorization, including time
between controller invocations. It prevents new work after the deadline. With
`drain`, already authorized jobs may finish beyond it. With `cancel`, the
controller requests cancellation. CPU-hours and model token/cost budgets are not
metered by this implementation. Do not represent an unobservable budget as
machine-enforced.

## Start and resume

```bash
waterology study create study-contract.nt --profile local --authorized-by "user approved the saved contract"
waterology study show STUDY_ID
waterology study enqueue STUDY_ID EXPERIMENT_ID
waterology study advance STUDY_ID
waterology study watch STUDY_ID
```

Replace identifiers, profile and authorization text with actual values. Do not
invent approval. Creating a study queues the baseline. `advance` performs one
controller tick. `watch` repeatedly reconciles evaluations and submits queued
candidates. It waits for additional candidates while the study remains within
budget. Both reload durable state and can resume without another approval.
Managed workflow commands emit NestedText by default. Use the global
`--output-format json` option for scripts that require JSON. MCP responses
and sealed archives retain their machine format.

Candidate proposals can come from the active agent or an explicitly configured
bounded runtime driver:

```bash
waterology study driver STUDY_ID --runtime codex --max-proposals 5
waterology study run STUDY_ID
```

The driver creates an owned experiment and supervised agent session for each
proposal, then queues the committed result for TORC evaluation. It generates
candidates sequentially and waits for evidence before proposing another one.
Separately queued independent candidates can use `max_parallel` evaluation slots.
The proposal cap counts generation attempts. The same study deadline applies.
Runtime permissions remain authoritative. Driver configuration does not grant
shell, remote or filesystem access, and cannot guarantee that an arbitrary
runtime setup is unattended. Validate the actual runtime before a long campaign.

## Stop and recover

```bash
waterology study stop STUDY_ID
waterology study show STUDY_ID
```

A stop marker is written before waiting for an active controller operation.
New work stops and the saved drain/cancel policy applies to evaluations and
candidate sessions. A completed outcome is preserved. A cancellation failure
remains blocked, with its saved identity available for recovery.

The study directory records intent before TORC submission and before candidate
session launch. If the response is lost, reconcile the recorded run/session ID.
A known supervised session can be recovered without launching another one.
An unknown TORC submission or a candidate without a recorded runtime attempt
remains blocked for inspection. There is no "assume failed and retry" option.

Profile, environment or protected-input changes block the loop. Restore the
saved configuration or create a newly authorized study. Do not edit queued,
running, unknown or collecting candidates. Managed collection uses a saved
configuration, verifies the candidate commit and rejects unchanged prior outputs.
Index repair refuses to discard unresolved managed attempts.

## Compare, assess and report

```bash
waterology compare-runs RUN_BASE RUN_CANDIDATE --baseline RUN_BASE
waterology claim "Observed benchmark value" RUN_ID --selector /elapsed
waterology claim-assess CLAIM_ID PASS "reviewer" "The stated value and units match the measurement"
waterology claims
waterology report RUN_BASE RUN_CANDIDATE --baseline RUN_BASE --destination reports/comparison
```

Comparisons retain every requested run. Deltas require verified archives with
compatible fixed source, environment, input and metric identities. Missing,
legacy, failed and incompatible runs remain visible with reasons. No uncertainty
interval is inferred from point estimates. The declared uncertainty method and
archived metrics remain available for a domain-specific analysis.

A claim references an archived JSON member and JSON pointer, with the selected
value and content hash. Array pointers support table rows encoded as JSON.
Reference integrity and claim support are separate: an intact file does not
prove its attached prose. Claim assessments append author, disposition and note.
Contradictory records are retained. Missing evidence remains UNVERIFIED and
changed evidence becomes STALE, using the passport vocabulary.

Research studies can stop with a supported negative, positive or inconclusive
conclusion:

```bash
waterology study conclude STUDY_ID CLAIM_ID --author "reviewer" --conclusion "The evaluated evidence is inconclusive under this setup"
```

The cited claims must belong to the study and have explicit PASS or EXPLAINED
assessments. The controller verifies those references, not the scientific
judgment itself. A conclusion can be recorded after a stop or exhausted budget
without authorizing new compute. An existing conclusion cannot be overwritten.
Candidate sessions follow the saved stop policy before cleanup is complete.
No deployment or publication follows automatically.

The report bundle includes Quarto source, comparison JSON, CSV, figure code,
claim assessments and a provenance manifest. It does not redistribute research
inputs. Regenerate and render it with the optional report environment:

```bash
pixi run -e reports python reports/comparison/render.py
pixi run -e reports quarto render reports/comparison/report.qmd --to html
```

Package users can install the `reports` extra for Plotly and provide their own
Quarto installation. Tables remain available without Plotly. Export never
replaces an existing directory or writes inside Git/Waterology control state.

The dashboard adds Studies and Compare runs views, links to recorded code
changes, and verified artifact downloads. Active HTML/SVG artifacts download
instead of executing within the dashboard's origin.

## Literature records

Check provider access before starting a literature or deep-research task:

```bash
waterology research-access
```

The package reads `ZOTERO_API_KEY` and `OPENALEX_API_KEY` from the process
environment. Missing keys produce warnings. The check reports presence only,
never their values, and does not claim the keys are valid. Export them through
your shell or approved environment manager. A running agent may need its
environment refreshed after keys are added.

```bash
waterology discover "reservoir operations" --after 2020-01-01 --limit 20
waterology source-decision SEARCH_ID SOURCE_ID include "Relevant evaluation design"
waterology source-add "Agency report" "stable locator or local path" "Access and version notes"
```

Discovery makes one bounded OpenAlex request. It retains the query, dates,
provider failures, DOI deduplication provenance and explicit selection notes.
Set `OPENALEX_API_KEY` in the local environment when required. Credentials and
credential-bearing HTTP error messages are not stored. Metadata access does not
establish full-text access. Use the existing bibliography validator for DOI and
citation checks before writing scholarly claims.

The client follows OpenAlex's [paging](https://help.openalex.org/api/paging/)
and [filtering](https://help.openalex.org/api/filtering/) interfaces. This feature
does not claim improved search recall or ranking accuracy.

### Automatic Zotero capture

Configure the library once using a NestedText settings file:

```nestedtext
library_type: user
library_id: YOUR_NUMERIC_LIBRARY_ID
collection_name: Project reference library
capture: selected
download_pdfs: true
```

Replace the library ID with the selected personal or group library ID. Save this
input outside `.zotero.nt`, then run `waterology zotero configure SETTINGS.nt`.
This writes a project `.zotero.nt` with a stable collection key. Existing
`zotero.nt` files remain readable. It makes no network request. The first sync
creates that collection if absent. An API key with write access to the chosen
library is required. Keys stay outside settings.

An included search result or a registered local/agency source is automatically
queued and synchronized when configured. By default, unselected search hits
remain discovery records. Use `capture: discovered` to collect every returned
record instead. Deep-research, literature-review and the researcher agent also
capture consulted sources found with other search tools:

```nestedtext
title: Title verified from the source
doi: 10.1234/example
authors:
    - Author name verified from the source
publication_date: 2025-01-01
url: https://example.org/article
pdf_url: https://example.org/article.pdf
```

These are placeholders, not actual bibliography entries. Use
`waterology zotero capture source.nt` when a source is read or cited. For a PDF
already in the project, replace `pdf_url` with `pdf_path: papers/article.pdf`.
The reference retains metadata even when a lawful public PDF cannot be found.
Local locators are kept locally and are not sent as Zotero URL fields.

```bash
waterology zotero status
waterology zotero sync --limit 20
```

Queue records live in `.waterology/references/*.nt`. PDF bytes are retained under
its `pdfs/` directory with SHA-256 identities and uploaded as child attachments.
PDFs must be at most 30 MB and pass a PDF signature check. No authenticated
publisher session is used. Paywalls, quotas, offline services and failed uploads
retain pending status separately from citation metadata. A downloaded PDF is
not automatically a read or verified source.

DOIs and stable source identities deduplicate project records. Existing Zotero
items with an exact DOI match are reused without replacing their metadata or
removing their existing collection memberships. Object keys and destination are
saved before writes. Retries reuse pinned PDF bytes and reconcile a matching
remote file checksum. An altered destination or conflicting attachment remains
blocked. Batches report remaining work and rotate attempted failures so they
cannot indefinitely hide later pending references.

These services use the [Zotero Web API](https://www.zotero.org/support/dev/web_api/v3/write_requests)
through [Pyzotero](https://pyzotero.readthedocs.io/en/latest/). Package users install
the optional `zotero` extra. The development Pixi environment includes it.
The Zotero desktop application receives items through its normal account sync.
Direct desktop writes and WebDAV file uploads are not implemented here.

## Remember and improve

Use `waterology learning context "TASK TERMS"` before substantial project work.
Only relevant verified lessons with unchanged content and evidence are returned.
Managed study ticks automatically record outcome observations as proposed
lessons. Candidate sessions receive matching verified lessons automatically.

The `project-learning` skill records supported corrections, failed approaches
and verified fixes at checkpoints. A lesson contains a trigger, action, outcome,
tags and project-relative evidence paths. Save it in `.nt` format and run
`waterology learning remember lesson.nt`. Assess support with
`waterology learning assess LESSON_ID verified --author NAME --note RATIONALE`.
Verification is an explicit evidence judgment, not a frequency-based confidence
score. Changes to either the lesson or its evidence invalidate that judgment.

Use rejected or superseded assessments without erasing history. Shared behavior
changes are proposals with verified lesson identifiers, a concrete change and a
validation plan, created by `waterology learning improve improvement.nt`.
They do not automatically edit shared skills, global preferences, permissions
or frozen scientific protocols. Session-log remains the narrative handoff.

Learning records are local project state under `.waterology/learning/` and are
not committed automatically. Preserve selected records alongside their evidence
when archiving or handing off a project. Optional learning errors are recorded
in `.waterology/learning-warning.nt` without blocking compute reconciliation.

## Human-readable formats

NestedText is the default for authored study contracts, lessons, reference
manifests and the new workflow command output. Known schema fields such as
thresholds and iteration limits are validated and converted to their intended
types. Arbitrary domain metadata stays as strings, so station `00123` retains
its leading zeros. Changing metadata representation changes evaluation identity;
do not convert a frozen running study's contract in place.

Existing TOML project/environment settings remain supported. `.nt`, `.toml` and
legacy `.json` study contracts are accepted. JSON remains at API boundaries and
inside existing immutable archives. Human-readable displays are not a lossless
serialization for arbitrary machine values: absent mapping fields are omitted.
Use `waterology --output-format json ...` for typed machine round trips.

## Validation boundaries

The repository includes deterministic study tests and
`scripts/smoke-managed-study.py`, which starts an isolated loopback TORC server,
runs two synthetic evaluations, restarts the controller between ticks and exports
a report. Run it only with a new destination directory. Its fixed synthetic
values test plumbing and acceptance behavior, not model skill.

Live remote profiles, native Windows/Linux execution and real unattended model
sessions need separate qualification in their selected environment. A passing
local smoke test does not establish readiness on a remote host.

See the [implementation validation record](validation/2026-09-05-managed-workflows.md)
for completed checks and the remaining limits.
The [learning/Zotero validation record](validation/2026-09-05-ecc-zotero.md)
covers this extension and separates offline verification from live account access.
