import argparse
import time
from pathlib import Path

from waterology.agents.supervisor import run_supervised_attempt


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one supervised Waterology agent attempt.")
    parser.add_argument("project", type=Path)
    parser.add_argument("session_id")
    parser.add_argument("attempt", type=int)
    parser.add_argument("gate", type=Path)
    arguments = parser.parse_args()
    deadline = time.monotonic() + 10
    while not arguments.gate.is_file():
        if time.monotonic() >= deadline:
            raise SystemExit("Waterology agent launch gate timed out")
        time.sleep(0.05)
    raise SystemExit(
        run_supervised_attempt(arguments.project, arguments.session_id, arguments.attempt)
    )


if __name__ == "__main__":
    main()
