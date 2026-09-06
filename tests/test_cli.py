from typer.testing import CliRunner

from waterology.cli import app

runner = CliRunner()


def test_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.stdout.strip() == "0.5.2"


def test_help_names_the_research_package() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Waterology research workflows" in result.stdout
