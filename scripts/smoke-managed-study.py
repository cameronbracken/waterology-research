"""Run two synthetic evaluations on an isolated local TORC server, then export a report."""

import argparse
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

from waterology.core.config import ProjectConfig, project_config_toml
from waterology.core.experiments import create_experiment
from waterology.core.project import initialize_project
from waterology.core.reports import export_report
from waterology.core.studies import StudyContract, StudyRecord, create_study, enqueue_candidate


def git(root, *args):
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


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
    machine = root / "machine.toml"
    machine.write_text(f'[profiles.local]\nmode="local"\napi_url="{api}"\n')
    os.environ["WATEROLOGY_CONFIG"] = str(machine)
    for name in ("TORC_PASSWORD", "TORC_AUTH_FILE", "TORC_COOKIE_HEADER", "DATABASE_URL"):
        os.environ.pop(name, None)
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
        )
        try:
            for _ in range(50):
                try:
                    with urlopen(api + "/workflows", timeout=1):
                        break
                except OSError:
                    time.sleep(0.2)
            project = root / "project"
            project.mkdir()
            git(project, "init", "-q")
            git(project, "config", "user.name", "Test")
            git(project, "config", "user.email", "test@example.org")
            initialize_project(project)
            config = ProjectConfig(
                name="synthetic-reservoir",
                command=("python3", "model.py"),
                default_compute_profile="local",
                artifact_roots=("results",),
                outputs=("results/metrics.json",),
                metrics=({"name": "error", "path": "results/metrics.json", "field": "error"},),
            )
            (project / "waterology.toml").write_text(project_config_toml(config))
            (project / ".gitignore").write_text(".waterology/\nresults/\n")
            (project / "model.py").write_text('print("fixture seed")\n')
            git(project, "add", ".")
            git(project, "-c", "commit.gpgsign=false", "commit", "-qm", "fixture base")
            experiments = []
            for label, value in [("baseline", 2.0), ("candidate", 0.5)]:
                experiment = create_experiment(
                    project, hypothesis="Synthetic target fixture", experiment_id=f"exp-{label}"
                )
                worktree = project / experiment.worktree
                (worktree / "model.py").write_text(
                    "import json\nfrom pathlib import Path\n"
                    'Path("results").mkdir(exist_ok=True)\n'
                    f'Path("results/metrics.json").write_text(json.dumps({{"error": {value}}}))\n'
                    f'print("synthetic fixture error: {value}", flush=True)\n'
                )
                git(worktree, "add", "model.py")
                git(worktree, "-c", "commit.gpgsign=false", "commit", "-qm", label)
                experiments.append(experiment.id)
            contract = StudyContract(
                mode="engineering",
                objective="Verify synthetic acceptance and resume",
                baseline_experiment=experiments[0],
                allowed_paths=("model.py",),
                evaluation={
                    "kind": "synthetic fixture",
                    "data": "no research data",
                    "seeds": "deterministic",
                },
                acceptance=({"name": "error", "unit": "m", "threshold": 1.0},),
                max_iterations=2,
                max_seconds=180,
            )
            record = create_study(
                project, contract, authorized_by="user authorized local implementation validation"
            )
            enqueue_candidate(project, record.id, experiments[1])
            previous = None
            while True:
                # Each tick reloads state. No process-local job identity is retained.
                completed = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "waterology",
                        "--output-format",
                        "json",
                        "study",
                        "advance",
                        record.id,
                        "--path",
                        str(project),
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                record = StudyRecord.model_validate_json(completed.stdout)
                status = (record.state, len(record.attempts), record.reason)
                if status != previous:
                    print(status, flush=True)
                    previous = status
                if record.state in {"complete", "blocked", "exhausted", "stopped"}:
                    break
                time.sleep(1)
            (root / "study-result.json").write_text(record.model_dump_json(indent=2))
            if record.state != "complete":
                raise RuntimeError(record.reason or record.state)
            run_ids = [a.run_id for a in record.attempts]
            export_report(project, run_ids, baseline=run_ids[0], destination="reports/smoke")
            print(
                json.dumps(
                    {
                        "status": "pass",
                        "study_id": record.id,
                        "runs": run_ids,
                        "report": "project/reports/smoke",
                    }
                ),
                flush=True,
            )
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()


if __name__ == "__main__":
    main()
