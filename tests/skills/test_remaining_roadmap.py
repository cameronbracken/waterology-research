import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _load_script(relative: str):
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(path.stem.replace("-", "_"), path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_bundled_runtime_resources_match_root_assets() -> None:
    pairs = (
        (
            "rules/simulation-conventions.md",
            "skills/simulation-study/references/simulation-conventions.md",
        ),
        ("templates/run-all.sh", "skills/audit-reproducibility/templates/run-all.sh"),
        ("templates/latexmkrc", "skills/compile-latex/templates/latexmkrc"),
        ("constraints/overfull-boxes.py", "skills/compile-latex/scripts/overfull_boxes.py"),
    )
    for root_asset, bundled_asset in pairs:
        assert _read(root_asset) == _read(bundled_asset)


def test_monte_carlo_and_environment_capture_contracts() -> None:
    simulation = _read("skills/simulation-study/SKILL.md")
    conventions = _read("rules/simulation-conventions.md")
    reviewer = _read("agent-definitions/reviewer.md")
    capture = _read("skills/setup-environment/references/capture-environment.md")

    for text in (simulation, conventions, reviewer):
        assert "MCSE" in text
        assert "converge" in text.lower() or "failed" in text.lower()
    for stack in ("R", "Python", "Fortran"):
        assert stack in capture
    assert "sessionInfo.txt" in capture


def test_mcse_constraint_flags_result_tables_without_uncertainty(tmp_path: Path) -> None:
    result_file = tmp_path / "simulation_results.csv"
    result_file.write_text(
        "estimator,mean_bias,coverage_rate,rejection.rate,size\na,0.1,0.95,0.2,0.05\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, str(ROOT / "constraints/mc-has-mcse.py"), str(tmp_path)],
        capture_output=True,
        check=False,
        text=True,
    )
    assert result.returncode == 1
    assert str(result_file) in result.stdout

    result_file.write_text(
        "estimator,mean_bias,bias_mcse,coverage_rate,coverage_mcse,"
        "rejection.rate,rejection_mcse,size,size_mcse\n"
        "a,0.1,0.02,0.95,0.005,0.2,0.01,0.05,0.003\n",
        encoding="utf-8",
    )
    assert (
        subprocess.run(
            [sys.executable, str(ROOT / "constraints/mc-has-mcse.py"), str(tmp_path)],
            check=False,
        ).returncode
        == 0
    )


def test_bibliography_validator_contract_and_fuzzy_matching(tmp_path: Path) -> None:
    skill = _read("skills/bib-validate/SKILL.md")
    validator = _load_script("skills/bib-validate/scripts/validate_bib.py")

    assert "OpenAlex" in skill
    assert "Crossref" in skill
    assert "--verify-doi" in skill
    assert validator.edit_distance("bracken", "braken") == 1

    tex = tmp_path / "paper.tex"
    bib = tmp_path / "references.bib"
    tex.write_text(r"\cite{Braken2026}" + "\n", encoding="utf-8")
    bib.write_text(
        "@article{Bracken2026,\n  author={Bracken, Cameron},\n"
        "  title={Water systems},\n  year={2026}\n}\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "skills/bib-validate/scripts/validate_bib.py"),
            str(tex),
            str(bib),
        ],
        capture_output=True,
        check=False,
        text=True,
    )
    assert result.returncode == 1
    assert "likely typo" in result.stdout.lower()


def test_pipeline_and_conservation_constraints(tmp_path: Path) -> None:
    manifest_ref = _read("skills/audit-reproducibility/references/pipeline-manifest.md")
    for suffix in (".f90", ".F90", ".f"):
        assert suffix in manifest_ref
    assert "topological" in manifest_ref.lower()

    evidence = tmp_path / "conservation-check.yaml"
    evidence.write_text("metric: mass_balance\nerror: 0.002\ntolerance: 0.001\n", encoding="utf-8")
    assert (
        subprocess.run(
            [sys.executable, str(ROOT / "constraints/conservation-tol.py"), str(tmp_path)],
            check=False,
        ).returncode
        == 1
    )
    evidence.write_text("metric: mass_balance\nerror: 0.0002\ntolerance: 0.001\n", encoding="utf-8")
    assert (
        subprocess.run(
            [sys.executable, str(ROOT / "constraints/conservation-tol.py"), str(tmp_path)],
            check=False,
        ).returncode
        == 0
    )


def test_myst_converter_and_document_constraints(tmp_path: Path) -> None:
    converter = _load_script("skills/project-conventions/scripts/myst_to_quarto.py")
    converted = converter.convert_myst("{cite:p}`Bracken2026`\n\n:::{warning} Check\nBody.\n:::\n")
    assert "[@Bracken2026]" in converted
    assert '::: {.callout-warning title="Check"}' in converted

    log = tmp_path / "paper.log"
    log.write_text(
        "Overfull \\hbox (12.5pt too wide) in paragraph at lines 4--5\n",
        encoding="utf-8",
    )
    assert (
        subprocess.run(
            [sys.executable, str(ROOT / "constraints/overfull-boxes.py"), str(tmp_path)],
            check=False,
        ).returncode
        == 1
    )

    qmd = tmp_path / "results.qmd"
    qmd.write_text("The fitted effect was 12.4% (p < 0.01).\n", encoding="utf-8")
    assert (
        subprocess.run(
            [sys.executable, str(ROOT / "constraints/no-hardcoded-results.py"), str(tmp_path)],
            check=False,
        ).returncode
        == 1
    )
