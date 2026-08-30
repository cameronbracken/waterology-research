from pathlib import Path

from waterology.runtime.skills import parse_skill

ROOT = Path(__file__).resolve().parents[2]
SKILL_PATH = ROOT / "skills/paper-writing/SKILL.md"


def test_write_a_report_routes_to_paper_writing() -> None:
    skill = parse_skill(SKILL_PATH)

    assert "write a report" in skill.description.lower()


def test_write_a_document_routes_to_paper_mode() -> None:
    skill = parse_skill(SKILL_PATH)

    assert "document" in skill.description.lower()


def test_report_mode_targets_results_summaries_with_interactive_graphics() -> None:
    instructions = SKILL_PATH.read_text(encoding="utf-8")

    required_contract = (
        "Interactive graphics are the primary content",
        "summary metrics",
        "parameterized",
        "params",
    )
    for requirement in required_contract:
        assert requirement in instructions


def test_paper_mode_requires_academic_writing_and_publication_figures() -> None:
    instructions = SKILL_PATH.read_text(encoding="utf-8")

    assert "academic quality writing" in instructions
    assert "publication quality figures" in instructions


def test_report_mode_builds_and_reviews_a_cited_interactive_quarto_report() -> None:
    instructions = SKILL_PATH.read_text(encoding="utf-8")

    required_contract = (
        "Report mode",
        ".qmd",
        "quarto render",
        "bib-validate",
        "research-review",
        "embed-resources: true",
        "light: flatly",
        "dark: darkly",
        "Plotly",
        "figure-style",
        "project-conventions",
    )
    for requirement in required_contract:
        assert requirement in instructions

    assert "invent" in instructions.lower()
    assert "provenance" in instructions.lower()
