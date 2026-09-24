# Bigpowers and context-mode evaluation

Recommendation after checking existing behavior: do not adopt either plugin or
schedule the proposed handoff and search-index prototypes. The initial review
identified plausible ideas, but did not establish an unmet need large enough
to justify those additions.

A narrower issue is confirmed: Waterology's MCP log tools expose complete log
contents through their service layer. A small change to those readers may be
worthwhile independently of either plugin. This review changes no runtime code,
skills, dependencies, or installed plugins.

## Follow-up implementation

After this evaluation, the user requested the narrow MCP improvement. The
[MCP log tools](mcp-log-reading.md) now use bounded readers with pagination and
literal search. The original full-log Python service remains available, so the
probe below records that baseline rather than the new MCP response. The broader
plugin and index recommendations remain deferred. The user plans an independent
context-mode trial.

## Sources

Reviewed on 2026-09-24:

- [bigpowers](https://github.com/danielvm-git/bigpowers/tree/812d57a917675f8b9929d1519f5038dc1d01917f),
  commit `812d57a917675f8b9929d1519f5038dc1d01917f`.
  Its [license](https://github.com/danielvm-git/bigpowers/blob/812d57a917675f8b9929d1519f5038dc1d01917f/LICENSE)
  is MIT. Copied or adapted material would need notices and Waterology attribution.
- [context-mode](https://github.com/mksglu/context-mode/tree/5a92b7caaf0086d04b87cc03a82505c891aa8254),
  commit `5a92b7caaf0086d04b87cc03a82505c891aa8254`.
  Its [license](https://github.com/mksglu/context-mode/blob/5a92b7caaf0086d04b87cc03a82505c891aa8254/LICENSE)
  is Elastic License 2.0. Do not copy its implementation into Waterology's MIT
  package without resolving the applicable license requirements. No upstream
  code or prompt text was incorporated in this change.

## Incremental value over Waterology

| Candidate | What already exists | Actual gap | Decision |
| --- | --- | --- | --- |
| Bigpowers handoff state | `skills/session-log/SKILL.md` already calls for branch/worktree, active identities, frozen decisions, failures, blockers, evidence links, and restart steps. | No automatically refreshed, structured summary of every interactive session. | Defer. Another format does not ensure the agent records the right facts. |
| Bigpowers verification trace | `core/claims.py` already distinguishes unresolved anchors, missing claims, evidence verification, and authored assessments. | No demonstrated Waterology decision that its story-coverage rules improve. | Do not port. Its delivery thresholds are not scientific acceptance criteria. |
| Context-mode compact resume view | Session records retain task paths, commits, attempts, and native session IDs; Claude and Codex adapters support native resume. Narrative handoffs cover decisions. | Generic cross-session event capture and retrieval are not present. | Defer. A view over existing records cannot reconstruct decisions those records never captured. |
| Context-mode searchable artifact index | Bounded source-reading guidance, files on disk, and ordinary text search are available. | Repeated relevance-ranked searches across an unknown corpus are not provided by the log reader. | Defer until that workload is demonstrated. |
| Context-mode output limiting | Native tools can select excerpts, but Waterology's MCP log endpoints lack range/size arguments. | A real unbounded service response. | Consider a small native reader change, without a new index or executor. |

The source links for these candidates are bigpowers
[session-state](https://github.com/danielvm-git/bigpowers/blob/812d57a917675f8b9929d1519f5038dc1d01917f/skills/session-state/SKILL.md)
and [gate-trace](https://github.com/danielvm-git/bigpowers/blob/812d57a917675f8b9929d1519f5038dc1d01917f/skills/gate-trace/SKILL.md),
and context-mode's
[store](https://github.com/mksglu/context-mode/blob/5a92b7caaf0086d04b87cc03a82505c891aa8254/src/store.ts),
[resume snapshot](https://github.com/mksglu/context-mode/blob/5a92b7caaf0086d04b87cc03a82505c891aa8254/src/session/snapshot.ts),
and [truncation utilities](https://github.com/mksglu/context-mode/blob/5a92b7caaf0086d04b87cc03a82505c891aa8254/src/truncate.ts).
These are observations of the pinned checkouts, not claims about later releases.

## What the output probe establishes

[Probe source](validation/plugin-output-probe.py) and
[recorded results](validation/plugin-output-probe.json) are retained. Run:

```bash
pixi run python docs/validation/plugin-output-probe.py
```

The probe calls the actual `services.session_logs` and `core.sessions` log
reader on deterministic synthetic files. Project/session lookup and path
resolution are mocked; this does not exercise authorization, MCP transport,
or a running agent. The full payload is measured before any host truncation.
The alternatives are an 8,192-byte tail and `rg -n -C 2 'ERROR|WARNING'`.

| Event lines | Complete service JSON, bytes | Search excerpt, bytes | Seeded records found by search | Seeded records found in tail |
| --- | ---: | ---: | ---: | ---: |
| 200 | 17,119 | 794 | 2/2 | 1/2 |
| 2,000 | 172,916 | 812 | 2/2 | 0/2 |
| 20,000 | 1,748,913 | 830 | 2/2 | 0/2 |

The fixtures deliberately contain identifiable error and warning terms. This
is a check of payload growth and a simple alternative, not a retrieval-quality
benchmark. It does not test context-mode, compare latency, estimate tokens,
measure agent accuracy, or prove that text search finds every relevant fact.
It shows that a large reduction on this task needs no search index. It also
shows why silently replacing a full log with its tail would lose older adverse
evidence.

The source path is direct:

- `src/waterology/mcp/server.py`: `read_session_logs` and `read_run_logs` expose
  service results without range arguments. `_bounded_tool` handles errors; its
  name does not imply a response-size budget.
- `src/waterology/services.py`: `session_logs` and `run_logs` pass through the
  corresponding readers.
- `src/waterology/core/sessions.py`: `read_session_logs` reads every attempt's
  complete events and stderr files.
- `src/waterology/core/archive.py`: `read_archive_logs` reads complete stdout
  and stderr files.

A separate inspection found that `core/study_driver.py` embeds every prior
attempt in each candidate prompt. That suggests another growth point, but no
long-study performance or context-loss result was measured here.

## Why the broader pieces do not yet earn their cost

Bigpowers provides a maintained structured handoff and workflow conventions.
Waterology already specifies the relevant handoff content. Enforcing another
state file adds synchronization with Git, session records, and notes. It would
be justified by recurring restart failures that a defined field or automatic
update demonstrably prevents. No such failure was established in this review.
Existing guidance is not proof that handoffs are always followed; it is a reason
to inspect that failure before inventing another representation.

Context-mode addresses a useful workload: large tool outputs and repeated
search across retained material, especially when an agent cannot easily use
local shell tools. Its FTS5 ranking is lexical rather than a guarantee of
semantic understanding. An index adds ingestion, invalidation, deletion,
project isolation, and source-location maintenance. Automatic session capture
also requires runtime hooks and policy for which events to retain.

A smaller derived index would still carry several of those obligations.
Moreover, the pinned snapshot implementation explicitly ignores its `maxBytes`
option. Its reference-oriented output should not be assumed to provide a hard
size bound merely because it is called a compact snapshot.

License differences reinforce the implementation cost but are not the primary
reason to defer. Even a permissive implementation would need a demonstrated
benefit over existing reads and handoffs.

## Conditions for reconsidering

- Revisit structured handoffs after repeated restarts lose the same required
  fact despite using the existing session log. Test one corrected handoff field
  or trigger against that failure first.
- Revisit an index when agents repeatedly search many unknown files and ordinary
  search or explicit source selection is insufficient. Compare the same task
  with simple search, a lightweight index, and the upstream tool if appropriate.
  Measure answer completeness, adverse-evidence retrieval, bytes, latency, and
  maintenance work.
- If MCP log reads are used regularly, a bounded reader is the first change to
  consider: select attempt/stream and range, expose total size and continuation,
  keep full logs on disk, and make truncation explicit. Preserve access to older
  errors. This is a Waterology API change and does not require either plugin.

The original handoff and index prototype recommendation is withdrawn pending
evidence of the corresponding workload. The later bounded-reader implementation
is recorded above.
