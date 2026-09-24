import json

from typer.testing import CliRunner

from waterology.cli import app
from waterology.core.formats import load_document
from waterology.core.studies import StudyContract


def test_engineering_init_is_bounded_and_does_not_start_execution(tmp_path):
    destination = tmp_path / "engineering.nt"
    result = CliRunner().invoke(
        app,
        [
            "engineering",
            "init",
            str(destination),
            "--objective",
            "Implement the parser",
            "--workflow",
            "qualify",
            "--allow-path",
            "src/parser",
            "--max-iterations",
            "4",
            "--max-seconds",
            "600",
        ],
    )
    assert result.exit_code == 0, result.output
    data = load_document(destination)
    contract = StudyContract.model_validate({**data, "baseline_experiment": "exp-baseline"})
    assert contract.mode == "engineering"
    assert contract.candidate_strategy == "latest_completed"
    assert contract.acceptance[0].name == "failed_checks"
    assert not (tmp_path / ".waterology").exists()
    assert (
        CliRunner()
        .invoke(
            app,
            [
                "engineering",
                "init",
                str(destination),
                "--objective",
                "Replace",
                "--workflow",
                "qualify",
                "--allow-path",
                "src",
                "--max-iterations",
                "4",
                "--max-seconds",
                "600",
            ],
        )
        .exit_code
        != 0
    )


def test_engineering_optimization_keeps_correctness_gate(tmp_path):
    destination = tmp_path / "optimize.nt"
    result = CliRunner().invoke(
        app,
        [
            "engineering",
            "init",
            str(destination),
            "--objective",
            "Reduce runtime",
            "--workflow",
            "benchmark",
            "--allow-path",
            "src",
            "--max-iterations",
            "3",
            "--max-seconds",
            "120",
            "--target-seconds",
            "2.5",
        ],
    )
    assert result.exit_code == 0, result.output
    data = load_document(destination)
    contract = StudyContract.model_validate({**data, "baseline_experiment": "exp-baseline"})
    assert [r.name for r in contract.acceptance] == ["failed_checks", "elapsed"]
    assert contract.promotion_metric == "elapsed"
    assert contract.candidate_strategy == "best"


def test_engineering_create_rejects_research_before_mutation(tmp_path):
    path = tmp_path / "research.json"
    path.write_text(json.dumps({"mode": "research"}))
    result = CliRunner().invoke(
        app,
        ["engineering", "create", str(path), "--authorized-by", "test", "--path", str(tmp_path)],
    )
    assert result.exit_code == 1
    assert "engineering" in result.output
    assert not (tmp_path / ".waterology").exists()


def test_existing_contract_serialization_and_partial_candidate_ancestry():
    from types import SimpleNamespace

    from test_contracts import contract

    from waterology.core.study_driver import candidate_parent

    original = contract()
    assert "candidate_strategy" not in original.model_dump()
    previous = SimpleNamespace(
        state="completed", assessment={"accepted": False}, run_id="run-partial"
    )
    unresolved = SimpleNamespace(state="running", assessment=None, run_id="run-unknown")
    record = SimpleNamespace(
        contract=original.model_copy(update={"candidate_strategy": "latest_completed"}),
        attempts=[previous, unresolved],
        best_run=None,
    )
    assert candidate_parent(record) is previous
    record.contract = original
    assert candidate_parent(record) is None
