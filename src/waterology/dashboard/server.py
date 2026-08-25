import threading
import time
import webbrowser
from pathlib import Path
from urllib.parse import urlencode

from waterology.dashboard.app import create_dashboard_app


def dashboard_url(host: str, port: int) -> str:
    display_host = {"0.0.0.0": "127.0.0.1", "::": "::1"}.get(host, host)
    if ":" in display_host and not display_host.startswith("["):
        display_host = f"[{display_host}]"
    return f"http://{display_host}:{port}/"


def run_dashboard(
    path: Path,
    *,
    host: str,
    port: int,
    open_browser: bool,
    allow_remote: bool,
    access_token: str | None,
) -> None:
    import uvicorn

    application = create_dashboard_app(
        path,
        host=host,
        allow_remote=allow_remote,
        access_token=access_token,
    )
    url = dashboard_url(host, port)
    config = uvicorn.Config(
        application,
        host=host,
        port=port,
        log_level="info",
        access_log=access_token is None,
    )
    server = uvicorn.Server(config)
    if open_browser:
        query = urlencode({"token": access_token}) if access_token else ""
        target = url + (f"?{query}" if query else "")
        thread = threading.Thread(
            target=_open_browser_when_started,
            args=(server, target),
            daemon=True,
        )
        thread.start()
    server.run()


def _open_browser_when_started(server: object, url: str) -> None:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if getattr(server, "started", False):
            webbrowser.open(url)
            return
        if getattr(server, "should_exit", False):
            return
        time.sleep(0.05)
