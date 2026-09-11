"""Read personal guidance on demand without embedding it in installations."""

import json
import os
import subprocess
import sys
from pathlib import Path

import typer

from waterology.core.profiles import (
    MachineConfigError,
    load_machine_config,
    machine_config_path,
)


def local_context(section: str) -> dict:
    source = machine_config_path()
    config = load_machine_config(source)
    files = list(config.preferences.files)
    result = {"guidance": [], "papers": []}
    if section == "project-conventions":
        result["identity"] = config.identity.model_dump(exclude_defaults=True)
    if section == "writing-style":
        files.extend(config.writing.files)
        result["papers"] = list(config.writing.papers)
    files.extend(config.guidance.get(section, ()))
    for name in dict.fromkeys(files):
        path = Path(name).expanduser()
        if not path.is_absolute():
            path = source.parent / path
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            raise MachineConfigError(f"Cannot read local guidance: {path}") from error
        result["guidance"].append({"path": str(path), "content": content})
    return result


def register_user_config_commands(config_app: typer.Typer) -> None:

    @config_app.command("path")
    def config_path() -> None:
        """Print the resolved global configuration path."""
        typer.echo(str(machine_config_path()))

    @config_app.command("init")
    def config_init() -> None:
        """Create empty settings without replacing an existing configuration."""
        source = machine_config_path()
        try:
            source.parent.mkdir(parents=True, exist_ok=True)
            descriptor = os.open(source, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            typer.echo(f"Configuration already exists: {source}")
            return
        except OSError:
            typer.echo("Cannot create user configuration", err=True)
            raise typer.Exit(1) from None
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(
                "# Private user configuration. Keep outside version control.\n"
                "trusted_profiles = []\n\n"
                '[identity]\nname = ""\nemail = ""\ngit_name = ""\norcid = ""\n\n'
                "[preferences]\nfiles = []\n\n"
                "[writing]\nfiles = []\npapers = []\n\n"
                "[guidance]\n"
            )
        typer.echo(f"Created user configuration: {source}")

    @config_app.command("context")
    def context(section: str) -> None:
        """Read the selected skill's local guidance. Output may be private."""
        try:
            typer.echo(json.dumps(local_context(section), indent=2))
        except (MachineConfigError, OSError) as error:
            typer.echo(str(error), err=True)
            raise typer.Exit(1) from None

    @config_app.command("dashboard")
    def dashboard(dry_run: bool = typer.Option(False, "--dry-run")) -> None:
        """Launch torc-dash using a local profile and environment credentials."""
        try:
            config = load_machine_config()
            settings = config.dashboard
            if not settings.profile:
                raise MachineConfigError("Set dashboard.profile in the user configuration")
            profile = config.profile(settings.profile)
            command = ["torc-dash", "--host", settings.host, "--api-url", profile.api_url]
            if dry_run:
                typer.echo(json.dumps(command))
                return
            environment = os.environ.copy()
            for name, value in (
                ("LLM_PROVIDER", settings.llm_provider),
                ("OPENAI_BASE_URL", settings.openai_base_url),
                ("OPENAI_MODEL", settings.openai_model),
            ):
                if value:
                    environment[name] = value
            if settings.api_key_env:
                if not environment.get(settings.api_key_env):
                    raise MachineConfigError("Configured dashboard API key environment is missing")
                environment["OPENAI_API_KEY"] = environment[settings.api_key_env]
            if settings.torc_password_keychain_service and not environment.get("TORC_PASSWORD"):
                if sys.platform != "darwin":
                    raise MachineConfigError("Set TORC_PASSWORD; Keychain requires macOS")
                lookup = subprocess.run(
                    [
                        "security",
                        "find-generic-password",
                        "-a",
                        environment.get("USER", ""),
                        "-s",
                        settings.torc_password_keychain_service,
                        "-w",
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if lookup.returncode or not lookup.stdout.strip():
                    raise MachineConfigError("Cannot read configured TORC Keychain credential")
                environment["TORC_PASSWORD"] = lookup.stdout.strip()
            raise typer.Exit(subprocess.call(command, env=environment))
        except (MachineConfigError, OSError) as error:
            typer.echo(str(error), err=True)
            raise typer.Exit(1) from None
