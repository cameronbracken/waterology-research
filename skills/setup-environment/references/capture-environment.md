# Environment capture (strict / archival deliverables)

Use before paper submission, formal DOE deliverable archival, or building a replication package. Never upgrade or mutate dependencies while capturing them.

## Capture by stack

- **Python:** Verify `pixi.lock` or `uv.lock` is current and committed; record Python version, execution command, and RNG seed setup (`default_rng`, `SeedSequence`, library seeds).
- **R:** Verify `rv.lock` (or existing `renv.lock` via `renv::status()` without mutating it unless authorized); write `sessionInfo()` to `sessionInfo.txt`; record R version, package repositories, `RNGkind()`, and `set.seed()` values.
- **Fortran / C:** Record compiler identity and version (`gfortran --version`), compile/link flags from `pixi.toml`/`Makefile`/`meson.build`, linked numerical/MPI/OpenMP libraries, default integer/real kind settings, and architecture.

## Output

Write `quality_reports/computational-requirements.md` (or update the project README) summarizing OS/architecture, language and compiler versions, lockfiles, RNG seeds, canonical build/run commands, expected runtime, and any restricted external inputs. Reference `sessionInfo.txt` and lockfiles by path rather than pasting hundreds of package lines inline.
