import re
from pathlib import Path

import yaml

from waterology.runtime.assets import AssetCatalog

ROOT = Path(__file__).resolve().parents[2]

EXPECTED_SKILLS = {
    "audit-reproducibility",
    "autoresearch",
    "bib-validate",
    "compile-latex",
    "diagrams",
    "figures",
    "literature-review",
    "project-conventions",
    "publish-blog-post",
    "r-code-style",
    "reports",
    "research-review",
    "research-software-quality",
    "setup-environment",
    "simulation-study",
    "sol-pi",
    "writing-style",
}


def test_skill_catalog_matches_focused_1_0_inventory() -> None:
    catalog = AssetCatalog.discover()
    names = {directory.name for directory in catalog.skill_directories()}
    assert names == EXPECTED_SKILLS


def test_no_skills_or_rules_invoke_config_context_shell_roundtrips() -> None:
    for directory in (ROOT / "skills", ROOT / "rules", ROOT / "agent-definitions"):
        for path in directory.rglob("*.md"):
            assert "config context" not in path.read_text(encoding="utf-8"), path


def test_writing_workflows_use_the_shared_style_skill() -> None:
    consumers = (
        ROOT / "agent-definitions/reviewer.md",
        ROOT / "skills/audit-reproducibility/SKILL.md",
        ROOT / "skills/autoresearch/SKILL.md",
        ROOT / "skills/diagrams/SKILL.md",
        ROOT / "skills/figures/SKILL.md",
        ROOT / "skills/literature-review/SKILL.md",
        ROOT / "skills/publish-blog-post/SKILL.md",
        ROOT / "skills/reports/SKILL.md",
        ROOT / "skills/research-review/SKILL.md",
        ROOT / "skills/simulation-study/SKILL.md",
    )
    for path in consumers:
        assert "writing-style" in path.read_text(encoding="utf-8"), path


def test_reports_skill_has_no_domain_specific_reservoir_leak_and_earth_tones_match() -> None:
    reports_text = (ROOT / "skills/reports/SKILL.md").read_text(encoding="utf-8")
    assert "52-week operating-rule" not in reports_text
    assert "guide curves" not in reports_text
    visual_design = (ROOT / "skills/figures/references/visual-design.md").read_text(
        encoding="utf-8"
    )
    assert "#2e6b4e" in visual_design
    assert "Okabe-Ito" not in (ROOT / "skills/figures/SKILL.md").read_text(encoding="utf-8")


def test_canonical_agents_enforce_delegation_and_quality_contracts() -> None:
    for path in sorted((ROOT / "agent-definitions").glob("*.md")):
        text = path.read_text(encoding="utf-8")
        assert "research-software-quality" in text, path
        assert "## Delegated task contract" in text, path
        assert "worktree" in text.lower(), path
        assert "compute" in text.lower(), path
        assert "output path" in text.lower(), path
        assert "do not merge" in text.lower(), path


def test_worktree_decision_fixtures_cover_the_cutoff() -> None:
    fixture_path = ROOT / "skills/research-software-quality/references/worktree-cases.yaml"
    data = yaml.safe_load(fixture_path.read_text(encoding="utf-8"))
    decisions = {case["id"]: case["decision"] for case in data["cases"]}
    assert decisions == {
        "already-isolated": "reuse",
        "behavioral-edit": "create",
        "clean-documentation": "work-in-place",
        "concurrent-writer": "create",
        "dirty-checkout": "create",
        "related-multi-file-change": "create",
    }


def test_skills_and_rules_leave_attribution_in_the_ledger() -> None:
    for directory in (ROOT / "skills", ROOT / "rules"):
        for path in directory.rglob("*.md"):
            text = path.read_text(encoding="utf-8")
            assert "<!--" not in text, path
            assert "attribution.md" not in text.lower(), path
            assert "adapted from" not in text.lower(), path
            assert "copyright" not in text.lower(), path

    for path in sorted((ROOT / "commands").glob("*.md")):
        command = path.read_text(encoding="utf-8")
        assert "<!-- Generated from skills/" in command, path
        assert "<!-- Adapted from" not in command, path
        assert not re.search(r"commit\s+[0-9a-f]{40}", command), path


def test_research_skills_are_portable_across_runtimes() -> None:
    for name in EXPECTED_SKILLS - {"sol-pi"}:
        path = ROOT / "skills" / name / "SKILL.md"
        text = path.read_text(encoding="utf-8")
        assert "CLAUDE_PLUGIN_ROOT" not in text, path
        assert "WebFetch" not in text, path
