"""Manage optional private user configuration."""

import os
from pathlib import Path

import typer

from waterology.core.user_settings import user_config_path


def register_user_config_commands(config_app: typer.Typer) -> None:
    @config_app.command("path")
    def config_path() -> None:
        """Print the resolved global user configuration path."""
        typer.echo(str(user_config_path()))

    @config_app.command("init")
    def config_init() -> None:
        """Create empty private user settings without replacing an existing file."""
        source: Path = user_config_path()
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
                '[credentials]\nfile = "~/.config/secrets/research.env"\n\n'  # waterology: allow-abs-path
                '[identity]\nname = ""\nemail = ""\ngit_name = ""\norcid = ""\n\n'
                "[preferences]\nfiles = []\n\n"
                "[writing]\nfiles = []\npapers = []\n\n"
                "[guidance]\n"
            )
        typer.echo(f"Created user configuration: {source}")
