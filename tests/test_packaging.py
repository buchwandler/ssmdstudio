from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path

from ssmdstudio.cli import main

ROOT = Path(__file__).resolve().parents[1]
PACKAGED_SKILL = "ssmdstudio/resources/skills/ssmdstudio/SKILL.md"


def test_skill_commands_show_path_and_install(tmp_path: Path, capsys) -> None:
    source_skill = ROOT / "skill" / "ssmdstudio" / "SKILL.md"
    resource_skill = ROOT / PACKAGED_SKILL
    assert source_skill.read_bytes() == resource_skill.read_bytes()

    main(["skill", "show"])
    assert capsys.readouterr().out == resource_skill.read_text(encoding="utf-8")

    main(["skill", "path"])
    skill_path = Path(capsys.readouterr().out.strip())
    assert skill_path == resource_skill

    target = tmp_path / "harness-skills" / "ssmdstudio"
    main(["skill", "install", str(target)])
    installed = target / "SKILL.md"
    assert Path(capsys.readouterr().out.strip()) == installed
    assert installed.read_bytes() == resource_skill.read_bytes()


def test_wheel_contains_bundled_skill(tmp_path: Path) -> None:
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
        assert PACKAGED_SKILL in wheel.namelist()
        content = wheel.read(PACKAGED_SKILL)
    assert content == (ROOT / "skill" / "ssmdstudio" / "SKILL.md").read_bytes()
