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
