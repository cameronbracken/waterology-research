# Codex Plugin Consolidation Design

Date: 2026-08-24

Status: Approved in conversation, pending written review

## Summary

Waterology will replace the useful parts of the Elements of Style and
Superpowers plugins with two compact, research focused skills. The first skill
will provide general prose and scientific writing guidance, with optional
user preferences supplied by local configuration. The second will provide proportional software quality guidance without
mandatory planning ceremonies.

The migration will remove the disabled `double-shot-latte` and `superpowers`
plugins and remove `elements-of-style` after Waterology provides its replacement.
`episodic-memory` will remain installed until Waterology has a tested session
search replacement. OpenAI maintained plugins and authenticated connectors will
remain separate because they provide runtime tools and external service access,
not overlapping instruction bundles.

## Goals

1. Reduce overlapping Codex workflow plugins without losing useful behavior.
2. Give Waterology a concise writing standard for documentation and research
   artifacts.
3. Match the direct, quantitative, and careful voice found in user-selected
   papers without copying paper text.
4. Preserve verification, debugging, testing, review, persistence, and Git
   isolation practices in a lighter workflow.
5. Keep concurrent Codex and Claude Code sessions in separate worktrees.
6. Credit public domain and MIT sources in each adapted file and in the
   repository attribution ledger.
7. Preserve one canonical skill set across Claude Code, Codex, and OpenCode.

## Non-goals

This change will not:

- Import the complete Superpowers skill suite.
- Require brainstorming, a written specification, an implementation plan,
  test driven development, a worktree, and separate review for every change.
- Reimplement OpenAI browser, document, spreadsheet, presentation, PDF, Sites,
  Calendar, Slack, or desktop application tools.
- Import the full 1918 text of _The Elements of Style_.
- Copy prose from selected papers or try to reproduce publisher editing.
- Replace `episodic-memory` in this release.
- Delete plugin caches before configuration and marketplace ownership are
  verified.

## Installed plugin boundary

The consolidation applies to third party workflow plugins only.

| Plugin | Decision | Reason |
| --- | --- | --- |
| `waterology` | Refresh | Install the new Waterology release after replacement checks pass. |
| `elements-of-style` | Replace, then uninstall | A compact Waterology skill can provide the needed prose guidance. |
| `superpowers` | Adapt a small subset, then uninstall | The full methodology adds more ceremony than the normal workflow needs. |
| `double-shot-latte` | Uninstall | It is disabled, Claude specific, and unnecessary when agents receive clear persistence guidance. |
| `episodic-memory` | Keep temporarily | It provides working cross-conversation search through a hook, MCP server, SQLite index, and embeddings. |
| OpenAI maintained plugins | Keep | They provide host capabilities and supported artifact workflows. |
| Calendar and Slack | Keep | They provide authenticated external service access. |

The Superpowers marketplace must remain configured while it supplies
`episodic-memory`.

## Writing skill

Waterology will add one `writing-style` skill with two layers.

### Base prose layer

The base layer applies to documentation, plans, commit messages, user facing
text, comments, logs, and explanations. It will:

- Use active voice and concrete language.
- Put the result before process details.
- Omit needless words and repeated conclusions.
- Avoid sales language, common AI phrasing, excessive headings, and unnecessary
  restatement.
- Prefer short sentences over long clause chains.
- Follow the punctuation, Markdown, and vocabulary preferences in local
  user guidance.
- Use plain ASCII punctuation unless a scientific symbol requires Unicode.

The skill will summarize the relevant public domain principles from William
Strunk Jr.'s 1918 _The Elements of Style_. It will not bundle the complete book.

### Scientific prose layer

The scientific layer activates for manuscripts, abstracts, reports, figure
captions, research summaries, and technical findings. It will add guidance
inferred from four first-author papers published from 2015 through 2025:

- Open with the practical or scientific problem, narrow to the gap, and state
  the contribution.
- Use direct first-person plural verbs for research actions.
- Define the period, spatial scale, resolution, threshold, dataset, and
  infrastructure assumptions early.
- Present evidence before interpretation.
- Distinguish observations, possible mechanisms, and implications.
- Calibrate causal claims with language such as `may`, `likely`, `suggests`,
  and `indicates` when uncertainty warrants it.
- State limitations directly and end with the scientific or operational
  consequence.
- Include enough method, data, code, and provenance detail to support reuse.

The editing pass will reduce repeated openings such as "In this study," shorten
clause chains, normalize terminology, and reject unsupported novelty claims.

The skill will keep its compact rules in `SKILL.md` and place the scientific
voice notes in a focused reference file. Existing paper and research writing
skills will link to this skill instead of duplicating its rules.

## Research software quality skill

Waterology will add one `research-software-quality` skill with short references
for verification, debugging, testing, review, persistence, and worktree safety.
The skill will scale its process to the risk and size of the task.

### Proportional workflow

- Every completion claim requires fresh evidence from the command that proves
  it.
- Behavior changes should receive a focused regression test when practical.
- Test driven development is preferred for clear behavior changes. It is not
  required for documentation, exploratory analysis, generated files, or
  trivial edits.
- Debugging starts by reproducing the symptom and gathering evidence before
  changing code.
- Reviewers and verifiers are used for substantial deliverables, risky changes,
  and explicit review requests. Routine patches do not require a separate
  review cycle.
- Agents continue while the requested outcome and next action remain clear.
  They stop when user input, new authority, or an external state change is
  required.

The skill will not impose mandatory brainstorming, specifications,
implementation plans, approval checkpoints, subagent review, or worktrees on
every task.

## Worktree cutoff

A session must use a worktree when any of these conditions is true:

- Another session may write to the same repository.
- The task changes executable code, tests, dependencies, build files, CI,
  schemas, plugin manifests, agent definitions, skills, hooks, or generated
  assets.
- The task spans several related files or needs an isolated test cycle.
- The current checkout contains unrelated changes.

A worktree is optional only when all of these conditions are true:

- This is the only writing session.
- The change affects documentation, comments, formatting, or one non-generated
  file.
- The change does not alter runtime or agent behavior.
- The current checkout is clean.

Skills and agent instructions count as behavior even when stored as Markdown.
Read-only sessions may share a checkout.

When parallel writing is planned, `main` becomes the integration lane. Each
writing session receives a named branch and worktree. Before deciding, the
agent inspects the current branch, repository status, linked worktrees, and
whether it is already inside a linked worktree. The agent never creates a
nested worktree or overwrites an existing branch or path.

## Agent and skill integration

The writer agent and prose producing research skills will reference
`writing-style`. The reviewer will check claim strength, terminology, and prose
clarity. The verifier will require fresh command output before a success claim.
All four canonical agents will receive concise persistence and worktree
ownership rules where relevant.

References will flow in one direction:

```text
research workflow skill -> writing-style
research software task -> research-software-quality
research-software-quality -> reviewer or verifier agent when warranted
```

The new skills will not invoke each other automatically. Existing skills will
link to the smallest relevant capability to avoid circular triggers and repeated
instruction loading.

## Runtime packaging

The new root skills remain canonical. Claude Code and Codex plugin manifests
will expose them from `skills/`. The OpenCode installer will use the existing
runtime adapter. Generated agent files will be refreshed from canonical agent
definitions and committed.

The release will bump Waterology from `0.2.0` to `0.3.0` because it adds two
user visible skills and changes agent behavior.

## Attribution

The writing skill will credit:

- William Strunk Jr., _The Elements of Style_ (1918), public domain, with the
  Project Gutenberg source.
- Local user preferences and an original stylistic analysis of four
  first-author papers. The skill will cite the papers by DOI and will not copy
  passages from them.

The research software quality skill will credit the specific adapted
Superpowers skills under the MIT license. Adaptation will extract principles
and rewrite them for Waterology rather than copy the complete workflows.

Each adapted file will carry a short source note. `ATTRIBUTION.md` will record
source repositories, versions or commits when available, licenses, adapted
ideas, and omitted material.

## Migration and rollback

Migration will follow this order:

1. Implement the replacement skills and agent changes in a dedicated worktree.
2. Run repository, packaging, runtime install, and generated file checks.
3. Refresh Waterology in Codex and start a new session to confirm the new skills
   are visible.
4. Update the user level `AGENTS.md` reference from Elements of Style to the
   Waterology writing skill.
5. Uninstall `elements-of-style`, `double-shot-latte`, and `superpowers` through
   supported Codex plugin management.
6. Confirm that `episodic-memory`, OpenAI plugins, connectors, and the
   Superpowers marketplace remain configured.
7. Inspect configuration and caches. Remove only cache entries that have no
   remaining plugin or marketplace reference.

If Waterology installation or skill discovery fails, the existing writing
plugin remains installed while the problem is corrected. Plugin removal occurs
only after the replacement passes its checks. Cache cleanup is last and does
not affect rollback because removed marketplace plugins can be reinstalled.

## Testing

Automated checks will cover:

- Valid skill frontmatter, names, descriptions, and reference paths.
- The two-layer writing routing rules.
- Worktree decisions for clean, dirty, concurrent, behavioral, documentation,
  and already-isolated cases.
- Agent rendering for Claude Code, Codex, and OpenCode.
- Plugin manifests, wheel contents, attribution links, and version consistency.
- Project and user scoped installation dry runs.
- Existing CLI, renderer, doctor, constraints, and package tests.

The worktree cases will be skill fixtures or content validation. This change
does not add a second worktree manager or advance the separate experiment
runtime worktree subsystem.

Final verification will run the full test suite, Ruff, project constraints,
generated agent drift checks, wheel installation tests, and a new Codex session
smoke test. The migration report will list plugins kept, removed, refreshed,
and deferred.
