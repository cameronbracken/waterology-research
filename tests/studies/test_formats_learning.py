import pytest


def test_nestedtext_contract_validates_numbers_without_guessing_identifiers(tmp_path):
    from waterology.core.formats import load_document
    from waterology.core.studies import StudyContract

    path = tmp_path / "study.nt"
    path.write_text("""mode: engineering
objective: Meet a target
baseline_experiment: exp-base
allowed_paths:
    - model.py
evaluation:
    station: 00123
acceptance:
    -
        name: error
        unit: m
        threshold: 0.5
max_iterations: 2
max_seconds: 60
""")
    spec = StudyContract.model_validate(load_document(path))
    assert spec.max_iterations == 2
    assert spec.acceptance[0].threshold == 0.5
    assert spec.evaluation["station"] == "00123"


def test_learning_requires_verification_and_expires_on_evidence_change(tmp_path):
    import subprocess

    from waterology.core.learning import assess_lesson, lesson_context, remember
    from waterology.core.project import initialize_project

    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    initialize_project(tmp_path)
    evidence = tmp_path / "check.txt"
    evidence.write_text("validated command and result")
    lesson = remember(
        tmp_path,
        trigger="torc worker",
        action="Use the declared wrapper",
        evidence=["check.txt"],
        outcome="Verified PATH",
        tags=["compute"],
    )
    assert lesson_context(tmp_path, "torc worker") == []
    assess_lesson(
        tmp_path, lesson["id"], status="verified", author="reviewer", note="Checked result"
    )
    assert len(lesson_context(tmp_path, "torc worker")) == 1
    assert lesson_context(tmp_path, "unrelated plotting") == []
    evidence.write_text("changed")
    assert lesson_context(tmp_path, "torc worker") == []


def test_learning_refuses_escaping_evidence(tmp_path):
    import subprocess

    from waterology.core.learning import remember
    from waterology.core.project import initialize_project

    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    initialize_project(tmp_path)
    with pytest.raises(ValueError):
        remember(tmp_path, trigger="x", action="y", evidence=["../outside"], outcome="z", tags=[])


def test_lesson_edit_invalidates_assessment_and_duplicate_id_cannot_rewrite(tmp_path):
    import subprocess

    from waterology.core.formats import load_document, write_document
    from waterology.core.learning import assess_lesson, inspect_lesson, remember
    from waterology.core.project import initialize_project

    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    initialize_project(tmp_path)
    (tmp_path / "evidence.txt").write_text("verified")
    args = {
        "trigger": "test",
        "action": "retain protocol",
        "evidence": ["evidence.txt"],
        "outcome": "matched",
        "tags": [],
    }
    lesson = remember(tmp_path, **args)
    assess_lesson(tmp_path, lesson["id"], status="verified", author="reviewer", note="checked")
    with pytest.raises(ValueError, match="different content"):
        remember(tmp_path, identifier=lesson["id"], **{**args, "action": "changed"})
    path = tmp_path / ".waterology/learning" / f"{lesson['id']}.nt"
    edited = load_document(path)
    edited["action"] = "changed"
    write_document(path, edited)
    assert inspect_lesson(tmp_path, lesson["id"])["status"] == "stale"
