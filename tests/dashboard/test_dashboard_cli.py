from pathlib import Path
from types import SimpleNamespace

from typer.testing import CliRunner

from waterology.cli import app
from waterology.dashboard import server

runner = CliRunner()


def test_dashboard_command_passes_server_configuration(
    monkeypatch: object, tmp_path: Path
) -> None:
    captured: dict[str, object] = {}

    def fake_run(path: Path, **values: object) -> None:
        captured.update({"path": path, **values})

    monkeypatch.setattr(server, "run_dashboard", fake_run)  # type: ignore[attr-defined]

    result = runner.invoke(
        app,
        [
            "dashboard",
            "--path",
            str(tmp_path),
            "--host",
            "127.0.0.1",
            "--port",
            "9123",
            "--no-open",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert captured == {
        "path": tmp_path,
        "host": "127.0.0.1",
        "port": 9123,
        "open_browser": False,
        "allow_remote": False,
        "access_token": None,
    }


def test_dashboard_url_uses_loopback_for_wildcard_bind() -> None:
    assert server.dashboard_url("0.0.0.0", 8127) == "http://127.0.0.1:8127/"
    assert server.dashboard_url("::", 8127) == "http://[::1]:8127/"


def test_browser_opens_only_after_selected_server_starts(monkeypatch: object) -> None:
    opened: list[str] = []
    monkeypatch.setattr(server.webbrowser, "open", opened.append)  # type: ignore[attr-defined]

    server._open_browser_when_started(SimpleNamespace(started=True, should_exit=False), "url")
    server._open_browser_when_started(SimpleNamespace(started=False, should_exit=True), "secret")

    assert opened == ["url"]
