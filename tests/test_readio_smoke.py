from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
READIO_ROOT = ROOT.parent / "readio"
FIXTURE = ROOT / "tests" / "fixtures" / "authoring" / "readio-preflight.ssmd.md"


@pytest.mark.skipif(
    os.environ.get("SSMDSTUDIO_READIO_SMOKE") != "1",
    reason="set SSMDSTUDIO_READIO_SMOKE=1 to run the optional sibling-checkout smoke",
)
def test_studio_authored_ssmd_passes_current_readio_render_preflight(tmp_path: Path) -> None:
    if not (READIO_ROOT / "readio" / "__main__.py").is_file():
        pytest.skip("sibling Readio source checkout is unavailable")
    if shutil.which("ssmd") is None:
        pytest.skip("optional ssmd CLI is unavailable")

    lint = subprocess.run(
        [
            sys.executable,
            "-m",
            "ssmdstudio",
            "ssmd",
            "lint",
            str(FIXTURE),
            "--roundtrip",
            "--json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert lint.returncode == 0, lint.stdout + lint.stderr
    assert json.loads(lint.stdout)["state"] == "passed"

    bound = tmp_path / "readio-preflight.bound.ssmd.md"
    binding = subprocess.run(
        [
            sys.executable,
            "-m",
            "ssmdstudio",
            "ssmd",
            "bind",
            str(FIXTURE),
            "--provider",
            "kokoro",
            "--voice-bind",
            "host=af_heart",
            "--output",
            str(bound),
            "--json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert binding.returncode == 0, binding.stdout + binding.stderr
    assert bound.is_file()

    preflight = subprocess.run(
        [
            sys.executable,
            "-m",
            "readio",
            "render",
            "--file",
            str(bound),
            "--input-format",
            "ssmd",
            "--engine",
            "kokoro",
            "--dry-run",
            "--json",
            "--no-progress",
        ],
        cwd=READIO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert preflight.returncode == 0, preflight.stdout + preflight.stderr
    assert json.loads(preflight.stdout)["schema"] == "readio.plan.v2"
