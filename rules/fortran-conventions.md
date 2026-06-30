---
name: fortran-conventions
description: Fortran 90+ conventions for waterology scientific/hydrology code
paths:
  - "**/*.f90"
  - "**/*.F90"
  - "**/*.f95"
  - "**/*.f"
---

# Fortran conventions

Conventions for scientific Fortran (hydrology model internals: SAC-SMA/Snow-17,
NWSRFS, VIC, and numerical kernels). This is original guidance — no upstream
plugin covers Fortran. Match an existing file's local style first; much of this
code is legacy fixed-form that should be touched conservatively.

## Standard and form

- Prefer **Fortran 90 or later**, free-form (`.f90`/`.F90`). When editing legacy
  fixed-form (`.f`, 72-column, `C` comments), keep the existing form — do not
  reflow a whole file to free-form unless asked.
- Always `implicit none` in every program, module, and procedure. Never rely on
  implicit typing.
- Organize reusable code into `module`s with `private` defaults and explicit
  `public` exports; `use module, only: ...` at call sites.

## Precision and numerical discipline

- Define a kind parameter once and use it everywhere, rather than bare `real`:
  ```fortran
  use, intrinsic :: iso_fortran_env, only: wp => real64
  real(wp) :: storage, runoff
  ```
  Match the precision the upstream model expects (most NWS hydrology code is
  single `real32`; check before widening — a precision change is an experiment).
- Never compare reals with `==`; test `abs(a - b) <= tol` with an explicit
  tolerance.
- Declare procedure argument `intent(in|out|inout)` on every dummy argument —
  it documents data flow and lets the compiler catch misuse.
- Guard against divide-by-zero and `log`/`sqrt` of non-positive inputs in
  physical updates (storages, flows). Conservation (mass/water balance) should
  close to tolerance — a good candidate for a future scriptable constraint.

## Reproducibility header

Start each driver/source file with a comment block (the Fortran equivalent of
the R/Python script header) so provenance survives:

```fortran
! ============================================================
! <file>.f90 -- <one-line purpose>
! Model:    SAC-SMA / Snow-17 / NWSRFS / VIC / ...
! Inputs:   <forcing files, parameter files>
! Outputs:  <state/flux files>  (paths are relative to project root)
! Build:    gfortran -O2 -Wall -fimplicit-none -std=f2008 <...>
! Seed:     <none | RNG module + seed>  (set explicitly if stochastic)
! ============================================================
```

Use `! waterology: allow-abs-path` / `! waterology: allow-unseeded` on a line to
opt a constraint out where genuinely needed.

## Building and running

- Build with **gfortran**; develop with warnings on:
  `gfortran -O2 -g -Wall -Wextra -fimplicit-none -fcheck=all -std=f2008`.
  Drop `-fcheck=all` and raise `-O` only for production/benchmark runs.
- Keep build commands in a `Makefile` (the existing convention for `gpu-SAC/`,
  `brent/`, `fortran-utils/`); do not hand-invoke long compiler lines ad hoc.
- Fixed seeds: Fortran's `random_number` is seeded via `random_seed`; set it
  explicitly from a known integer for any stochastic simulation so runs replay.
