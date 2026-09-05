# Project learning, Zotero and readable formats

Implemented as an extension of the managed-workflow worktree. See
[managed studies](../../managed-studies.md) for commands and configuration.
See the [validation record](../../validation/2026-09-05-ecc-zotero.md) for tests,
review dispositions and live-access limits.
No ECC installer, hooks, background observer or agents are installed.

## Evidence and selection

Inspected ECC at commit `e04ea0b9cc8248686edf5ac751cadff550e162b8`, including
the [skill catalog](https://ecc.tools/skills) and
[agent inventory](https://github.com/affaan-m/ECC/tree/e04ea0b9cc8248686edf5ac751cadff550e162b8/agents).
The repository is MIT, copyright 2026 Affaan Mustafa.

| ECC candidate | Waterology overlap | Decision |
| --- | --- | --- |
| [continuous-learning-v2](https://github.com/affaan-m/ECC/blob/e04ea0b9cc8248686edf5ac751cadff550e162b8/skills/continuous-learning-v2/SKILL.md) | Session logs exist, but reusable lesson assessment and retrieval were missing | Adapt project scope, atomic lessons, retained evidence and improvement proposals into project-learning |
| [strategic-compact](https://github.com/affaan-m/ECC/blob/e04ea0b9cc8248686edf5ac751cadff550e162b8/skills/strategic-compact/SKILL.md) | Session-log and autoresearch token discipline already cover handoffs | Extend session-log checkpoint fields; no additional compaction skill or runtime hook |
| research-ops, deep-research and scholarly review skills | Existing deep-research, literature-review, source comparison and research review | Do not import |
| iterative-retrieval | Existing bounded source summarization, multi-hop literature search and delegation | Do not import |
| planner, code-reviewer, Python/C++ and framework reviewer agents | Existing quality workflow and research review agents, with language conventions | Do not import a second set of agent roles |
| eval and orchestration frameworks | Existing study contracts, archived comparisons, TORC and supervised sessions | Do not introduce another scheduler, evaluation store or loop controller |

Waterology does not turn repetition into scientific confidence. Evidence hashes
prove identity, while an explicit assessment records whether a lesson is useful.
Changed evidence or lesson text makes the assessment stale. Verified project
lessons can guide later work. Changes to shared skills remain reviewable proposals.
No global Codex memory or preferences are modified by the learning service.

## Zotero behavior

One project settings file binds a selected personal or group library and a
stable collection key. Selected sources, agency/local registrations, and sources
read through other paper tools feed the same queue. A project can opt to save all
discovery results. The research skills make that capture part of the task rather
than a separate request after writing.

Use environment `ZOTERO_API_KEY` and `OPENALEX_API_KEY`. Report missing keys at
skill entry and provider access. Never log values or credential-bearing provider
errors. Configuration selects a library; the presence of a key alone does not
authorize choosing a group or uploading unrelated files.

Use Pyzotero with the official Web API. Reuse exact DOI matches, preserve existing
collection memberships and metadata, save intended object keys before writes,
and retain separate metadata/PDF status. PDFs use bounded public downloads or
explicit project-relative local files. Preserve pinned bytes for retries and
verify existing Zotero file checksums before declaring an ambiguous upload done.
Unavailable PDFs, quota failures and offline access do not lose citations.

## Format decision

[NestedText](https://nestedtext.org/en/latest/file_format.html) fits handwritten
contracts and narrative lessons. It has strings, lists and mappings, so typed
validation belongs at the schema boundary. Known numeric fields are converted;
arbitrary station IDs and metadata are not guessed. Existing TOML configuration
stays in place. JSON remains for API interchange and immutable historical
archives, with an explicit CLI option for scripts requiring typed JSON output.

## Implementation and qualification

- Human input/output: NestedText/TOML/legacy JSON loader, default NestedText
  workflow output, explicit JSON machine output and updated contract examples.
- Learning: immutable lesson content, evidence hashes, append-only reviews,
  stale detection, scoped retrieval, managed outcome capture, candidate-context
  integration and shared improvement proposals.
- References: OpenAlex metadata normalization, automatic selected-source capture,
  optional discovered-source capture, durable Zotero queue, bounded sync, stable
  destinations/keys, retained PDFs and retry reconciliation.
- Access: environment credential checks with no values exposed, CLI/MCP preflight
  and missing-key warnings in research workflows.
- Behavior: project-learning is the only new skill. Existing quality, handoff,
  research and autoresearch skills are extended individually. Researcher runtime
  definitions are regenerated from the canonical source.

Deterministic checks cover missing credentials, key use, lesson staleness,
optional-service failure isolation, DOI and stable-locator deduplication,
partial attachments, destination drift and preserved pending work. Live Zotero
account writes require the selected library and available credentials. A fake
gateway establishes state-machine behavior, not live account readiness.

The public PDF URL checks reject private addresses and credential-bearing URLs
but are not a complete hostile-network sandbox. DNS is resolved again by the HTTP
client. Use runtime network controls when processing untrusted arbitrary URLs.
Automatic learning captures explicit managed events and skill checkpoints;
there is no claim of observing every tool call in every runtime.
