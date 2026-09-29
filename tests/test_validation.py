from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from ssmdstudio import Studio
from ssmdstudio.cli import main


def make_studio(tmp_path: Path) -> Studio:
    studio = Studio.init(tmp_path / "story", title="Story", brief="A short story.")
    output = tmp_path / "story.ssmd.md"
    output.write_text('---\nssmd_version: "0.9"\n---\nNarration.\n', encoding="utf-8")
    studio.set_output(output)
    return studio


def test_output_validation_records_passed_and_stales_after_output_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    studio = make_studio(tmp_path)
    monkeypatch.setattr("ssmdstudio.project.shutil.which", lambda _: "/fake/bin/ssmd")

    def run(command, *, cwd, capture_output, text, check):
        assert command[1:] == [
            "--json",
            "lint",
            "output/current.ssmd.md",
            "--roundtrip",
            "--fail-on-warn",
        ]
        assert cwd == studio.root
        assert capture_output and text and not check
        return subprocess.CompletedProcess(command, 0, '{"errors": []}\n', "")

    monkeypatch.setattr("ssmdstudio.project.subprocess.run", run)
    result = studio.validate_output()
    assert result["state"] == "passed"
    assert studio.validation_status() == "passed"
    record = json.loads((studio.root / "output" / "validation.json").read_text(encoding="utf-8"))
    assert record["state"] == "passed"
    assert record["returncode"] == 0

    replacement = tmp_path / "story.ssmd.md"
    replacement.write_text("---\nssmd_version: '0.9'\n---\nChanged.\n", encoding="utf-8")
    studio.set_output(replacement)
    assert studio.validation_status() == "stale"


def test_failed_output_validation_surfaces_diagnostics_and_exit_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    studio = make_studio(tmp_path)
    monkeypatch.setattr("ssmdstudio.project.shutil.which", lambda _: "/fake/bin/ssmd")
    diagnostic = '{"errors": [{"code": "roundtrip.semantic_loss"}]}\n'
    monkeypatch.setattr(
        "ssmdstudio.project.subprocess.run",
        lambda command, **kwargs: subprocess.CompletedProcess(
            command, 1, diagnostic, "lint failed\n"
        ),
    )

    with pytest.raises(SystemExit) as error:
        main(["output", "validate", "--project", str(studio.root)])
    assert error.value.code == 1
    output = capsys.readouterr()
    assert "validation: failed" in output.out
    assert "roundtrip.semantic_loss" in output.out
    assert "lint failed" in output.err
    assert "syntax lint: passed" not in output.out
    assert studio.validation_status() == "failed"


def test_unavailable_output_validation_is_explicit_not_validated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    studio = make_studio(tmp_path)
    monkeypatch.setattr("ssmdstudio.project.shutil.which", lambda _: None)

    result = studio.validate_output()
    assert result["state"] == "unavailable"
    assert result["command"] is None
    assert studio.validation_status() == "unavailable"

    main(["output", "validate", "--project", str(studio.root)])
    output = capsys.readouterr().out
    assert "validation: unavailable" in output
    assert "ssmd runtime is not installed" in output
    assert "passed" not in output
