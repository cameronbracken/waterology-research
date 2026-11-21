---
name: scientific-writing
description: >
  Default concise skill to write, structure, or revise peer-reviewed scientific
  manuscripts, journal articles, data descriptors, abstracts, plain-language
  summaries, figure and table captions, and responses to reviewers. Mutually
  exclusive with `scientific-writing-detailed`: load only one of the two in a
  session. Use for formal scientific papers rather than general documentation,
  blog posts, notes, or READMEs.
---

# Scientific Writing

> **Mutual exclusion:** Load **either** `scientific-writing` **or** [scientific-writing-detailed](../scientific-writing-detailed/SKILL.md), **never both at the same time**. Default to this concise skill unless the user explicitly asks for `scientific-writing-detailed`.

Write grounded, peer-to-peer scientific prose for journal articles, data descriptors, abstracts, captions, and reviewer responses. For conversational technical writing, blog posts, documentation, reports, and Markdown mechanics, use [writing-style](../writing-style/SKILL.md). When drafting or restructuring paper sections, read [section-playbook.md](references/section-playbook.md).

## Voice and epistemic stance

- **Collegial, matter-of-fact register:** Write for fellow domain scientists and engineers. Cut promotional adjectives (`groundbreaking`, `revolutionary`, `novel`, `vital`, `crucial`), dramatic hooks, and exclamation marks. Avoid `first` or `first of its kind` unless verified by literature review and scoped to the exact combination of scale, variables, and method.
- **Operational and physical anchoring:** Tie statistical indices, model layers, spatial units, and timescales early to the physical process or real-world planning/operational decision they serve (such as reservoir management, dam safety, control-area balancing, or storage sizing).
- **Methodological candor:** State pragmatic thresholds, approximations, and compute budgets plainly (`We chose ... because ...`, `For simplicity, we assume ... though this can be relaxed by ...`). Note failed alternatives briefly when instructive, and report null or counterintuitive results directly alongside their physical or experimental cause (`This null result likely stems from ...`).
- **Calibrated confidence:** Use direct verbs (`shows`, `indicates`, `demonstrates`, `reduces`, `captures`) for observed statistics and validation metrics; shift to hedges (`may`, `might`, `could`, `likely`, `tends to`, `suggests`, `is consistent with`) for causal mechanisms, tail extrapolations, and future scenarios. Distinguish modeled proxies or resource deficits from realized system operations.

## Cadence, voice, and paragraph structure

- **Measured sentence cadence:** Target ~18 to 26 words on average (interquartile range ~15 to 30). Pair 10 to 15 word anchor/takeaway sentences with 22 to 32 word analytical sentences linking pattern to mechanism; split 45+ word clause chains.
- **Active `we` for agency, passive for pipeline mechanics:** Use `we`/`our` (never `I`) for framing, design choices, caveats, and synthesis (`We present`, `We propose`, `We chose`, `We note that`, `We find that`, `We recommend`). Use natural passive voice for data provenance, routine preprocessing, and formal definitions (`Daily observations were obtained from ...`, `Duration is defined as ...`). Do not repeat `In this study` or `We` across consecutive openings.
- **Narrative paragraphs over bullets:** Build 4 to 8 sentence paragraphs (~120 to 200 words) moving from conceptual/visual anchor -> quantitative or mathematical evidence -> operational or physical takeaway. Avoid bullet lists in body text; use numbered lists only for (1) 2 to 3 research questions or required model properties, (2) step-by-step algorithms, (3) baseline model suites, or (4) structured method comparisons.
- **Transitions and terminology:** Pivot with `While ...,`, `Although ...,`, `However,`, `For example,`, `In addition,`, `Specifically,`, `In contrast,`, `Conversely,`, and `Consequently,`. Define acronyms once in the Abstract and once in the main text, add a brief operational gloss on first use of specialized terms, and keep one term and hyphenation pattern per concept.

## Equations, visuals, and rigor

- **Grammatical equations with intuition:** Introduce equations as natural sentence clauses followed immediately by `where ... is ...` for every symbol and bound. State why a distribution's support or tail suits the variable, what limiting parameter values mean physically, and key numerical details (log-likelihood space, input scaling for priors, MCMC convergence $\hat{R} < 1.1$).
- **Orient-first figure narration and standalone captions:** Alternate `Figure 3 shows ...` lead-ins with `(Figure 4)` pointers. Spend 1 to 2 sentences explaining dense or multi-panel encodings (rows/columns, median vs. percentile ribbons, normalization) before narrating: overall pattern -> regional/seasonal contrast -> outlier -> mechanism. Make captions standalone with units, periods, panel keys, uncertainty bounds, and scaling notes.
- **Scope, baselines, and checks:** State periods, spin-up/calibration/validation splits, resolution, sample sizes, and exclusion counts/reasons early. Benchmark against out-of-sample baselines (climatology, stationary/independent models, operational forecasts), and apply `rules/quarto-conventions.md`, [bib-validate](../bib-validate/SKILL.md), and [compile-latex](../compile-latex/SKILL.md).
