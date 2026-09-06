"""Qualify named TORC jobs and portable reproduction through the CLI on loopback."""

import argparse
import json
import os
import platform
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

from waterology.core.config import WorkflowConfig
from waterology.core.project import initialize_project
from waterology.core.registry import register_workflow


def call(arguments, root, *, environment=None):
    print("Running:", " ".join(arguments[:4]), flush=True)
    return subprocess.run(
        arguments,
        cwd=root,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
        timeout=180,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    root = args.destination.resolve()
    root.mkdir(parents=True, exist_ok=False)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    api = f"http://127.0.0.1:{port}/torc-service/v1"
    environment = dict(os.environ)
    for key in ("TORC_PASSWORD", "TORC_AUTH_FILE", "TORC_COOKIE_HEADER", "DATABASE_URL"):
        environment.pop(key, None)
    machine = root / "machine.toml"
    machine.write_text(f'[profiles.local]\nmode="local"\napi_url="{api}"\n')
    environment["WATEROLOGY_CONFIG"] = str(machine)
    with (root / "server.log").open("w") as log:
        server = subprocess.Popen(
            [
                "torc-server",
                "run",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--database",
                str(root / "torc.sqlite"),
                "--completion-check-interval-secs",
                "1",
            ],
            stdout=log,
            stderr=log,
            env=environment,
        )
        try:
            for _ in range(100):
                try:
                    with urlopen(api + "/workflows", timeout=1):
                        break
                except OSError:
                    time.sleep(0.2)
            project = root / "project"
            project.mkdir()
            call(["git", "init", "-q"], project)
            call(["git", "config", "user.name", "Waterology fixture"], project)
            call(["git", "config", "user.email", "fixture@example.org"], project)
            target = (
                ("osx-arm64" if platform.machine() == "arm64" else "osx-64")
                if sys.platform == "darwin"
                else "win-64"
                if sys.platform == "win32"
                else "linux-64"
            )
            (project / "pixi.toml").write_text(
                f'[workspace]\nname="workflow-fixture"\nchannels=["conda-forge"]\nplatforms=["{target}"]\n[dependencies]\npython=">=3.11,<3.15"\n[tasks]\nprepare="python prepare.py"\nsimulate="python simulate.py"\n'
            )
            call(["pixi", "install"], project, environment=environment)
            initialize_project(project)
            (project / ".gitignore").write_text(".waterology/\n.pixi/\nresults/\n")
            (project / "prepare.py").write_text(
                'from pathlib import Path\nPath("results").mkdir(exist_ok=True)\nPath("results/part.json").write_text(\'{"value": 2.0}\')\n'
            )
            (project / "simulate.py").write_text(
                'from pathlib import Path\nPath("results/value.json").write_bytes(Path("results/part.json").read_bytes())\n'
            )
            (project / "workflows").mkdir()
            (project / "workflows/evaluate.yaml").write_text("""name: evaluate
jobs:
  - name: prepare
    command: pixi run --locked prepare
  - name: simulate
    command: pixi run --locked simulate
    depends_on: [prepare]
""")
            register_workflow(
                project,
                "evaluate",
                WorkflowConfig(
                    torc_file="workflows/evaluate.yaml",
                    outputs=("results/value.json",),
                    environment_files=("pixi.toml", "pixi.lock"),
                    restore=(("pixi", "install", "--locked"),),
                    environment_probe=("pixi", "info", "--json"),
                ),
            )
            config = project / "waterology.toml"
            config.write_text(
                config.read_text().replace(
                    'artifact_roots = ["artifacts"]', 'artifact_roots = ["results"]'
                )
            )
            call(["git", "add", "."], project)
            call(["git", "-c", "commit.gpgsign=false", "commit", "-qm", "Fixture source"], project)
            cli = [sys.executable, "-m", "waterology", "--output-format", "json"]
            result = call(
                [*cli, "workflow", "run", "evaluate", "--profile", "local"],
                project,
                environment=environment,
            )
            (root / "workflow.log").write_text(result.stdout)
            archives = list((project / ".waterology/runs").glob("run-*"))
            assert len(archives) == 1
            definition = project / "deliverable.nt"
            definition.write_text(f"""workflow: evaluate
reference_run: {archives[0].name}
checks:
    -
        path: results/value.json
        mode: numeric
        field: value
        atol: 0.000001
""")
            call(
                [*cli, "deliverable", "register", "final", str(definition)],
                project,
                environment=environment,
            )
            bundle = root / "export"
            call(
                [*cli, "deliverable", "export", "final", str(bundle)],
                project,
                environment=environment,
            )
            project.rename(root / "original-unavailable")
            result = call(
                [
                    *cli,
                    "reproduce",
                    "final",
                    str(root / "reproduction"),
                    "--path",
                    str(bundle),
                    "--bundle",
                    "--profile",
                    "local",
                ],
                root,
                environment=environment,
            )
            (root / "reproduction.log").write_text(result.stdout)
            record = json.loads((root / "reproduction/reproduction.json").read_text())
            assert record["state"] == "passed", record
            (root / "validation.json").write_text(
                json.dumps({"state": "passed", "reproduction": record}, indent=2) + "\n"
            )
            print("Passed:", root / "validation.json", flush=True)
        except subprocess.CalledProcessError as error:
            (root / "failure.log").write_text(error.stdout + "\n" + error.stderr)
            raise
        finally:
            server.terminate()
            server.wait(timeout=10)


if __name__ == "__main__":
    main()
