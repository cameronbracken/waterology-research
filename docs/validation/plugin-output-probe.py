"""Probe output growth and two simple read alternatives; not a plugin benchmark.

Run from the checkout: pixi run python docs/validation/plugin-output-probe.py
Project/session lookup is mocked. The actual session log reader and service
serialization run on deterministic synthetic files in a temporary directory.
"""

import hashlib
import json
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from waterology import services
from waterology.core import sessions


def probe(line_count: int) -> dict:
    lines = [
        json.dumps({"step": number, "level": "INFO", "message": "candidate evaluation progress"})
        for number in range(line_count)
    ]
    lines[line_count // 4] = json.dumps(
        {"level": "ERROR", "message": "EVIDENCE_A solver failed: negative storage"}
    )
    lines[line_count // 2] = json.dumps(
        {"level": "WARNING", "message": "EVIDENCE_B coverage incomplete: missing replication"}
    )
    lines[-1] = json.dumps({"level": "INFO", "message": "controller finished"})
    events = "\n".join(lines) + "\n"
    with TemporaryDirectory(prefix="waterology-output-probe-") as temporary:
        root = Path(temporary)
        (root / "events.jsonl").write_text(events, encoding="utf-8")
        (root / "stderr.log").write_text("", encoding="utf-8")
        session = SimpleNamespace(
            id="session-0000000000000000",
            attempts=(
                SimpleNamespace(number=1, events_path="events.jsonl", stderr_path="stderr.log"),
            ),
        )
        with (
            patch.object(sessions, "discover_project", return_value=SimpleNamespace(root=root)),
            patch.object(sessions, "load_session", return_value=session),
            patch.object(
                sessions, "resolve_session_file", side_effect=lambda _, __, name: root / name
            ),
        ):
            payload = services.session_logs(root, session.id)
        full = json.dumps(payload).encode()
        assert payload[0]["events"] == events
        tail = events.encode()[-8192:]
        result = subprocess.run(
            ["rg", "-n", "-C", "2", "ERROR|WARNING", str(root / "events.jsonl")],
            check=True,
            capture_output=True,
        )
        filtered = result.stdout
        needles = (b"EVIDENCE_A", b"EVIDENCE_B")
        return {
            "lines": line_count,
            "source_sha256": hashlib.sha256(events.encode()).hexdigest(),
            "source_bytes": len(events.encode()),
            "service_json_bytes": len(full),
            "service_evidence_found": sum(needle in full for needle in needles),
            "tail_bytes": len(tail),
            "tail_evidence_found": sum(needle in tail for needle in needles),
            "rg_context_bytes": len(filtered),
            "rg_evidence_found": sum(needle in filtered for needle in needles),
            "expected_evidence_count": len(needles),
        }


if __name__ == "__main__":
    result = {
        "scope": "synthetic log-reader probe; not an upstream plugin or agent-quality benchmark",
        "rows": [probe(size) for size in (200, 2000, 20000)],
    }
    output = Path(__file__).with_name("plugin-output-probe.json")
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(output.read_text(encoding="utf-8"))
