"""Append-only claims with verifiable archive member and JSON pointer evidence."""

import hashlib
import json
import re
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from waterology.core.archive import load_archive, verify_project_archive
from waterology.core.atomic import write_json
from waterology.core.config import _portable_project_path
from waterology.core.errors import WaterologyError
from waterology.core.project import discover_project, project_state_lock


class ClaimRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal[1] = 1
    id: str = Field(pattern=r"^claim-[0-9a-f]{16}$")
    claim: str = Field(min_length=1)
    kind: Literal["observation", "inference", "proposed_analysis"] = "observation"
    run_id: str = Field(pattern=r"^run-[a-z0-9][a-z0-9-]{0,62}$")
    member: str
    selector: str
    sha256: str
    value: object
    relation: Literal["supports", "contradicts", "context"] = "supports"
    related_claim: str | None = None


class ManuscriptAnchor(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal[1] = 1
    id: str = Field(pattern=r"^anchor-[0-9a-f]{16}$")
    label: str = Field(min_length=1)
    path: str = Field(min_length=1)
    claim_id: str | None = Field(default=None, pattern=r"^claim-[0-9a-f]{16}$")
    resolved: bool = False
    context: str | None = None


def _claims_dir(start: Path) -> Path:
    path = discover_project(start).paths.state / "claims"
    if path.is_symlink():
        raise ValueError("Claim directory must not be a symlink")
    path.mkdir(exist_ok=True)
    return path


def _member(start: Path, run_id: str, member: str) -> Path:
    load_archive(start, run_id)
    directory = discover_project(start).paths.runs / run_id
    path = directory / _portable_project_path(member)
    if (
        path.is_symlink()
        or not path.resolve().is_relative_to(directory.resolve())
        or not path.is_file()
    ):
        raise ValueError("Evidence member must be an existing archive file")
    return path


def select_json(value: object, pointer: str) -> object:
    if not pointer:
        return value
    if not pointer.startswith("/"):
        raise ValueError("Use a JSON pointer starting with /")
    for item in pointer[1:].split("/"):
        if re.search(r"~(?![01])", item):
            raise ValueError("Invalid JSON pointer escape")
        key = item.replace("~1", "/").replace("~0", "~")
        if isinstance(value, list):
            if not re.fullmatch(r"0|[1-9][0-9]*", key):
                raise ValueError("Invalid array index")
            value = value[int(key)]
        elif isinstance(value, dict):
            value = value[key]
        else:
            raise TypeError("Selector traverses a scalar")
    return value


def register_claim(
    start: Path,
    *,
    claim: str,
    run_id: str,
    member: str = "metrics.json",
    selector: str = "",
    kind: str = "observation",
    relation: str = "supports",
    related_claim: str | None = None,
) -> ClaimRecord:
    with project_state_lock(start):
        if not verify_project_archive(start, run_id).valid:
            raise ValueError("Archive integrity failed")
        path = _member(start, run_id, member)
        payload = path.read_bytes()
        value = select_json(json.loads(payload), selector)
        if related_claim is not None and related_claim not in {c.id for c in list_claims(start)}:
            raise ValueError("Related claim does not exist")
        record = ClaimRecord(
            id=f"claim-{uuid4().hex[:16]}",
            claim=claim,
            run_id=run_id,
            member=member,
            selector=selector,
            sha256=hashlib.sha256(payload).hexdigest(),
            value=value,
            kind=kind,
            relation=relation,
            related_claim=related_claim,
        )
        write_json(_claims_dir(start) / f"{record.id}.json", record.model_dump(mode="json"))
        return record


def list_claims(start: Path) -> list[ClaimRecord]:
    records = []
    for path in sorted(_claims_dir(start).glob("claim-*.json")):
        if path.is_symlink():
            raise ValueError("Claim record must not be a symlink")
        record = ClaimRecord.model_validate_json(path.read_text())
        if record.id != path.stem:
            raise ValueError("Claim identity mismatch")
        records.append(record)
    return records


def _claim_hash(claim: ClaimRecord) -> str:
    payload = json.dumps(claim.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def register_anchor(
    start: Path,
    *,
    label: str,
    path: str,
    claim_id: str | None = None,
    context: str | None = None,
) -> ManuscriptAnchor:
    with project_state_lock(start):
        claims = {claim.id for claim in list_claims(start)}
        resolved = claim_id in claims if claim_id is not None else False
        if claim_id is not None and not resolved:
            raise ValueError("Claim anchor references an unknown claim")
        record = ManuscriptAnchor(
            id=f"anchor-{uuid4().hex[:16]}",
            label=label,
            path=_portable_project_path(path),
            claim_id=claim_id,
            resolved=resolved,
            context=context,
        )
        write_json(_claims_dir(start) / f"{record.id}.json", record.model_dump(mode="json"))
        return record


def list_anchors(start: Path) -> list[ManuscriptAnchor]:
    records = []
    for path in sorted(_claims_dir(start).glob("anchor-*.json")):
        if path.is_symlink():
            raise ValueError("Claim anchor must not be a symlink")
        record = ManuscriptAnchor.model_validate_json(path.read_text())
        if record.id != path.stem:
            raise ValueError("Claim anchor identity mismatch")
        records.append(record)
    return records


def claim_coverage(start: Path) -> dict[str, object]:
    claims = {claim.id for claim in list_claims(start)}
    anchors = list_anchors(start)
    unresolved = [anchor.model_dump(mode="json") for anchor in anchors if not anchor.resolved]
    anchored_claims = {anchor.claim_id for anchor in anchors if anchor.resolved and anchor.claim_id}
    missing = sorted(claims - anchored_claims)
    return {
        "schema_version": 1,
        "claims": len(claims),
        "anchors": len(anchors),
        "covered_claims": len(anchored_claims),
        "missing_claim_ids": missing,
        "unresolved_anchors": unresolved,
    }


def conformance_ladder(start: Path) -> dict[str, object]:
    claims = list_claims(start)
    claim_checks = [verify_claim(start, claim) for claim in claims]
    archives = {claim.run_id for claim in claims}
    archive_checks = {run_id: verify_project_archive(start, run_id) for run_id in archives}
    blockers = {
        "index": [],
        "trace": [],
        "replay": [],
        "verify": [],
    }
    if any(not check.valid for check in archive_checks.values()):
        blockers["index"].append("one or more archive records fail schema or checksum verification")
    coverage = claim_coverage(start)
    if coverage["missing_claim_ids"] or coverage["unresolved_anchors"]:
        blockers["trace"].append("manuscript claim anchors are incomplete")
    if any(check["reference_status"] != "PASS" for check in claim_checks):
        blockers["trace"].append("one or more claims do not resolve to recorded evidence")
    project = discover_project(start)
    for run_id in archives:
        archive = project.paths.runs / run_id
        if not all((archive / name).is_file() for name in ("source.tar.zst", "environment.json", "command.json")):
            blockers["replay"].append(f"{run_id} lacks replay source, environment or command evidence")
    if any(check["status"] not in {"PASS", "EXPLAINED"} for check in claim_checks):
        blockers["verify"].append("one or more claim assessments are missing or failing")
    levels = ("index", "trace", "replay", "verify")
    achieved = "none"
    inherited: list[str] = []
    results = {}
    for level in levels:
        inherited.extend(blockers[level])
        results[level] = {"passed": not inherited, "blockers": tuple(inherited)}
        if not inherited:
            achieved = level
    return {"schema_version": 1, "level": achieved, "levels": results, "coverage": coverage}


def assess_claim(start: Path, claim_id: str, *, status: str, author: str, note: str) -> dict:
    from datetime import UTC, datetime

    if status not in {"PASS", "FAIL", "EXPLAINED"} or not author.strip() or not note.strip():
        raise ValueError("Supply a passport disposition, author and substantive assessment note")
    with project_state_lock(start):
        claim = next((c for c in list_claims(start) if c.id == claim_id), None)
        if claim is None:
            raise ValueError("Claim does not exist")
        if verify_claim(start, claim)["reference_status"] != "PASS":
            raise ValueError("Resolve reference integrity before assessing claim support")
        record = {
            "id": f"assessment-{uuid4().hex[:16]}",
            "claim_id": claim_id,
            "claim_sha256": _claim_hash(claim),
            "status": status,
            "author": author,
            "note": note,
            "created_at": datetime.now(UTC).isoformat(),
        }
        write_json(_claims_dir(start) / f"{record['id']}.json", record)
        return record


def verify_claim(start: Path, claim: ClaimRecord) -> dict[str, object]:
    """Separate reference integrity from an explicit assessment of claim support."""
    reference_status = "UNVERIFIED"
    status = "UNVERIFIED"
    reason = "Claim support has not been assessed"
    assessment = None
    try:
        path = _member(start, claim.run_id, claim.member)
        payload = path.read_bytes()
        if (
            hashlib.sha256(payload).hexdigest() != claim.sha256
            or not verify_project_archive(start, claim.run_id).valid
        ):
            reference_status = status = "STALE"
            reason = "Referenced archive changed"
        elif select_json(json.loads(payload), claim.selector) != claim.value:
            reference_status = status = "FAIL"
            reason = "Selected value differs from registered observation"
        else:
            reference_status = "PASS"
            assessments = []
            for path in _claims_dir(start).glob("assessment-*.json"):
                if path.is_symlink():
                    raise ValueError("Assessment record must not be a symlink")
                item = json.loads(path.read_text())
                if item["claim_id"] == claim.id:
                    if (
                        item["status"] not in {"PASS", "FAIL", "EXPLAINED"}
                        or not item["author"]
                        or not item["note"]
                    ):
                        raise ValueError("Invalid claim assessment")
                    assessments.append(item)
            if assessments:
                assessment = max(assessments, key=lambda a: (a["created_at"], a["id"]))
                if assessment.get("claim_sha256") != _claim_hash(claim):
                    status = "STALE"
                    reason = "Claim content changed or assessment lacks a claim fingerprint"
                else:
                    status, reason = assessment["status"], assessment["note"]
    except (WaterologyError, ValueError, TypeError, KeyError, IndexError, OSError) as error:
        reason = str(error)
    return {
        "claim": claim.model_dump(mode="json"),
        "status": status,
        "reference_status": reference_status,
        "reason": reason,
        "assessment": assessment,
    }
