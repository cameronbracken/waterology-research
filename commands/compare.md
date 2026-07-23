---
description: Compare multiple sources on a topic and produce a source-grounded matrix of agreements, disagreements, and confidence.
argument-hint: <topic>
---

<!-- Adapted from Feynman (companion-inc/feynman, MIT). See ATTRIBUTION.md. -->

Compare sources for: $ARGUMENTS

Tools: `WebSearch`/`WebFetch` and paper search (Consensus MCP when connected); the `Task` tool to launch the `researcher` (gathering) and `verifier` (citations) agents.

Derive a short slug from the comparison topic (lowercase, hyphens, no filler words, at most 5 words). Use it for all files in this run.

Requirements:
- Before starting, outline the comparison plan: which sources to compare, which dimensions to evaluate, expected output structure. Write it to `outputs/.plans/<slug>.md`. Summarize briefly and continue immediately unless the user asked to review the plan first.
- Use the `researcher` subagent to gather source material when the set is broad, and the `verifier` subagent to verify sources and add inline citations to the final matrix.
- Build a comparison matrix covering: source, key claim, evidence type, caveats, confidence.
- Use a source-backed table for quantitative comparisons, or a Mermaid diagram for method or architecture comparisons when the structure is source-supported. Follow the `figure-style` skill for any plot.
- Distinguish agreement, disagreement, and uncertainty clearly.
- Save exactly one comparison to `outputs/<slug>-comparison.md`, ending with a `Sources` section of direct URLs for every source used.
