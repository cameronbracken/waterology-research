---
name: waterology-scientific-writing-detailed
description: >
  Expanded variant of `waterology-scientific-writing` for writing, structuring, or revising
  peer-reviewed scientific manuscripts, journal articles, data descriptors,
  abstracts, captions, and reviewer responses with fuller explanations and
  examples. Mutually exclusive with `waterology-scientific-writing`: load only one of the
  two in a session, using this skill when the detailed variant is requested.
---

<!-- Generated from skills/scientific-writing-detailed/SKILL.md. Do not edit. -->

# Scientific Writing (Detailed Variant)

> **Mutual exclusion:** Load **either** `waterology-scientific-writing-detailed` **or** [scientific-writing](../waterology-scientific-writing/SKILL.md), **never both at the same time**. If `waterology-scientific-writing` is already loaded in context, do not load or combine this skill with it.

Write clear, grounded, peer-to-peer scientific prose for journal manuscripts, data descriptors, abstracts, captions, and reviewer responses. For general documentation, READMEs, blog posts, plans, emails, commit messages, and Markdown file mechanics, use [writing-style](../waterology-writing-style/SKILL.md). When drafting or restructuring specific paper sections, also read [section-playbook.md](references/section-playbook.md).

## Voice, tone, and epistemic stance

- **Grounded collegial authority:** Write for fellow domain scientists and engineers in a calm, direct, matter-of-fact register. Remove promotional adjectives (`groundbreaking`, `revolutionary`, `novel`, `vital`, `crucial`), rhetorical hype, and conversational filler.
- **Operational and physical anchoring:** Tie statistical definitions, model layers, spatial units, and temporal resolutions directly to the physical process or real-world planning/operational decision they inform (such as reservoir operations, dam safety, grid balancing, or storage sizing).
- **Methodological candor:** State pragmatic modeling decisions, approximations, thresholds, and computational budgets openly (`We chose ... because ...`, `For simplicity, we assume ... though this assumption can be relaxed by ...`, `Testing indicated that additional iterations provided marginal improvement`). Include brief cautionary notes when an explored method fails or introduces artifacts.
- **Plain reporting of null and counterintuitive results:** Report null trends, regional discrepancies, or unexpected behavior directly, then diagnose the physical, statistical, or experimental cause (`No significant trend in ... was detected across scenarios. This null result likely stems from ... For this reason, ... should be interpreted with caution.`).
- **Calibrated confidence:**
  - Use direct indicative verbs (`shows`, `indicates`, `demonstrates`, `reduces`, `captures`) for observed statistics, mathematical properties, and validation metrics.
  - Shift to calibrated hedges (`may`, `might`, `could`, `likely`, `tends to`, `suggests`, `is consistent with`) when inferring causal mechanisms, extrapolating into distribution tails, or projecting future scenarios.
  - Distinguish modeled proxies or resource availability from realized system operations (for example, separating resource shortfalls from actual dispatch or unserved energy under network constraints, or separating naturalized flow from regulated operations).
  - Avoid `first` or `first of its kind` unless supported by a thorough literature review and scoped to the exact combination of scale, variables, and framework.

## Sentence rhythm, voice, and paragraph craft

- **Measured academic cadence:** Aim for an average sentence length around 18 to 26 words (interquartile range roughly 15 to 30 words). Pair crisp 10 to 15 word topic or takeaway sentences with controlled 22 to 32 word analytical sentences that connect a pattern to its mechanism or condition. Split sprawling 45+ word clause chains.
- **Balanced active `we` and purposeful passive:**
  - Use active first-person plural (`we`, `our`; never singular `I`) for framing, contribution statements, design judgments, caveats, and interpretation (`We present`, `We propose`, `We develop`, `We examine`, `We chose`, `We required`, `We note that`, `We acknowledge that`, `We find that`, `We recommend`).
  - Use natural passive voice for data provenance, routine preprocessing steps, and standard mathematical definitions (`Daily observations were obtained from ...`, `Runoff was aggregated to ...`, `Duration is defined as ...`) so Methods sections read smoothly rather than as repetitive `We did X` logs.
  - Vary openings so consecutive sentences or paragraphs do not repeat `In this study,` or `We`.
- **Cohesive narrative paragraphs:** Build paragraphs of roughly 4 to 8 sentences (120 to 200 words) that open with the conceptual role, claim, or figure orientation, develop through concrete quantitative or mathematical detail, and close with the physical, statistical, or operational implication.
- **Prose over bullet lists:** Write manuscript sections in full paragraphs. Reserve numbered lists (`1. ... 2. ...` or inline `(1) ..., (2) ..., and (3) ...`) strictly for:
  1. Explicit research questions or required model properties at the end of an Introduction,
  2. Step-by-step simulation, calibration, or resampling algorithms,
  3. Named baseline or ablation configurations in a model comparison, or
  4. Structured multi-point contrasts between methods in Discussion or Conclusions.
- **Transitions, terminology, and punctuation:**
  - Use contrastive openings (`While ..., ...`, `Although ..., ...`) and clear logical pivots (`However,`, `For example,`, `In addition,`, `Specifically,`, `In contrast,`, `Conversely,`, `Furthermore,`, `Consequently,`, `Therefore,`).
  - Define acronyms once on first use in the Abstract and again on first use in the main text. Pair specialized terms on first appearance with a brief operational gloss (`positive residual load events, the supply gap left when variable generation cannot meet demand`). Maintain one term, capitalization, and hyphenation pattern per concept.
  - Never use exclamation marks. Avoid decorative bolding and em-dash chains; use parentheticals judiciously for period bounds `(1980-2019)`, units, acronym definitions, or concise examples `(e.g., ...)`.

## Equations, visuals, and quantitative rigor

- **Grammatical equations with intuition:** Lead into displayed equations as natural clauses of the surrounding sentence and follow immediately with `where ... is ..., ... denotes ..., and ...` defining every symbol, subscript, and bound. Pair equations and key parameters with physical or statistical intuition: why a distribution's support or tail behavior suits the data, what extreme parameter values imply physically, and practical numerical details (such as log-likelihood evaluation to avoid underflow, scaling inputs for weakly informative priors, or convergence diagnostics like $\hat{R} < 1.1$).
- **Self-orienting figure and table narration:** Alternate naturally between orienting lead-ins (`Figure 3 shows ...`, `Table 1 summarizes ...`) and parenthetical pointers `(Figure 4)`. Before interpreting a dense or multi-panel figure, spend 1 to 2 sentences explaining how to read the visual encoding (panel rows and columns, solid median versus 5th to 95th percentile ribbons, symbol size, or normalization). Then move in order: overall pattern -> regional or seasonal contrast -> notable exception or hotspot -> physical or methodological explanation.
- **Standalone captions:** State the plotted quantity and units, spatial and temporal scope, scenario or validation period, panel layout (`(a)`, `(b)`, or `top`/`bottom`, `left`/`right`), uncertainty bounds, and any visual filtering or logarithmic scaling so the figure can be understood without hunting through the body text.
- **Scope, baselines, and reproducibility:** Establish the time period, spin-up/calibration/validation splits, spatial extent and resolution, sample size, and completeness or exclusion rules (with exact counts and reasons) early. Compare proposed methods against domain-appropriate baselines (such as climatology, independent or stationary models, or operational benchmarks) under out-of-sample validation. Follow `rules/quarto-conventions.md` for dynamic number import, [bib-validate](../waterology-bib-validate/SKILL.md) for citation verification, and [compile-latex](../waterology-compile-latex/SKILL.md) for LaTeX builds.

## Manuscript revision pass

1. **Argument and scope:** Confirm that every section motivates choices operationally, defines temporal/spatial bounds and exclusion counts explicitly, and separates modeled proxies from real-world system operations.
2. **Claim calibration:** Check that observed statistics use direct verbs while mechanisms, extrapolations, and scenario projections carry calibrated hedges, and that null or counterintuitive findings include a concrete diagnosis.
3. **Cadence and prose hygiene:** Break 45+ word sentences, replace bulleted fragments with cohesive paragraphs, balance `we` agency with passive pipeline descriptions, eliminate repeated `In this study` openings, and verify equation symbol definitions and standalone captions.
