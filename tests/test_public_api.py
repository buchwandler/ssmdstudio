from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_package_root_exports_authoring_api_without_importing_ssmd() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            """
import sys
sys.modules["ssmd"] = None
from ssmdstudio import (
    BindingResult,
    SSMDUnavailableError,
    TemplateLibrary,
    ValidationDiagnostic,
    ValidationResult,
    check_ssmd,
    materialize_voice_bindings,
)
assert all((BindingResult, SSMDUnavailableError, TemplateLibrary, ValidationDiagnostic,
            ValidationResult, check_ssmd, materialize_voice_bindings))
""",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
