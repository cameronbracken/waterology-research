---
name: waterology-deep-research
description: >
  Run a thorough, source-heavy investigation on any topic. Use when the user
  asks for deep research, a comprehensive analysis, an in-depth report, or a
  multi-source investigation. Produces a cited research brief with provenance
  tracking.
metadata:
  claude-command:
    name: deepresearch
    argument-hint: <topic>
---

<!-- Generated from skills/deep-research/SKILL.md. Do not edit. -->

# Deep Research

Use `waterology-writing-style` for the research brief and synthesis.

At entry, run `waterology research-access` or MCP `research_access`. Use
`OPENALEX_API_KEY` and `ZOTERO_API_KEY` from the environment when present. If a
key is missing, give a concise warning before trying that provider. Never print
keys or ask for them in chat. Presence does not verify provider permissions.

Read [workflow.md](references/workflow.md) and follow it for the complete plan,
scale, evidence, drafting, citation, review, and delivery protocol.

When handing a complete investigation to another agent, use
`research-coordinator` and supply the scope, plan and approval record when
available, owned worktree and artifacts, source and compute limits, and whether
the parent will dispatch specialists. The coordinator follows this skill. An
agent already coordinating the investigation keeps ownership rather than
recursively delegating to another coordinator. Direct execution remains valid
for a small task or when delegation adds no value.

In an initialized Waterology project, build the reference library while
researching. Use `literature_search`/`waterology discover` for recorded searches.
Mark relevant consulted sources included with `source-decision`; this queues
them for the configured Zotero project collection. For sources found through
other search tools, use MCP `zotero_capture` or `waterology zotero capture source.yaml`
as soon as they are read or cited. Include DOI, title, authors, publication date,
stable URL and a lawful PDF URL or existing project-relative PDF path when known.
Metadata-only inspection is not full-text reading.

Resume pending work with `waterology zotero sync` before final delivery. Report
metadata and PDF status separately. Missing credentials, offline Zotero, a
paywall or storage limits leave pending work and must not erase research results.
Use existing library settings without repeated approval. Do not silently choose
a different library or upload private source files outside the authorized scope.

Coordinator when a complete investigation is delegated: `research-coordinator`.
Specialists: `researcher`, `research-syntesizer`, `research-verifier`, `research-reviewer`.
Output: a cited brief in `docs/` (or `papers/`) with a `.provenance.md` sidecar.
