import pytest

from waterology.core.studies import MetricRule, StudyContract, evaluate_metrics


def contract(**changes):
    return StudyContract.model_validate(
        {
            "mode": "engineering",
            "objective": "Meet the specification",
            "baseline_experiment": "exp-base",
            "allowed_paths": ["model.py"],
            "evaluation": {"data": "sha256:abc", "split": "fixed", "seeds": [42]},
            "acceptance": [
                {"name": "error", "unit": "m", "direction": "minimize", "threshold": 1.0}
            ],
            "max_iterations": 3,
            "max_seconds": 60,
            **changes,
        }
    )


def test_feasibility_precedes_optimization():
    spec = contract(
        acceptance=[
            {"name": "valid", "unit": "boolean", "direction": "maximize", "threshold": 1},
            {"name": "seconds", "unit": "s", "direction": "minimize", "threshold": 2},
        ]
    )
    assert evaluate_metrics(spec, {"valid": 0, "seconds": 0.1})["accepted"] is False
    assert evaluate_metrics(spec, {"valid": 1, "seconds": 1.5})["accepted"] is True


def test_missing_nonfinite_and_bool_values_are_not_measurements():
    spec = contract()
    for value in [None, float("nan"), float("inf"), True, "0.1"]:
        assert not evaluate_metrics(spec, {"error": value})["accepted"]


def test_research_does_not_accept_numeric_target_as_scientific_answer():
    assert not evaluate_metrics(contract(mode="research"), {"error": 0.1})["accepted"]


def test_contract_requires_bounded_scope():
    with pytest.raises(ValueError):
        contract(allowed_paths=["../escape"])
    with pytest.raises(ValueError):
        contract(max_seconds=0)
    with pytest.raises(ValueError):
        MetricRule(name="x", unit="m", threshold=float("nan"))
