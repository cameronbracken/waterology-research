# Attribution

`waterology` is original work by Cameron Bracken, but its methodology and
several components are adapted from open-source Claude Code projects. This
ledger records what was borrowed and from whom. Files that derive from a
source carry a one-line credit at the top; this page is the canonical list.

## Sources

### edwinhu/workflows — methodology

- **Author:** Edwin Hu
- **Repo:** <https://github.com/edwinhu/workflows>
- **License:** MIT *(asserted in the project README; no standalone `LICENSE`
  file is present in the repo as of June 2026 — cited in good faith)*
- **What we adapt:** the `PHILOSOPHY.md` methodology — the
  *constraints-vs-conventions* distinction and its pass/fail litmus test, the
  paired `foo.md` + `foo.py` constraint pattern with an auto-discovering
  `check-all.py` runner, hook-enforced phase gates, independent verification
  (the implementer never reviews its own work), and "evidence over claims."
- **Credit string:** *Methodology adapted from Edwin Hu, "Workflow Philosophy,"
  edwinhu/workflows (MIT, per README).*

### pedrohcgs/claude-code-my-workflow — reproducibility + R/simulation

- **Author:** Pedro H. C. Sant'Anna
- **Repo:** <https://github.com/pedrohcgs/claude-code-my-workflow>
- **License:** MIT — © 2026 Pedro H. C. Sant'Anna
- **What we adapt (planned / in progress):** the reproducibility **passport**
  (`audit-reproducibility` skill, `passport.yaml` schema, `claim-reconcile.py`
  STALE-detection hook), the Monte Carlo trio (`simulation-study` +
  `sim-reviewer` + simulation conventions), the `r-reviewer` agent (esp. its
  numerical-discipline checks), `r-package-check` (CRAN `--as-cran` gate), and
  `capture-environment`. Stata- and econ-specific material is stripped.
- **Credit string:** *Adapted from pedrohcgs/claude-code-my-workflow (MIT,
  © 2026 Pedro H. C. Sant'Anna).*
- **Note:** Sant'Anna credits the "passport" concept itself to
  `Imbad0202/academic-research-skills` ("Material Passport") — carried forward.

### flonat/claude-research — reproducibility auditor + bibliography

- **Author:** Florian Burnat
- **Repo:** <https://github.com/flonat/claude-research>
- **License:** MIT — © 2026 Florian Burnat
- **What we adapt (planned / in progress):** the `reproducibility-auditor`
  agent and its 12-row PASS/FAIL checklist, bibliography / DOI validation via
  the free OpenAlex + Crossref path, the `myst_to_quarto.py` converter, LaTeX
  `latexmk` / overfull-box handling, and the `no-hardcoded-results` rule.
- **Credit string:** *Adapted from flonat/claude-research (MIT, © 2026 Florian
  Burnat).*

## Original to this plugin

Fortran support (discovery globs, `gfortran` runner, reproducibility header,
conventions), the Quarto-as-document conventions, and all tuning to the
hydrology / energy-systems / extremes toolchain are original work.
