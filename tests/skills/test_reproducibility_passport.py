from pathlib import Path

import yaml

from waterology.runtime.assets import AssetCatalog
from waterology.runtime.skills import load_skills

ROOT = Path(__file__).resolve().parents[2]


def test_reproducibility_skill_and_passport_are_discoverable() -> None:
    catalog = AssetCatalog.discover()
    skills = {skill.name: skill for skill in load_skills(catalog)}
    skill = skills["audit-reproducibility"]

    assert "numeric claims" in skill.description.lower()
    assert skill.claude_command is not None
    assert skill.claude_command.name == "audit-reproducibility"
    assert (ROOT / "skills/audit-reproducibility/references/passport-schema.md").is_file()


def test_passport_template_carries_the_provenance_and_status_contract() -> None:
    template = yaml.safe_load((ROOT / "templates/passport.yaml").read_text(encoding="utf-8"))
    claim = template["claims"][0]

    assert {"source_file", "source_line", "output_file", "output_field"} <= set(claim)
    assert claim["status"] == "UNVERIFIED"
    assert claim["tolerance"] == {
        "point_estimate": 0.01,
        "standard_error": 0.05,
        "sample_size": "exact",
        "p_value": "same_significance_level",
        "percentage_points": 0.1,
    }


def test_passport_workflow_is_documented_and_recorded_complete() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")

    assert "/audit-reproducibility" in readme
    assert "Claude plugin hook" not in readme
    assert "Reproducibility passport (done 2026-08-25)" in roadmap
    assert "flag affected claims\n  STALE" not in roadmap
