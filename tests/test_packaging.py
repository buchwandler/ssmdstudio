from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from ssmdstudio.cli import main

ROOT = Path(__file__).resolve().parents[1]


def test_skill_commands_are_not_part_of_the_cli(capsys) -> None:
    with pytest.raises(SystemExit) as error:
        main(["skill", "show"])
    assert error.value.code == 2
    assert "invalid choice" in capsys.readouterr().err


def test_wheel_contains_typing_metadata_but_no_prompt_or_skill_prose(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(tmp_path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    wheels = list(tmp_path.glob("*.whl"))
    assert len(wheels) == 1
    with zipfile.ZipFile(wheels[0]) as wheel:
        members = set(wheel.namelist())

    package_members = {name for name in members if name.startswith("ssmdstudio/")}
    assert "ssmdstudio/py.typed" in package_members
    assert not any(name.endswith(".md") for name in package_members)
    assert not any("/resources/" in name for name in package_members)
    assert not any(name.endswith("SKILL.md") for name in members)
    assert not any(name.startswith("skill/") for name in members)
    assert not (ROOT / "ssmdstudio" / "resources").exists()
