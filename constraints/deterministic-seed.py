#!/usr/bin/env python3
"""Constraint check: stochastic scripts set a seed.

See deterministic-seed.md for the rule. Exits 0 (PASS) when clean, 1 (FAIL)
when a script uses randomness without seeding, 2 (ERROR) on internal problems.

Adapted from the numerical-discipline / simulation tooling in
pedrohcgs/claude-code-my-workflow (MIT, (c) 2026 Pedro H. C. Sant'Anna).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", ".pixi", "renv", "out"}
ALLOW_MARKER = "waterology: allow-unseeded"

R_SUFFIXES = {".R", ".r"}
PY_SUFFIXES = {".py"}

R_RNG = re.compile(
    r"\b(rnorm|runif|sample|rbinom|rpois|rgamma|rbeta|rexp|mvrnorm|simulate|boot)\s*\("
)
R_SEED = re.compile(r"\bset\.seed\s*\(")

PY_RNG = re.compile(r"(np\.random\.|(?<!\w)random\.|default_rng\s*\(|torch\.rand|\.sample\s*\()")
PY_SEED = re.compile(
    r"(np\.random\.seed\s*\(|(?<!\w)seed\s*\(|default_rng\s*\(\s*\d|manual_seed\s*\()"
)


def iter_scripts(targets: list[str]):
    for raw in targets:
        root = Path(raw)
        if root.is_file():
            if root.suffix in R_SUFFIXES | PY_SUFFIXES:
                yield root
            continue
        for path in root.rglob("*"):
            if path.is_dir() or any(part in SKIP_DIRS for part in path.parts):
                continue
            if path.suffix in R_SUFFIXES | PY_SUFFIXES:
                yield path


def check_file(path: Path) -> str | None:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"could not read {path}: {exc}", file=sys.stderr)
        return None
    if ALLOW_MARKER in text:
        return None
    if path.suffix in R_SUFFIXES:
        rng, seed = R_RNG, R_SEED
    else:
        rng, seed = PY_RNG, PY_SEED
    if rng.search(text) and not seed.search(text):
        return f"{path}: uses randomness but never sets a seed"
    return None


def main() -> int:
    targets = sys.argv[1:] or ["."]
    findings = [msg for p in iter_scripts(targets) if (msg := check_file(p))]
    if findings:
        print(f"{len(findings)} unseeded stochastic script(s):")
        for finding in findings:
            print(f"  {finding}")
        print("Add set.seed()/np.random.seed(), or mark the file with "
              "'# waterology: allow-unseeded'.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
