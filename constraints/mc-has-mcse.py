#!/usr/bin/env python3
"""Require Monte Carlo summary CSV and Parquet files to report Monte Carlo uncertainty."""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

SKIP_DIRS = {".git", ".pixi", ".venv", "__pycache__", "node_modules", "renv"}
FILE_MARKERS = ("simulation", "monte-carlo", "mc-results", "mc_results")
METRIC_FAMILIES = {
    "bias": ("bias",),
    "coverage": ("coverage",),
    "power": ("power", "rejection", "size"),
}


def iter_tables(targets: list[str]):
    for raw in targets:
        target = Path(raw)
        paths = (target,) if target.is_file() else target.rglob("*")
        for path in paths:
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            if (
                path.is_file()
                and path.suffix.lower() in {".csv", ".parquet"}
                and any(marker in path.name.lower() for marker in FILE_MARKERS)
            ):
                yield path


def missing_mcse(path: Path) -> list[str]:
    if path.suffix.lower() == ".parquet":
        try:
            from pyarrow import parquet
        except ImportError as exc:
            raise ValueError(
                "Parquet inspection requires pyarrow; install waterology-research[constraints] "
                "in the checker environment"
            ) from exc
        header = parquet.read_schema(path).names
    else:
        with path.open(encoding="utf-8", newline="") as handle:
            header = next(csv.reader(handle), [])
    columns = {re.sub(r"[^a-z0-9]+", "_", column.strip().lower()).strip("_") for column in header}
    missing: list[str] = []
    for family, aliases in METRIC_FAMILIES.items():
        if not any(set(column.split("_")).intersection(aliases) for column in columns):
            continue
        if not any(
            "mcse" in column and set(column.split("_")).intersection(aliases) for column in columns
        ):
            missing.append(family)
    return missing


def main() -> int:
    findings = []
    for path in iter_tables(sys.argv[1:] or ["."]):
        try:
            if missing := missing_mcse(path):
                findings.append(f"{path}: missing MCSE for {', '.join(missing)}")
        except (OSError, ValueError, UnicodeError) as exc:
            findings.append(f"could not read {path}: {exc}")
    if not findings:
        return 0
    print(f"{len(findings)} Monte Carlo summary table issue(s):")
    for finding in findings:
        print(f"  {finding}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
