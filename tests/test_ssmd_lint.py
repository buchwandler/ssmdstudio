from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from ssmdstudio.ssmd import check_ssmd


def _source(tmp_path: Path, name: str = "source.ssmd.md") -> Path:
    path = tmp_path / name
    path.write_text("---\nssmd_version: '0.9'\n---\nHello.\n", encoding="utf-8")
    return path


def _payload(*, ok: bool = True, issues: list[dict[str, object]] | None = None) -> str:
    return json.dumps(
        {
            "schema": "ssmd.cli.v1",
            "ok": ok,
            "command": "lint",
            "result": {
                "files": [{"path": "source.ssmd.md", "ok": ok, "issues": issues or []}],
                "summary": {"error_count": 0, "warning_count": len(issues or [])},
            },
        }
    )


def _fake_executable(monkeypatch) -> None:
    monkeypatch.setattr("ssmdstudio.ssmd.shutil.which", lambda name: "/fake/bin/ssmd")


def test_check_ssmd_passes_with_bounded_argv_and_typed_result(tmp_path: Path, monkeypatch) -> None:
    source = _source(tmp_path)
    config = tmp_path / "authoring.yaml"
    config.write_text("schema: ssmd.config.v1\n", encoding="utf-8")
    _fake_executable(monkeypatch)
    calls: list[tuple[list[str], dict[str, object]]] = []

    def run(command, **kwargs):
        calls.append((list(command), kwargs))
        return subprocess.CompletedProcess(command, 0, _payload(), "")

    monkeypatch.setattr("ssmdstudio.ssmd.subprocess.run", run)
    result = check_ssmd(source, roundtrip=True, fail_on_warn=True, config=config)

    command, kwargs = calls[0]
    assert command == [
        "/fake/bin/ssmd",
        "--json",
        "--config",
        str(config.resolve()),
        "lint",
        str(source.resolve()),
        "--dialect",
        "0.9",
        "--roundtrip",
        "--fail-on-warn",
    ]
    assert kwargs == {
        "shell": False,
        "capture_output": True,
        "text": True,
        "timeout": 30,
        "check": False,
    }
    assert result.state == "passed"
    assert result.ok is True
    assert result.source_sha256 == hashlib.sha256(source.read_bytes()).hexdigest()
    assert result.to_dict()["schema"] == "ssmdstudio.validation.v1"
    assert result.to_dict()["tool"]["name"] == "ssmd"


def test_check_ssmd_reports_warnings_and_fail_on_warn(tmp_path: Path, monkeypatch) -> None:
    source = _source(tmp_path)
    _fake_executable(monkeypatch)
    warning = {
        "severity": "warn",
        "code": "header.unknown_key",
        "message": "Unknown key",
        "line": 4,
    }
    payload = _payload(issues=[warning])
    monkeypatch.setattr(
        "ssmdstudio.ssmd.subprocess.run",
        lambda command, **kwargs: subprocess.CompletedProcess(command, 0, payload, ""),
    )

    allowed = check_ssmd(source, roundtrip=False)
    rejected = check_ssmd(source, roundtrip=False, fail_on_warn=True)

    assert allowed.state == "passed"
    assert allowed.diagnostics[0].severity == "warning"
    assert allowed.diagnostics[0].line == 4
    assert rejected.state == "failed"
    assert rejected.ok is False
    assert "--roundtrip" not in rejected.command
    assert "--fail-on-warn" in rejected.command


def test_check_ssmd_reports_structural_failures_and_nonzero_exit(
    tmp_path: Path, monkeypatch
) -> None:
    source = _source(tmp_path)
    _fake_executable(monkeypatch)
    issue = {"severity": "error", "code": "syntax.invalid", "message": "Bad syntax", "line": 2}
    payload = _payload(ok=False, issues=[issue])
    monkeypatch.setattr(
        "ssmdstudio.ssmd.subprocess.run",
        lambda command, **kwargs: subprocess.CompletedProcess(command, 1, payload, "lint failed"),
    )

    result = check_ssmd(source)

    assert result.state == "failed"
    assert result.returncode == 1
    assert result.diagnostics[0].code == "syntax.invalid"
    assert result.stderr == "lint failed"
    assert result.to_dict()["raw_output"]["stdout"] == payload


def test_check_ssmd_distinguishes_unavailable_executable_without_diagnostics(
    tmp_path: Path, monkeypatch
) -> None:
    source = _source(tmp_path)
    monkeypatch.setattr("ssmdstudio.ssmd.shutil.which", lambda _name: None)
    monkeypatch.setattr(
        "ssmdstudio.ssmd.subprocess.run",
        lambda *args, **kwargs: pytest.fail("must not spawn when ssmd is unavailable"),
    )

    result = check_ssmd(source)

    assert result.state == "unavailable"
    assert result.ok is False
    assert result.returncode is None
    assert result.diagnostics == ()
    assert result.message == "ssmd executable is not installed or not on PATH"


def test_check_ssmd_handles_malformed_json_and_json_shape(tmp_path: Path, monkeypatch) -> None:
    source = _source(tmp_path)
    _fake_executable(monkeypatch)
    responses = iter(("not-json", json.dumps({"ok": True})))
    monkeypatch.setattr(
        "ssmdstudio.ssmd.subprocess.run",
        lambda command, **kwargs: subprocess.CompletedProcess(command, 0, next(responses), ""),
    )

    malformed = check_ssmd(source)
    wrong_shape = check_ssmd(source)

    assert malformed.state == "failed"
    assert malformed.diagnostics[0].code == "ssmd.cli.invalid_json"
    assert malformed.stdout == "not-json"
    assert wrong_shape.diagnostics[0].code == "ssmd.cli.invalid_json_shape"


def test_check_ssmd_bounds_timeout_and_preserves_partial_output(
    tmp_path: Path, monkeypatch
) -> None:
    source = _source(tmp_path)
    _fake_executable(monkeypatch)
    captured: dict[str, object] = {}

    def timeout(command, **kwargs):
        captured.update(kwargs)
        raise subprocess.TimeoutExpired(
            command, kwargs["timeout"], output="partial", stderr="waiting"
        )

    monkeypatch.setattr("ssmdstudio.ssmd.subprocess.run", timeout)
    result = check_ssmd(source)

    assert captured["timeout"] == 30
    assert result.state == "failed"
    assert result.diagnostics[0].code == "ssmd.cli.timeout"
    assert result.stdout == "partial"
    assert result.stderr == "waiting"


def test_check_ssmd_validates_paths_and_dialect_before_spawning(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(
        "ssmdstudio.ssmd.subprocess.run",
        lambda *args, **kwargs: pytest.fail("invalid inputs must not spawn ssmd"),
    )
    with pytest.raises(ValueError, match="suffix"):
        check_ssmd(tmp_path / "not-ssmd.txt")
    with pytest.raises(FileNotFoundError):
        check_ssmd(tmp_path / "missing.ssmd")
    with pytest.raises(ValueError, match="dialect"):
        check_ssmd(_source(tmp_path), dialect="0.7")
    with pytest.raises(FileNotFoundError):
        check_ssmd(_source(tmp_path, "other.ssmd"), config=tmp_path / "missing.yaml")


def test_ssmd_lint_cli_emits_one_json_object_and_nonzero_on_failure(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    from ssmdstudio.cli import main

    source = _source(tmp_path)
    _fake_executable(monkeypatch)
    monkeypatch.setattr(
        "ssmdstudio.ssmd.subprocess.run",
        lambda command, **kwargs: subprocess.CompletedProcess(command, 0, _payload(), ""),
    )
    main(["ssmd", "lint", str(source), "--roundtrip", "--json"])
    output = capsys.readouterr()
    result = json.loads(output.out)
    assert result["schema"] == "ssmdstudio.validation.v1"
    assert result["ok"] is True
    assert output.err == ""

    failed_payload = _payload(
        ok=False,
        issues=[{"severity": "error", "code": "syntax.invalid", "message": "bad", "line": 1}],
    )
    monkeypatch.setattr(
        "ssmdstudio.ssmd.subprocess.run",
        lambda command, **kwargs: subprocess.CompletedProcess(command, 1, failed_payload, ""),
    )
    with pytest.raises(SystemExit) as error:
        main(["ssmd", "lint", str(source), "--json"])
    assert error.value.code == 1
    output = capsys.readouterr()
    failed = json.loads(output.out)
    assert failed["state"] == "failed"
    assert "syntax.invalid" in output.out
    assert output.err == ""
