"""Project lessons with explicit evidence, applicability and append-only review.

Design adapted from ECC continuous-learning-v2 at e04ea0b9cc8248686edf5ac751cadff550e162b8
(MIT, Affaan Mustafa). See ATTRIBUTION.md. No ECC hooks or observer are installed.
"""

import hashlib
import re
import warnings
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from waterology.core.config import _portable_project_path
from waterology.core.formats import load_document, write_document
from waterology.core.project import discover_project, project_state_lock


def _directory(start: Path) -> Path:
    path = discover_project(start).paths.state / "learning"
    if path.is_symlink():
        raise ValueError("Learning directory must not be a symlink")
    path.mkdir(exist_ok=True)
    return path


def _id(identifier: str) -> str:
    if not re.fullmatch(r"lesson-[0-9a-f]{16}", identifier):
        raise ValueError("Invalid lesson identifier")
    return identifier


def _evidence(start: Path, relative: str) -> dict:
    root = discover_project(start).root
    path = root / _portable_project_path(relative)
    if path.is_symlink() or not path.resolve().is_relative_to(root) or not path.is_file():
        raise ValueError("Lesson evidence must be a project file")
    return {"path": relative, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def remember(
    start: Path,
    *,
    trigger: str,
    action: str,
    evidence: list[str],
    outcome: str,
    tags: list[str],
    identifier: str | None = None,
) -> dict:
    if not trigger.strip() or not action.strip() or not outcome.strip() or not evidence:
        raise ValueError("A lesson needs a trigger, action, observed outcome and evidence")
    with project_state_lock(start):
        identifier = _id(identifier or f"lesson-{uuid4().hex[:16]}")
        path = _directory(start) / f"{identifier}.nt"
        if path.exists():
            previous = load_document(path)
            expected = {
                "trigger": trigger,
                "action": action,
                "outcome": outcome,
                "tags": tags,
                "evidence": [_evidence(start, p) for p in evidence],
            }
            if any(previous.get(key) != value for key, value in expected.items()):
                raise ValueError("Lesson ID already names different content or evidence")
            return previous
        record = {
            "schema_version": 1,
            "id": identifier,
            "trigger": trigger,
            "action": action,
            "outcome": outcome,
            "tags": tags,
            "scope": "project",
            "created_at": datetime.now(UTC).isoformat(),
            "evidence": [_evidence(start, p) for p in evidence],
        }
        write_document(path, record)
        return record


def inspect_lesson(start: Path, identifier: str) -> dict:
    path = _directory(start) / f"{_id(identifier)}.nt"
    if path.is_symlink():
        raise ValueError("Lesson must not be a symlink")
    lesson = load_document(path)
    reviews = []
    for p in sorted(_directory(start).glob(f"{identifier}.review-*.nt")):
        if p.is_symlink():
            raise ValueError("Lesson review must not be a symlink")
        reviews.append(load_document(p))
    reviews.sort(key=lambda r: r["created_at"])
    status = reviews[-1]["status"] if reviews else "proposed"
    if (
        reviews
        and reviews[-1].get("lesson_sha256") != hashlib.sha256(path.read_bytes()).hexdigest()
    ):
        status = "stale"
    try:
        if any(_evidence(start, e["path"]) != e for e in lesson["evidence"]):
            status = "stale"
    except (OSError, ValueError):
        status = "stale"
    return {"lesson": lesson, "status": status, "reviews": reviews}


def assess_lesson(start: Path, identifier: str, *, status: str, author: str, note: str) -> dict:
    if (
        status not in {"verified", "rejected", "superseded"}
        or not author.strip()
        or not note.strip()
    ):
        raise ValueError("Supply verified/rejected/superseded, author and assessment rationale")
    with project_state_lock(start):
        current = inspect_lesson(start, identifier)
        if status == "verified" and current["status"] == "stale":
            raise ValueError("Evidence changed; record a new lesson")
        record = {
            "status": status,
            "author": author,
            "note": note,
            "lesson_sha256": hashlib.sha256(
                (_directory(start) / f"{identifier}.nt").read_bytes()
            ).hexdigest(),
            "created_at": datetime.now(UTC).isoformat(),
        }
        write_document(_directory(start) / f"{identifier}.review-{uuid4().hex}.nt", record)
        return inspect_lesson(start, identifier)


def list_lessons(start: Path) -> list[dict]:
    return [
        inspect_lesson(start, p.stem)
        for p in sorted(_directory(start).glob("lesson-*.nt"))
        if ".review-" not in p.name
    ]


def lesson_context(start: Path, query: str, limit: int = 8) -> list[dict]:
    if not 1 <= limit <= 20:
        raise ValueError("Context limit must be between 1 and 20")
    terms = set(re.findall(r"[a-z0-9_]+", query.lower()))
    selected = []
    for entry in list_lessons(start):
        lesson = entry["lesson"]
        words = set(
            re.findall(r"[a-z0-9_]+", (lesson["trigger"] + " " + " ".join(lesson["tags"])).lower())
        )
        score = len(terms & words)
        if entry["status"] == "verified" and score:
            selected.append((score, lesson))
    return [
        lesson for _, lesson in sorted(selected, key=lambda pair: (-pair[0], pair[1]["id"]))[:limit]
    ]


def propose_improvement(
    start: Path, identifiers: list[str], *, change: str, validation: str
) -> dict:
    if not identifiers or not change.strip() or not validation.strip():
        raise ValueError("An improvement needs lessons, a concrete change and a validation plan")
    with project_state_lock(start):
        for identifier in identifiers:
            if inspect_lesson(start, identifier)["status"] != "verified":
                raise ValueError("Only current verified lessons support an improvement")
        record = {
            "id": f"improvement-{uuid4().hex[:16]}",
            "status": "proposed",
            "scope": "shared Waterology",
            "lessons": identifiers,
            "change": change,
            "validation": validation,
            "created_at": datetime.now(UTC).isoformat(),
        }
        write_document(_directory(start) / f"{record['id']}.nt", record)
        return record


def capture_study_outcomes(start: Path, study) -> None:
    """Idempotent observations, never automatic scientific or behavioral promotion."""
    for attempt in study.attempts:
        if attempt.state not in {"completed", "failed", "cancelled", "lost"}:
            continue
        identifier = "lesson-" + hashlib.sha256(attempt.run_id.encode()).hexdigest()[:16]
        remember(
            start,
            identifier=identifier,
            trigger=f"{study.contract.mode} {study.contract.objective}",
            action="Inspect this archived outcome before repeating the candidate",
            evidence=[f".waterology/runs/{attempt.run_id}/manifest.json"],
            outcome=f"{attempt.run_id}: {attempt.state}; numerical result is not a scientific conclusion",
            tags=["study", study.contract.mode],
        )


def learning_warning(start: Path, error: Exception) -> None:
    """Optional learning cannot prevent compute reconciliation or cancellation."""
    message = f"Project learning unavailable: {type(error).__name__}; execution state is preserved"
    try:
        write_document(
            discover_project(start).paths.state / "learning-warning.nt", {"warning": message}
        )
    except (OSError, ValueError):
        warnings.warn(message, RuntimeWarning, stacklevel=2)
