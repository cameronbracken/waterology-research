from typer.testing import CliRunner

from waterology.cli import app

runner = CliRunner()


def test_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.stdout.strip() == "1.0.0"


def test_help_names_the_research_package() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Waterology research skills" in result.stdout


def test_validate_command_passes() -> None:
    result = runner.invoke(app, ["validate", "--json"])
    assert result.exit_code == 0
    assert '"status": "pass"' in result.stdout
