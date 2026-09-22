"""Comparable measurements from sealed archives; missing evidence stays visible."""

import json
import math
from pathlib import Path

from waterology.core.archive import load_archive, verify_project_archive
from waterology.core.errors import WaterologyError
from waterology.core.project import discover_project
from waterology.core.studies import StudyContract, fingerprint


def compare_runs(start: Path, run_ids: list[str], *, baseline: str) -> dict[str, object]:
    if baseline not in run_ids or len(run_ids) != len(set(run_ids)):
        raise ValueError("Select a unique run list containing the baseline")
    project = discover_project(start)
    rows = []
    for run_id in run_ids:
        row = {
            "run_id": run_id,
            "status": "unverified",
            "reason": None,
            "metrics": {},
            "deltas": {},
            "contract": None,
            "source_hash": None,
            "moved": {},
        }
        try:
            manifest = load_archive(start, run_id)
            row.update(
                experiment_id=manifest.experiment_id,
                commit_sha=manifest.commit_sha,
                operational_state=manifest.terminal_state,
            )
            if not verify_project_archive(start, run_id).valid:
                raise ValueError("Archive integrity failed")
            directory = project.paths.runs / run_id
            row["source_hash"] = fingerprint((directory / "checksums.sha256").read_text())
            if not (directory / "study.json").is_file():
                raise ValueError("Legacy run has no verified comparison contract")
            context = json.loads((directory / "study.json").read_text())
            contract = StudyContract.model_validate(context["contract"])
            if fingerprint(contract.model_dump(mode="json")) != context["contract_hash"]:
                raise ValueError("Study contract hash mismatch")
            # Budgets, allowed edits and selection strategies do not define an estimand.
            row["contract"] = {
                "mode": contract.mode,
                "input_files": contract.input_files,
                "evaluation_hash": context["evaluation_hash"],
                "evaluation": contract.evaluation,
                "metrics": [r.model_dump() for r in contract.acceptance],
                "uncertainty": contract.uncertainty,
            }
            row["contract_hash"] = fingerprint(row["contract"])
            metrics = json.loads((directory / "metrics.json").read_text())
            row["metrics"] = {
                r.name: metrics.get(r.name)
                if type(metrics.get(r.name)) in (int, float) and math.isfinite(metrics[r.name])
                else None
                for r in contract.acceptance
            }
            if manifest.terminal_state != "completed":
                raise ValueError(f"Run ended {manifest.terminal_state}")
            if any(v is None for v in row["metrics"].values()):
                raise ValueError("Missing or nonfinite measurements")
            row["status"] = "verified"
        except (WaterologyError, ValueError, KeyError, OSError) as error:
            row["reason"] = str(error)
        rows.append(row)
    base = next(row for row in rows if row["run_id"] == baseline)
    for row in rows:
        if row["status"] != "verified":
            continue
        if base["status"] != "verified":
            row.update(status="incomparable", reason="Baseline is not verified")
        elif row["contract_hash"] != base["contract_hash"]:
            row.update(
                status="incomparable", reason="Evaluation, units or metric definitions differ"
            )
        else:
            row["deltas"] = {
                name: value - base["metrics"][name] for name, value in row["metrics"].items()
            }
            row["moved"] = _movement(project.paths.runs / baseline, project.paths.runs / row["run_id"])
    return {
        "schema_version": 1,
        "baseline": baseline,
        "rows": rows,
        "complete": all(r["status"] == "verified" for r in rows),
        "uncertainty": "Only declared uncertainty is reported; no intervals inferred from point estimates.",
    }


def _sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _artifact_hashes(archive: Path) -> dict[str, str]:
    root = archive / "artifacts"
    if not root.is_dir():
        return {}
    return {
        path.relative_to(root).as_posix(): _sha256(path) or ""
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _movement(baseline: Path, candidate: Path) -> dict[str, bool]:
    base_manifest = json.loads((baseline / "manifest.json").read_text(encoding="utf-8"))
    candidate_manifest = json.loads((candidate / "manifest.json").read_text(encoding="utf-8"))
    base_metrics = json.loads((baseline / "metrics.json").read_text(encoding="utf-8"))
    candidate_metrics = json.loads((candidate / "metrics.json").read_text(encoding="utf-8"))
    return {
        "code": base_manifest.get("commit_sha") != candidate_manifest.get("commit_sha"),
        "environment": _sha256(baseline / "environment.json") != _sha256(candidate / "environment.json"),
        "data": _artifact_hashes(baseline) != _artifact_hashes(candidate),
        "seed": base_metrics.get("seed") != candidate_metrics.get("seed"),
    }
