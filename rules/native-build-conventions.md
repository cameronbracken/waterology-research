---
name: native-build-conventions
description: >
  Build-system conventions for compiled code inside R/Python packages:
  Makevars, Makefiles, configure scripts, and cross-platform floating-point
  reproducibility.
paths:
  - "**/Makevars*"
  - "**/Makefile*"
  - "**/makefile"
  - "**/configure"
  - "**/*.mk"
  - "**/meson.build"
---

# Native build conventions

Rules for compiled scientific model builds. Every item
here caused a real failure at least once.

## Parallel-safe Makevars

CRAN builds packages with `make -j`. Fortran 90 modules must therefore carry
explicit dependency edges or the build races on missing `.mod` files:

```makefile
# modules compile before their users
stats.o: sorting.o
utilities.o: stats.o sorting.o
sac_snow.o: utilities.o
```

Test the ordering locally with GNU make 4.4+:
`MAKEFLAGS="-j$(nproc) --shuffle=reverse" R CMD INSTALL ...` shakes out
missing edges that an in-order parallel build hides.

## Explicit rules must carry the flags

A special rule for a legacy `.f` file (e.g. to drop `-std=f95`) bypasses R's
implicit rule, so it must repeat `$(PKG_FFLAGS)` itself. Otherwise the
package-level flags silently never reach that file. This is how
`-ffp-contract=off` failed to apply to `exsnow19.f`.

## Stale objects after ABI changes

R/cpp11 does not track header dependencies. After any change to a vendored
header-only core that alters a class layout (new vtable, reordered members),
`R CMD INSTALL` happily reuses stale `.o` files that read members at the wrong
offsets. Symptoms: garbage denormal values (`7.27e-314`), hard aborts under
`testthat`, while the C++ test suite of the same core passes (it rebuilds; the
R package did not). Fix:

```bash
rm -f src/*.o src/*.so && R CMD INSTALL --preclean .
```

Suspect a stale object file before suspecting the C++.

## Cross-platform floating point

When results differ between macOS and Linux (or between compiler versions),
check FMA contraction before anything else:

- gfortran's default `-ffp-contract` behavior differs by version (GCC 14
  changed it) and by ISA (aarch64 contracts, plain x86-64 cannot). This
  dominates mac-vs-linux divergence and can reach output scale through
  threshold flips in spin-up.
- For platform-independent results, compile everything with
  `-ffp-contract=off` and regenerate baselines once from a non-contracting
  build.
- Do not hardcode the flag in a shipped `Makevars` (`R CMD check` flags it
  non-portable). Probe it in `configure` and generate `src/Makevars` from a
  `Makevars.in` template with a placeholder; set it directly in `Makevars.win`
  (always Rtools gfortran). Meson side: `get_supported_arguments`.
- The residual after contraction is off is 1-ulp libm differences (Apple libm
  vs glibc `pow`/`exp`). That floor is irreducible; set test tolerances to
  absorb it rather than chasing exact equality across platforms.

A flags or precision change is an experiment, not a refactor: A/B the outputs
before adopting it.

## CI guards worth copying

- A clean step before builds: `find . \( -name '*.o' -o -name '*.so' -o -name
  '*.mod' \) -delete`. Stale artifacts corrupt incremental rebuilds.
- The `--shuffle=reverse` parallel build above, as a job.
- `readelf -lW pkg.so | grep GNU_STACK` to catch executable-stack regressions
  without running anything.
