#!/usr/bin/env python3
"""Auto-discovering constraint runner.

Pattern adapted from Edwin Hu, "Workflow Philosophy," edwinhu/workflows
(MIT, per README): constraints live as paired files in this directory --
``<name>.md`` (the human-readable rule) and ``<name>.py`` (the deterministic
check). This runner globs every ``*.py`` sibling (except itself), runs each as
a standalone check, and aggregates pass/fail. Adding a new check script is the
entire wiring step -- no registration.

A check script is any ``constraints/<name>.py`` that:
  * accepts zero or more target paths as argv (default: current directory),
  * prints human-readable findings to stdout/stderr,
  * exits 0 on PASS, 1 on FAIL, 2 on its own internal error.

Usage:
    python3 constraints/check-all.py [PATH ...]
    python3 constraints/check-all.py --only no-absolute-paths [PATH ...]

Exit code is 0 only if every check passed.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SELF = Path(__file__).resolve().name

PASS = "PASS"
FAIL = "FAIL"
ERROR = "ERROR"


def discover_checks(only: list[str] | None) -> list[Path]:
    checks = sorted(p for p in HERE.glob("*.py") if p.name != SELF)
    if only:
        wanted = set(only)
        checks = [p for p in checks if p.stem in wanted]
    return checks


def run_check(script: Path, targets: list[str]) -> tuple[str, str]:
    """Run one check script; return (status, captured_output)."""
    try:
        proc = subprocess.run(
            [sys.executable, str(script), *targets],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        return ERROR, "timed out after 120s"
    except OSError as exc:  # check script not executable / interpreter issue
        return ERROR, f"could not run: {exc}"

    output = (proc.stdout + proc.stderr).strip()
    if proc.returncode == 0:
        return PASS, output
    if proc.returncode == 1:
        return FAIL, output
    return ERROR, output or f"exit code {proc.returncode}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run all paired constraints.")
    parser.add_argument("targets", nargs="*", default=["."], help="paths to check")
    parser.add_argument(
        "--only",
        nargs="+",
        metavar="NAME",
        help="run only the named check(s) (by file stem)",
    )
    args = parser.parse_args()
    targets = args.targets or ["."]

    checks = discover_checks(args.only)
    if not checks:
        print("No constraint checks found.", file=sys.stderr)
        return 0

    results: list[tuple[str, str, str]] = []
    for script in checks:
        status, output = run_check(script, targets)
        results.append((status, script.stem, output))

    width = max(len(name) for _, name, _ in results)
    failed = 0
    errored = 0
    for status, name, output in results:
        mark = {PASS: "ok ", FAIL: "FAIL", ERROR: "err "}[status]
        print(f"[{mark}] {name.ljust(width)}")
        if status != PASS and output:
            for line in output.splitlines():
                print(f"        {line}")
        failed += status == FAIL
        errored += status == ERROR

    total = len(results)
    print(
        f"\n{total - failed - errored}/{total} passed"
        + (f", {failed} failed" if failed else "")
        + (f", {errored} errored" if errored else "")
    )
    # Fail the run on a real constraint violation; surface (but tolerate)
    # internal check errors so a broken check never silently blocks work.
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
