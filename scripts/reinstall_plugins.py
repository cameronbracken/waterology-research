#!/usr/bin/env python3
"""Reinstall local Waterology plugins during development."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Iterator, Sequence
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PLUGIN_ID = "waterology@waterology"
MARKETPLACE = "waterology"
RUNTIMES = ("codex", "claude")


class ReinstallError(RuntimeError):
    """Report a reinstall problem without a traceback."""


@dataclass(frozen=True)
class Installation:
    runtime: str
    scope: str | None
    enabled: bool


def detect_codex_install(payload: object) -> Installation | None:
    if not isinstance(payload, dict) or not isinstance(payload.get("installed"), list):
        raise ReinstallError("Codex returned an unexpected plugin list")
    for plugin in payload["installed"]:
        if isinstance(plugin, dict) and plugin.get("pluginId") == PLUGIN_ID:
            return Installation("codex", None, bool(plugin.get("enabled", True)))
    return None


def detect_claude_install(payload: object) -> Installation | None:
    if not isinstance(payload, list):
        raise ReinstallError("Claude returned an unexpected plugin list")
    for plugin in payload:
        if isinstance(plugin, dict) and plugin.get("id") == PLUGIN_ID:
            scope = plugin.get("scope", "user")
            if scope not in {"user", "project", "local"}:
                raise ReinstallError(f"Claude returned an unsupported install scope: {scope}")
            return Installation("claude", scope, bool(plugin.get("enabled", True)))
    return None


def select_runtimes(requested: str, installs: dict[str, Installation | None]) -> tuple[str, ...]:
    if requested == "auto":
        selected = tuple(runtime for runtime in RUNTIMES if installs.get(runtime) is not None)
        if not selected:
            raise ReinstallError(
                "No previous Waterology plugin installation was found. "
                "Pass --runtime codex, --runtime claude, or --runtime all for a first install."
            )
        return selected
    if requested == "all":
        return RUNTIMES
    return (requested,)


def marketplace_status(runtime: str, payload: object, project_root: Path) -> tuple[bool, bool]:
    entries: object
    if runtime == "codex":
        if not isinstance(payload, dict):
            raise ReinstallError("Codex returned an unexpected marketplace list")
        entries = payload.get("marketplaces")
    else:
        entries = payload
    if not isinstance(entries, list):
        raise ReinstallError(f"{runtime.title()} returned an unexpected marketplace list")

    expected = project_root.resolve()
    for entry in entries:
        if not isinstance(entry, dict) or entry.get("name") != MARKETPLACE:
            continue
        raw_path = entry.get("root") if runtime == "codex" else entry.get("path")
        if not isinstance(raw_path, str):
            raw_path = entry.get("installLocation")
        matches = isinstance(raw_path, str) and Path(raw_path).resolve() == expected
        return True, matches
    return False, False


def build_plan(
    runtime: str,
    install: Installation | None,
    *,
    marketplace_present: bool,
    marketplace_matches: bool,
    project_root: Path,
    requested_scope: str | None,
) -> tuple[tuple[str, ...], ...]:
    root = str(project_root.resolve())
    commands: list[tuple[str, ...]] = []
    if runtime == "codex":
        if install:
            commands.append(("codex", "plugin", "remove", PLUGIN_ID, "--json"))
        if marketplace_present and not marketplace_matches:
            commands.append(("codex", "plugin", "marketplace", "remove", MARKETPLACE, "--json"))
        if not marketplace_present or not marketplace_matches:
            commands.append(("codex", "plugin", "marketplace", "add", root, "--json"))
        commands.append(("codex", "plugin", "add", PLUGIN_ID, "--json"))
        return tuple(commands)

    scope = (install.scope if install else requested_scope) or "user"
    if install:
        commands.append(
            (
                "claude",
                "plugin",
                "uninstall",
                PLUGIN_ID,
                "--scope",
                scope,
                "--keep-data",
                "-y",
            )
        )
    if marketplace_present and not marketplace_matches:
        commands.append(
            ("claude", "plugin", "marketplace", "remove", MARKETPLACE, "--scope", scope)
        )
    if not marketplace_present or not marketplace_matches:
        commands.append(("claude", "plugin", "marketplace", "add", root, "--scope", scope))
    commands.append(("claude", "plugin", "install", PLUGIN_ID, "--scope", scope, "-y"))
    if install and not install.enabled:
        commands.append(("claude", "plugin", "disable", PLUGIN_ID, "--scope", scope))
    return tuple(commands)


def _atomic_write(path: Path, content: bytes) -> None:
    mode = path.stat().st_mode
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


@contextmanager
def cache_busted_manifests(project_root: Path) -> Iterator[str]:
    paths = (
        project_root / ".codex-plugin" / "plugin.json",
        project_root / ".claude-plugin" / "plugin.json",
    )
    originals = {path: path.read_bytes() for path in paths}
    payloads = {path: json.loads(content) for path, content in originals.items()}
    versions = {payload.get("version") for payload in payloads.values()}
    if len(versions) != 1 or not all(isinstance(version, str) for version in versions):
        raise ReinstallError("Plugin manifests must have one matching string version")
    base = next(iter(versions)).split("+", 1)[0]
    stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    version = f"{base}+dev.{stamp}.{os.getpid()}"
    try:
        for path, payload in payloads.items():
            payload["version"] = version
            _atomic_write(path, (json.dumps(payload, indent=2) + "\n").encode())
        yield version
    finally:
        for path, content in originals.items():
            _atomic_write(path, content)


def _run_json(command: Sequence[str], *, cwd: Path) -> Any:
    result = subprocess.run(command, check=False, capture_output=True, text=True, cwd=cwd)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "no error output"
        raise ReinstallError(f"Command failed ({' '.join(command)}): {detail}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise ReinstallError(f"Command returned invalid JSON: {' '.join(command)}") from error


def _execute(command: Sequence[str], *, cwd: Path) -> None:
    print(f"Running: {' '.join(command)}", flush=True)
    result = subprocess.run(command, check=False, cwd=cwd)
    if result.returncode != 0:
        raise ReinstallError(f"Command failed with exit {result.returncode}: {' '.join(command)}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Reinstall Waterology in previously configured agent runtimes."
    )
    parser.add_argument(
        "--runtime",
        choices=("auto", "codex", "claude", "all"),
        default="auto",
        help="runtimes to install; auto reinstalls only detected installations",
    )
    parser.add_argument(
        "--scope",
        choices=("user", "project", "local"),
        help="Claude scope for a first install; an existing scope is preserved by default",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="print actions without changing state"
    )
    parser.add_argument(
        "--no-cache-bust",
        action="store_true",
        help="reuse the manifest version instead of a temporary development version",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    project_root = Path(__file__).resolve().parents[1]
    probed = RUNTIMES if args.runtime in {"auto", "all"} else (args.runtime,)
    missing = [runtime for runtime in probed if shutil.which(runtime) is None]

    installs: dict[str, Installation | None] = {runtime: None for runtime in RUNTIMES}
    marketplace_payloads: dict[str, object] = {}
    if "codex" in probed and "codex" not in missing:
        installs["codex"] = detect_codex_install(
            _run_json(("codex", "plugin", "list", "--json"), cwd=project_root)
        )
        marketplace_payloads["codex"] = _run_json(
            ("codex", "plugin", "marketplace", "list", "--json"), cwd=project_root
        )
    if "claude" in probed and "claude" not in missing:
        installs["claude"] = detect_claude_install(
            _run_json(("claude", "plugin", "list", "--json"), cwd=project_root)
        )
        marketplace_payloads["claude"] = _run_json(
            ("claude", "plugin", "marketplace", "list", "--json"), cwd=project_root
        )

    selected = select_runtimes(args.runtime, installs)
    unavailable = [runtime for runtime in selected if runtime in missing]
    if unavailable:
        raise ReinstallError(f"Required runtime command not found: {', '.join(unavailable)}")

    plans: dict[str, tuple[tuple[str, ...], ...]] = {}
    for runtime in selected:
        present, matches = marketplace_status(runtime, marketplace_payloads[runtime], project_root)
        plans[runtime] = build_plan(
            runtime,
            installs[runtime],
            marketplace_present=present,
            marketplace_matches=matches,
            project_root=project_root,
            requested_scope=args.scope,
        )
        status = "detected" if installs[runtime] else "not installed"
        print(f"{runtime}: {status}")

    if args.dry_run:
        for runtime in selected:
            for command in plans[runtime]:
                print(f"Would run: {' '.join(command)}")
        return 0

    context = (
        nullcontext("unchanged") if args.no_cache_bust else cache_busted_manifests(project_root)
    )
    with context as version:
        print(f"Plugin version during install: {version}")
        for runtime in selected:
            for command in plans[runtime]:
                _execute(command, cwd=project_root)

    for runtime in selected:
        payload = _run_json((runtime, "plugin", "list", "--json"), cwd=project_root)
        detected = (
            detect_codex_install(payload) if runtime == "codex" else detect_claude_install(payload)
        )
        if detected is None:
            raise ReinstallError(f"{runtime.title()} did not report {PLUGIN_ID} after installation")
        print(f"{runtime}: installed")
    print("Start a new Codex thread or restart Claude Code before testing updated assets.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReinstallError as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
