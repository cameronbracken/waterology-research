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
        ("templates/run-all.sh", "skills/pipeline-manifest/templates/run-all.sh"),
        ("templates/latexmkrc", "skills/compile-latex/templates/latexmkrc"),
        ("constraints/overfull-boxes.py", "skills/compile-latex/scripts/overfull_boxes.py"),
    )
    for root_asset, bundled_asset in pairs:
        assert _read(root_asset) == _read(bundled_asset)


def test_slice_3_monte_carlo_contract_is_complete() -> None:
    simulation = _read("skills/simulation-study/SKILL.md")
    conventions = _read("rules/simulation-conventions.md")
    r_reviewer = _read("agent-definitions/r-reviewer.md")
    sim_reviewer = _read("agent-definitions/sim-reviewer.md")

    for text in (simulation, conventions, sim_reviewer):
        assert "coverage" in text.lower()
        assert "truth" in text.lower()
        assert "MCSE" in text
        assert "failed" in text.lower() or "non-converged" in text.lower()
        assert "raw" in text.lower()
    assert "generate_data" in simulation
    assert "L'Ecuyer-CMRG" in simulation
    assert "11" in r_reviewer
    assert "hydrology" in r_reviewer.lower()
    assert "coverage-against-the-estimate" in sim_reviewer


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
    result_file.write_text("estimator,size\na,0.05\n", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(ROOT / "constraints/mc-has-mcse.py"), str(tmp_path)],
        capture_output=True,
        check=False,
        text=True,
    )
    assert result.returncode == 1
    assert "power" in result.stdout
    result_file.write_text(
        "estimator,mean_bias,bias_mcse,coverage_rate,coverage_mcse,"
        "rejection.rate,rejection_mcse,size,size_mcse\n"
        "a,0.1,0.02,0.95,0.005,0.2,0.01,0.05,0.003\n",
        encoding="utf-8",
    )
    assert subprocess.run(
        [sys.executable, str(ROOT / "constraints/mc-has-mcse.py"), str(tmp_path)],
        check=False,
    ).returncode == 0


def test_slice_4_reproducibility_capture_covers_supported_stacks() -> None:
    auditor = _read("agent-definitions/reproducibility-auditor.md")
    capture = _read("skills/capture-environment/SKILL.md")

    for dimension in (
        "entry points",
        "dependencies",
        "path hygiene",
        "hidden assumptions",
        "output traceability",
        "exploratory",
    ):
        assert dimension in auditor.lower()
    for status in ("GREEN", "YELLOW", "RED"):
        assert status in auditor
    assert "12-row" in auditor
    for stack in ("R", "Python", "Fortran"):
        assert stack in capture
    assert "compiler" in capture.lower()
    assert "flags" in capture.lower()
    assert "sessionInfo.txt" in capture


def test_slice_5_bibliography_validator_contract_and_fuzzy_matching(tmp_path: Path) -> None:
    skill = _read("skills/bib-validate/SKILL.md")
    rule = _read("rules/no-hallucinated-citations.md")
    validator = _load_script("skills/bib-validate/scripts/validate_bib.py")

    assert "OpenAlex" in skill
    assert "Crossref" in skill
    assert "--verify-doi" in skill
    assert "--fix" in skill
    assert "0.95" in skill
    assert "fabrication" in skill.lower()
    assert "DOI" in rule
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
        [sys.executable, str(ROOT / "skills/bib-validate/scripts/validate_bib.py"), str(tex), str(bib)],
        capture_output=True,
        check=False,
        text=True,
    )
    assert result.returncode == 1
    assert "likely typo" in result.stdout.lower()


def test_bibliography_validator_reads_quarto_and_checks_doi_metadata(monkeypatch) -> None:
    validator = _load_script("skills/bib-validate/scripts/validate_bib.py")
    assert validator.bibliography_entries(
        "@article{Compact2026, title={Water systems}, author={Bracken, Cameron}, "
        "year={2026}, doi={10.1234/example}}\n"
    ) == {
        "Compact2026": {
            "title": "Water systems",
            "author": "Bracken, Cameron",
            "year": "2026",
            "doi": "10.1234/example",
        }
    }
    citations = validator.citation_keys(
        "Quarto cites [@Bracken2026; @Doe2025] and @Smith2024.\n"
        "```python\n@not_a_citation\n```\n"
    )
    assert citations == {"Bracken2026", "Doe2025", "Smith2024"}

    monkeypatch.setattr(
        validator,
        "request_json",
        lambda _url: {
            "id": "https://openalex.org/W1",
            "title": "An unrelated paper",
            "publication_year": 1999,
            "authorships": [{"author": {"display_name": "Other, Author"}}],
        },
    )
    status, detail = validator.verify_doi(
        "10.1234/example",
        {"title": "Water systems", "author": "Bracken, Cameron", "year": "2026"},
    )
    assert status == "FAIL"
    assert "title" in detail
    status, detail = validator.verify_doi("10.1234/example", {})
    assert status == "UNVERIFIED"
    assert "title" in detail and "first author" in detail and "year" in detail


def test_slice_6_pipeline_and_conservation_contract(tmp_path: Path) -> None:
    skill = _read("skills/pipeline-manifest/SKILL.md")
    template = _read("templates/run-all.sh")

    for suffix in (".f90", ".F90", ".f"):
        assert suffix in skill
    assert "topological" in skill.lower()
    assert "gfortran" in template
    assert "Rscript" in template
    assert "python3" in template

    evidence = tmp_path / "conservation-check.yaml"
    evidence.write_text("metric: mass_balance\nerror: 0.002\ntolerance: 0.001\n", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(ROOT / "constraints/conservation-tol.py"), str(tmp_path)],
        capture_output=True,
        check=False,
        text=True,
    )
    assert result.returncode == 1
    assert "mass_balance" in result.stdout
    evidence.write_text("metric: mass_balance\nerror: 0.0002\ntolerance: 0.001\n", encoding="utf-8")
    assert subprocess.run(
        [sys.executable, str(ROOT / "constraints/conservation-tol.py"), str(tmp_path)],
        check=False,
    ).returncode == 0


def test_slice_7_document_build_tools(tmp_path: Path) -> None:
    converter = _load_script("skills/myst-to-quarto/scripts/myst_to_quarto.py")
    source = """# Result

{cite:p}`Bracken2026`, {cite:t}`Doe2025`, and {cite}`Smith2024`

```{note}
Check this.
```{python}
value = 1
```
```

:::{warning} Important title
Colon fenced callout.
:::

```{figure} figure.png
  :name: fig-result
  :alt: Result figure
  :width: 80%
  :height: 400px
  :align: center
  :class: framed wide
  :loading: lazy
Result caption.
```
"""
    converted = converter.convert_myst(source)
    assert "[@Bracken2026]" in converted
    assert "@Doe2025" in converted
    assert "@Smith2024" in converted
    assert "[@Smith2024]" not in converted
    assert "::: {.callout-note}" in converted
    assert "```{python}\nvalue = 1\n```\n:::" in converted
    assert '::: {.callout-warning title="Important title"}\nColon fenced callout.\n:::' in converted
    assert "![Result caption.](figure.png){" in converted
    for attribute in (
        "#fig-result",
        'fig-alt="Result figure"',
        'width="80%"',
        'height="400px"',
        'fig-align="center"',
        ".framed",
        ".wide",
        'data-myst-loading="lazy"',
    ):
        assert attribute in converted

    log = tmp_path / "paper.log"
    log.write_text(
        "Overfull \\hbox (12.5pt too wide) in paragraph at lines 4--5\n"
        "Overfull \\hbox (0.5pt too wide) in paragraph at line 8\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, str(ROOT / "constraints/overfull-boxes.py"), str(tmp_path)],
        capture_output=True,
        check=False,
        text=True,
    )
    assert result.returncode == 1
    assert "major" in result.stdout.lower()
    assert "12.5" in result.stdout
    assert "0.5" not in result.stdout

    qmd = tmp_path / "results.qmd"
    qmd.write_text("The fitted effect was 12.4% (p < 0.01).\n", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(ROOT / "constraints/no-hardcoded-results.py"), str(tmp_path)],
        capture_output=True,
        check=False,
        text=True,
    )
    assert result.returncode == 1
    assert str(qmd) in result.stdout

    layout_dir = tmp_path / "layout"
    layout_dir.mkdir()
    layout = layout_dir / "layout.qmd"
    layout.write_text(
        "---\ntitle: Layout\nfig-width: 80%\n---\n\n"
        "![](figure.png){width=100%}\n<div style=\"width: 75%\">Panel</div>\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, str(ROOT / "constraints/no-hardcoded-results.py"), str(layout_dir)],
        capture_output=True,
        check=False,
        text=True,
    )
    assert result.returncode == 0, result.stdout

    prose_dir = tmp_path / "prose"
    prose_dir.mkdir()
    prose = prose_dir / "results.qmd"
    prose.write_text("The confidence interval width = 12.5%.\n", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(ROOT / "constraints/no-hardcoded-results.py"), str(prose_dir)],
        capture_output=True,
        check=False,
        text=True,
    )
    assert result.returncode == 1
    assert str(prose) in result.stdout

    mixed_dir = tmp_path / "mixed"
    mixed_dir.mkdir()
    mixed = mixed_dir / "results.tex"
    mixed.write_text(r"Estimate: \input{estimate}; p < 0.01" + "\n", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(ROOT / "constraints/no-hardcoded-results.py"), str(mixed_dir)],
        capture_output=True,
        check=False,
        text=True,
    )
    assert result.returncode == 1
    assert str(mixed) in result.stdout

    compile_skill = _read("skills/compile-latex/SKILL.md")
    assert "latexmk" in compile_skill
    assert "XeLaTeX" in compile_skill
    assert "overfull-boxes" in compile_skill
    assert _read("templates/latexmkrc")
