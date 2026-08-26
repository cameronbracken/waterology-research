import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / "hooks/claim-reconcile.py"


def run_hook(project: Path, changed: Path, state: Path) -> subprocess.CompletedProcess[str]:
    payload = {
        "cwd": str(project),
        "hook_event_name": "PostToolUse",
        "tool_name": "Edit",
        "tool_input": {"file_path": str(changed)},
    }
    environment = os.environ.copy()
    environment["CLAUDE_PROJECT_DIR"] = str(project)
    environment["WATEROLOGY_HOOK_STATE_DIR"] = str(state)
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env=environment,
        check=False,
    )


def write_passport(project: Path) -> Path:
    passport = project / "quality_reports/passports/paper.yaml"
    passport.parent.mkdir(parents=True)
    passport.write_text(
        """paper:
  slug: paper
claims:
  - id: C1
    source_file: scripts/R/analyze.R
    source_line: 10
    output_file: results/main.csv
    output_field: estimate
    status: PASS
    notes: ""
  - id: C2
    source_file: scripts/python/analyze.py
    source_line: 20
    output_file: results/main.csv
    output_field: uncertainty
    status: EXPLAINED
    notes: "named alternative"
""",
        encoding="utf-8",
    )
    return passport


def test_hook_marks_only_claims_that_reference_the_changed_file(tmp_path: Path) -> None:
    passport = write_passport(tmp_path)
    changed = tmp_path / "scripts/R/analyze.R"
    changed.parent.mkdir(parents=True)
    changed.write_text("fit <- lm(y ~ x)\n", encoding="utf-8")

    result = run_hook(tmp_path, changed, tmp_path / "state")

    assert result.returncode == 0
    output = json.loads(result.stdout)
    assert output["hookSpecificOutput"]["hookEventName"] == "PostToolUse"
    assert "C1" in output["hookSpecificOutput"]["additionalContext"]
    claims = yaml.safe_load(passport.read_text(encoding="utf-8"))["claims"]
    assert [claim["status"] for claim in claims] == ["STALE", "EXPLAINED"]


def test_hook_throttles_nudges_without_skipping_stale_transition(tmp_path: Path) -> None:
    passport = write_passport(tmp_path)
    changed = tmp_path / "results/main.csv"
    changed.parent.mkdir(parents=True)
    changed.write_text("estimate,se\n1.2,0.1\n", encoding="utf-8")
    state = tmp_path / "state"

    first = run_hook(tmp_path, changed, state)
    data = yaml.safe_load(passport.read_text(encoding="utf-8"))
    for claim in data["claims"]:
        claim["status"] = "PASS"
    passport.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    second = run_hook(tmp_path, changed, state)

    assert first.stdout
    assert second.returncode == 0
    assert second.stdout == ""
    claims = yaml.safe_load(passport.read_text(encoding="utf-8"))["claims"]
    assert [claim["status"] for claim in claims] == ["STALE", "STALE"]


def test_hook_ignores_untracked_and_outside_files(tmp_path: Path) -> None:
    passport = write_passport(tmp_path)
    original = passport.read_text(encoding="utf-8")
    state = tmp_path / "state"

    untracked = tmp_path / "scripts/R/other.R"
    untracked.parent.mkdir(parents=True)
    untracked.write_text("print('other')\n", encoding="utf-8")
    outside = tmp_path.parent / "outside.R"

    assert run_hook(tmp_path, untracked, state).stdout == ""
    assert run_hook(tmp_path, outside, state).stdout == ""
    assert passport.read_text(encoding="utf-8") == original


def test_hook_fails_open_on_invalid_input() -> None:
    result = subprocess.run(
        [sys.executable, str(HOOK)],
        input="not json",
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""
