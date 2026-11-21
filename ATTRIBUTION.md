# Attribution

`waterology` is original work by [Cameron Bracken](https://orcid.org/0000-0003-1917-402X), with methodology and selected components adapted from open-source research and agent projects. This file records active upstream sources and licenses for Waterology 1.0.

## House defaults, R style, and visual deliverables

- Author: [Cameron Bracken](https://orcid.org/0000-0003-1917-402X).
- Scope: tool selection (`skills/project-conventions/`), environment defaults (`skills/setup-environment/`), R code style (`skills/r-code-style/`), scientific manuscript prose (`skills/scientific-writing/` and `skills/scientific-writing-detailed/`), general technical prose (`skills/writing-style/`), plots and interactive graphics (`skills/figures/`), TikZ flowcharts (`skills/diagrams/`), Markdown and Quarto report bundles (`skills/reports/`), and Quarto blog preparation (`skills/publish-blog-post/`).
- Private values, machine inventories, account settings, and credentials stay outside package assets.

## Upstream sources

### edwinhu/workflows - methodology

- Author: Edwin Hu
- Repository: [edwinhu/workflows](https://github.com/edwinhu/workflows)
- License: MIT (asserted in the project README; cited in good faith)
- Adapted elements: the `PHILOSOPHY.md` distinction between deterministic constraints and prose conventions, the paired `.md` + `.py` constraint pattern with an auto-discovering `constraints/check-all.py` runner, independent verification (`agent-definitions/reviewer.md`), and fresh evidence before completion claims.
- Credit string: _Methodology adapted from Edwin Hu, "Workflow Philosophy," edwinhu/workflows (MIT, per README)._

### pedrohcgs/claude-code-my-workflow - reproducibility and simulation

- Author: Pedro H. C. Sant'Anna
- Repository: [pedrohcgs/claude-code-my-workflow](https://github.com/pedrohcgs/claude-code-my-workflow)
- Pinned revisions: `cb38a277840fd0ee0c0a6ea61ddc2bceb940efc6` (passport) and `9d371f0bf8a8bc99569feca3210ef5133af28d33` (review and build tools)
- License: MIT, Copyright (c) 2026 Pedro H. C. Sant'Anna
- Adapted elements: the reproducibility passport (`skills/audit-reproducibility/` and `templates/passport.yaml`, extended to Fortran and fixed-width outputs without Stata material), Monte Carlo study design and conventions (`skills/simulation-study/` and `rules/simulation-conventions.md`), simulation critique criteria (`agent-definitions/reviewer.md`), environment snapshots (`skills/setup-environment/`), and the `latexmk` compile workflow (`skills/compile-latex/`). Sant'Anna credits the passport concept to `Imbad0202/academic-research-skills` ("Material Passport").
- Credit string: _Adapted from pedrohcgs/claude-code-my-workflow (MIT, Copyright 2026 Pedro H. C. Sant'Anna)._

### flonat/claude-research - reproducibility audit and bibliography

- Author: Florian Burnat
- Repository: [flonat/claude-research](https://github.com/flonat/claude-research)
- Pinned revision: `e7007d0b1e465ef96de7338599ca04079e83a972`
- License: MIT, Copyright (c) 2026 Florian Burnat
- Adapted elements: reproducibility audit checks and script-to-figure pipeline manifests (`skills/audit-reproducibility/`), bibliography and DOI verification through OpenAlex and Crossref (`skills/bib-validate/` and `rules/no-hallucinated-citations.md`), LaTeX box diagnostics (`skills/compile-latex/scripts/overfull_boxes.py` and `constraints/overfull-boxes.py`), and the rule against hardcoded computed numbers (`rules/no-hardcoded-results.md` and `constraints/no-hardcoded-results.py`). `skills/project-conventions/scripts/myst_to_quarto.py` is an original Waterology implementation of the conversion workflow.
- Credit string: _Adapted from flonat/claude-research (MIT, Copyright 2026 Florian Burnat)._

### companion-inc/feynman - research agents and skills

- Author: Companion, Inc.
- Repository: [companion-inc/feynman](https://github.com/companion-inc/feynman)
- Pinned revisions: `8ad8d5582fc5acb855fb83f972f0f3121d1aa423` and `c8d84cd1939a018a930272f48d16f79da8ec249b`
- License: MIT, Copyright (c) 2026 Companion, Inc.
- Adapted elements: primary-source gathering and peer review subagents (`agent-definitions/researcher.md` and `agent-definitions/reviewer.md`), multi-provider literature and ML recipe synthesis (`skills/literature-review/`, incorporating 11-source coverage planning), manuscript and narrative critique (`skills/research-review/`), paper-to-code parity checks (`skills/audit-reproducibility/`), multi-panel figure composition and Plotly layout hygiene (`skills/figures/`), bounded iteration loops (`skills/autoresearch/`), and generated command shims (`commands/`). Product-specific tool names and biology wrappers are replaced with portable runtime conventions for R, Python, Quarto, hydrology, and energy systems.
- Credit string: _Adapted from Feynman (companion-inc/feynman, MIT)._

### alphaXiv/OpenResearch (formerly openresearch-cli) - experiment trees and alphaXiv discovery

- Author: alphaXiv
- Repository: [alphaXiv/OpenResearch](https://github.com/alphaXiv/OpenResearch) (including prior [alphaXiv/openresearch-cli](https://github.com/alphaXiv/openresearch-cli) revisions `13049867497de8fd5e15253cd818462629edd690` and `5412465c112b4f81033420db7ff7267ec88106c6`, and OpenResearch revision `8fc90cf355cda1e89a6aabc02d49a098f159f463`)
- License: MIT, Copyright (c) 2026 alphaXiv
- Adapted elements: Git experiment-tree discipline (`skills/autoresearch/references/experiment-tree.md`), multi-hop citation verification rules (`skills/literature-review/` and `agent-definitions/reviewer.md`), and public `alphaxiv` / `alphaxiv-keyword` HTTP request structure in `src/waterology/core/literature.py` (original Python implementation, no Rust or UI code copied).
- Credit string: _Adapted from alphaXiv/OpenResearch (MIT)._

### William Strunk Jr. - concise prose principles

- Author: William Strunk Jr.
- Source: [The Elements of Style (Project Gutenberg #37134)](https://www.gutenberg.org/ebooks/37134)
- License: Public domain in the United States
- Adapted elements: compact composition principles in `skills/writing-style/SKILL.md`.
- Credit string: _Prose principles adapted from William Strunk Jr., The Elements of Style (1918, public domain)._

### obra/superpowers - proportional software quality

- Author: Jesse Vincent
- Repository: [obra/superpowers](https://github.com/obra/superpowers) (version 6.3.0)
- License: MIT, Copyright (c) 2025 Jesse Vincent
- Adapted elements: evidence-first debugging, regression testing, fresh verification before completion claims, risk-based review, and Git worktree isolation in `skills/research-software-quality/SKILL.md`.
- Credit string: _Software quality guidance adapted from Superpowers 6.3.0 (obra/superpowers, MIT)._

### NatLabRockies/torc - native distributed and HPC execution

- Organization: National Laboratory of the Rockies
- Repository: [NatLabRockies/torc](https://github.com/NatLabRockies/torc)
- License: BSD 3-Clause
- Use: documented as an external workflow runner in `docs/torc.md`, `skills/project-conventions/`, and `skills/autoresearch/`. No TORC source code is copied.
- Credit string: _Distributed execution guidance references TORC (NatLabRockies/torc, BSD 3-Clause)._

### NVlabs/SoL-Pi - SoL-Pi delegation skill

- Organization: NVIDIA Corporation and affiliates
- Repository: [NVlabs/SoL-Pi](https://github.com/NVlabs/SoL-Pi/tree/219568034fa54ed121ede80961655e33dfb9d0e3) (commit `219568034fa54ed121ede80961655e33dfb9d0e3`)
- License: MIT, Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES
- Adapted elements: `skills/sol-pi/SKILL.md` merges the Claude Code and Codex variants of `examples/sol-pi-skill/*/SKILL.md` into one portable skill without copying upstream launchers or extensions.
- Credit string: _SoL-Pi delegation skill adapted from NVlabs/SoL-Pi (MIT)._

## Original to Waterology

Fortran conventions and constraint checks, standalone `.zotero.toml` reference sync (`waterology.core` and `waterology.mcp`), Hugging Face Hub metadata inspection, multi-runtime asset rendering and transactional installation (`waterology.runtime`), TikZ and report-bundle verifiers, and hydrology and energy-systems defaults are original work.
