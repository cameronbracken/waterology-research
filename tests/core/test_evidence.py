import subprocess
from pathlib import Path

import pytest

from waterology.core.evidence import (
    EvidencePathError,
    EvidenceRelationshipError,
    list_artifact_references,
    list_evidence,
    register_artifact_reference,
    register_evidence,
)
from waterology.core.experiments import create_experiment
from waterology.core.project import initialize_project


def make_experiment(path: Path) -> tuple[Path, str, Path]:
    path.mkdir()
    subprocess.run(["git", "init", "--quiet", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "Test"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "test@example.org"], check=True)
    initialize_project(path)
    (path / "model.py").write_text("print('baseline')\n", encoding="utf-8")
    subprocess.run(
        ["git", "-C", str(path), "add", "model.py", "waterology.toml", ".gitignore"],
        check=True,
    )
    subprocess.run(["git", "-C", str(path), "commit", "--quiet", "-m", "base"], check=True)
    experiment = create_experiment(
        path,
        hypothesis="Evidence supports this experiment.",
        experiment_id="exp-evidence",
    )
    return path, experiment.id, path / experiment.worktree


def test_register_and_list_note_evidence(tmp_path: Path) -> None:
    root, experiment_id, _worktree = make_experiment(tmp_path / "study")

    evidence = register_evidence(
        root,
        experiment_id=experiment_id,
        claim="The baseline RMSE is 2.1.",
        kind="metric",
        evidence_id="evidence-1111111111111111",
    )

    assert list_evidence(root, experiment_id=experiment_id) == (evidence,)
    assert (root / ".waterology" / "evidence" / f"{evidence.id}.json").is_file()


def test_register_artifact_requires_existing_file_inside_experiment_worktree(
    tmp_path: Path,
) -> None:
    root, experiment_id, worktree = make_experiment(tmp_path / "study")
    figure = worktree / "artifacts" / "comparison.png"
    figure.parent.mkdir(exist_ok=True)
    figure.write_bytes(b"png")

    artifact = register_artifact_reference(
        root,
        experiment_id=experiment_id,
        path=f".waterology/worktrees/{experiment_id}/artifacts/comparison.png",
        label="RMSE comparison",
        artifact_id="artifact-2222222222222222",
    )

    assert artifact.path.endswith("artifacts/comparison.png")
    assert list_artifact_references(root, experiment_id=experiment_id) == (artifact,)


@pytest.mark.parametrize("path", ["../secret.txt", "/tmp/secret.txt", "model.py"])
def test_register_artifact_rejects_paths_outside_durable_scope(tmp_path: Path, path: str) -> None:
    root, experiment_id, _worktree = make_experiment(tmp_path / "study")
    (root / "model.py").write_text("secret\n", encoding="utf-8")

    with pytest.raises(EvidencePathError):
        register_artifact_reference(root, experiment_id=experiment_id, path=path)


def test_register_artifact_rejects_another_experiment_worktree(tmp_path: Path) -> None:
    root, experiment_id, _worktree = make_experiment(tmp_path / "study")
    other = create_experiment(
        root,
        hypothesis="Keep evidence provenance separate.",
        experiment_id="exp-other",
    )
    artifact = root / other.worktree / "artifacts" / "other.txt"
    artifact.parent.mkdir(exist_ok=True)
    artifact.write_text("other\n", encoding="utf-8")

    with pytest.raises(EvidenceRelationshipError, match="another experiment"):
        register_artifact_reference(
            root,
            experiment_id=experiment_id,
            path=f"{other.worktree}/artifacts/other.txt",
        )
