# Context and token discipline

Use these rules for long autoresearch runs, remote runs, or runs with multiple
agents. Reduce repeated model work while preserving the fixed benchmark,
scientific scope, and completion criteria.

## Bound the run

- Set a benchmark run cap and, when relevant, a token or cost budget before the
  baseline. Stop at the first limit unless the user extends it.
- In tree mode, define the promotion margin, refill rule, and terminal
  conditions before testing candidates.
- Keep experiment selection inside the autoresearch loop. Treat production
  deployment, publication, presentation, and cleanup as later phases unless
  the frozen run contract includes them.
- Run deterministic preflight checks before expensive benchmarks. A failed
  preflight does not consume an experiment iteration when no benchmark ran.

## Keep durable context compact

- Use `autoresearch.md` as the concise current state and decision record. Put
  complete event history in `autoresearch.jsonl` and large logs in files.
- Record artifact paths, hashes, counts, metrics, and short failure excerpts.
  Do not paste complete logs or manifests into conversation when the files are
  available.
- At a major milestone, write a compact handoff containing the active node,
  frozen command, seed, metric, established decisions, unresolved blockers,
  and next action. Resume from that artifact instead of replaying the full
  transcript.
- Do not repeat evidence that is already recorded and verified by hash unless its
  inputs or authoritative state changed.

## Supervise tools economically

- Request bounded command output: relevant failures, summary counts, hashes,
  and a short log tail. Keep full output on disk.
- For long jobs, write or use a small machine readable status file. Poll at an
  interval matched to expected runtime and report only state changes or useful
  milestones.
- Prefer one deterministic verifier over repeated manual inspections. Rerun a
  check after a relevant change, not merely because another turn started.

## Limit duplicated agent work

- Delegate only independent work that benefits from parallel execution or a
  separate review. Give each agent a standalone brief with the minimum context,
  owned files, allowed compute, and return contract.
- Do not send full conversation history when a concise brief and artifact paths
  are sufficient. Avoid assigning multiple agents the same investigation.
- Use one implementation pass and one independent review at a meaningful
  milestone when review is warranted. Repeat review only after a relevant
  change or unresolved finding.
- Use the least costly model and reasoning level that reliably handles routine
  polling, transfers, syntax checks, and deterministic validation. Reserve
  deeper reasoning for hypothesis choice, scientific interpretation, and
  consequential review.

## Audit once, incrementally

Map each completion criterion to authoritative evidence at the start. Update
that ledger as evidence arrives. The final audit should verify the ledger and
changed state rather than reconstructing the entire run from conversation.
