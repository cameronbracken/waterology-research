import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    ("scanner", "violation"),
    [
        ("deterministic-seed.py", "import random\nvalue = random" + ".random()\n"),
        ("no-absolute-paths.py", "path = " + repr("C:" + "\\generated") + "\n"),
    ],
)
def test_scanners_ignore_pixi_environment_but_check_project_files(
    tmp_path: Path,
    scanner: str,
    violation: str,
) -> None:
    generated = tmp_path / ".pixi" / "envs" / "default" / "generated.py"
    generated.parent.mkdir(parents=True)
    generated.write_text(violation, encoding="utf-8")
    project = tmp_path / "project.py"
    project.write_text(violation, encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(ROOT / "constraints" / scanner), str(tmp_path)],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 1
    assert str(project) in result.stdout
    assert str(generated) not in result.stdout
