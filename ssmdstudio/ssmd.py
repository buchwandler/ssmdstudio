"""Provider-neutral SSMD authoring operations backed by the public SSMD API."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from types import MappingProxyType
from typing import Any, Literal
from uuid import uuid4

_PROVIDER_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]*\Z")
_ROLE_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]*\Z")
_SSMD_SUFFIXES = (".ssmd.md", ".ssmd")


class SSMDUnavailableError(RuntimeError):
    """Raised when an operation needs an unavailable or unsupported SSMD runtime."""


@dataclass(frozen=True, slots=True)
class BindingResult:
    """Outcome of materializing explicit provider-specific voice bindings."""

    source: Path
    output: Path
    provider: str
    bindings: Mapping[str, str]
    in_place: bool
    source_sha256: str
    output_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "ssmdstudio.binding.v1",
            "source": str(self.source),
            "output": str(self.output),
            "provider": self.provider,
            "bindings": dict(self.bindings),
            "in_place": self.in_place,
            "source_sha256": self.source_sha256,
            "output_sha256": self.output_sha256,
        }


@dataclass(frozen=True, slots=True)
class ValidationDiagnostic:
    severity: str
    code: str
    message: str
    line: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
            "line": self.line,
        }


@dataclass(frozen=True, slots=True)
class ValidationResult:
    source: Path
    state: Literal["passed", "failed", "unavailable"]
    dialect: str
    roundtrip: bool
    tool_version: str | None
    diagnostics: tuple[ValidationDiagnostic, ...]
    returncode: int | None
    source_sha256: str
    command: tuple[str, ...] = ()
    stdout: str = ""
    stderr: str = ""
    message: str | None = None

    @property
    def ok(self) -> bool:
        return self.state == "passed"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "ssmdstudio.validation.v1",
            "source": str(self.source),
            "state": self.state,
            "ok": self.ok,
            "dialect": self.dialect,
            "roundtrip": self.roundtrip,
            "tool": {"name": "ssmd", "version": self.tool_version},
            "diagnostics": [item.to_dict() for item in self.diagnostics],
            "returncode": self.returncode,
            "source_sha256": self.source_sha256,
            "command": list(self.command) if self.command else None,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "raw_output": {"stdout": self.stdout, "stderr": self.stderr},
            "message": self.message,
        }


def _ssmd_api() -> Any:
    try:
        import ssmd  # type: ignore[import-not-found]
    except ImportError as error:
        raise SSMDUnavailableError(
            "SSMD authoring requires the optional dependency ssmd>=0.9.3,<0.10"
        ) from error

    version = str(getattr(ssmd, "__version__", ""))
    match = re.match(r"^0\.9\.(\d+)", version)
    if match is None or int(match.group(1)) < 3:
        raise SSMDUnavailableError(
            f"SSMD authoring requires ssmd>=0.9.3,<0.10; found {version or 'unknown version'}"
        )
    required = (
        "parse_structure",
        "parse_front_matter",
        "merge_generated_header",
        "serialize_front_matter",
    )
    missing = [name for name in required if not callable(getattr(ssmd, name, None))]
    if missing:
        raise SSMDUnavailableError(
            "installed ssmd does not expose required public authoring APIs: " + ", ".join(missing)
        )
    return ssmd


def _read_utf8(path: Path) -> tuple[bytes, str]:
    content = path.read_bytes()
    try:
        return content, content.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(f"SSMD source must be UTF-8: {path}") from error


def _source_suffix(path: Path) -> str:
    lowered = path.name.casefold()
    for suffix in _SSMD_SUFFIXES:
        if lowered.endswith(suffix):
            return suffix
    raise ValueError("SSMD source must use the .ssmd or .ssmd.md suffix")


def _binding_output_path(source: Path) -> Path:
    suffix = _source_suffix(source)
    stem = source.name[: -len(suffix)]
    return source.with_name(f"{stem}.bound.ssmd.md")


def _normalize_bindings(bindings: Mapping[str, str]) -> dict[str, str]:
    if not isinstance(bindings, Mapping):
        raise TypeError("voice bindings must be a role-to-voice mapping")
    normalized: dict[str, str] = {}
    for role, voice in bindings.items():
        if not isinstance(role, str) or not _ROLE_RE.fullmatch(role):
            raise ValueError(f"invalid or empty SSMD role name: {role!r}")
        if not isinstance(voice, str) or not voice or voice != voice.strip():
            raise ValueError(f"voice ID for role {role!r} must be a non-empty string")
        if role in normalized and normalized[role] != voice:
            raise ValueError(f"conflicting voice bindings were supplied for role {role!r}")
        normalized[role] = voice
    if not normalized:
        raise ValueError("at least one voice binding is required")
    return normalized


def _parse_document(text: str, *, source: Path, api: Any) -> tuple[dict[str, Any], str, str]:
    front_matter = api.parse_front_matter(text)
    header = dict(front_matter.data) if front_matter.present else {}
    version = header.get("ssmd_version")
    dialect = "0.9" if version is None else str(version)
    if dialect not in {"0.8", "0.9"}:
        raise ValueError(
            f"unsupported ssmd_version {version!r} in {source}; expected '0.8' or '0.9'"
        )

    try:
        parsed = api.parse_structure(
            text,
            normalize=False,
            parse_yaml_header=True,
            resolve_defaults=False,
            dialect=dialect,
        )
    except Exception as error:
        raise ValueError(f"invalid SSMD source {source}: {error}") from error
    errors = [item for item in parsed.diagnostics if getattr(item, "severity", None) == "error"]
    if errors:
        first = errors[0]
        code = getattr(first, "code", "ssmd.invalid")
        message = getattr(first, "message", str(first))
        raise ValueError(f"invalid SSMD source {source}: {message} ({code})")

    if front_matter.present and front_matter.source_end is not None:
        body = text[front_matter.source_end :]
    else:
        body = text
    return header, body, dialect


def _atomic_write(
    target: Path,
    content: bytes,
    *,
    overwrite: bool,
    expected_source: Path | None = None,
    expected_sha256: str | None = None,
    mode: int | None = None,
) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_symlink():
        raise ValueError(f"refusing to write through a symlink: {target}")
    if target.exists() and not target.is_file():
        raise ValueError(f"output is not a regular file: {target}")
    if target.exists() and not overwrite:
        raise FileExistsError(f"output already exists: {target}; pass force=True to replace it")

    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        if mode is not None:
            temporary.chmod(mode)
        if target.is_symlink():
            raise ValueError(f"refusing to replace a symlink: {target}")
        if target.exists() and not overwrite:
            raise FileExistsError(f"output already exists: {target}; pass force=True to replace it")
        if expected_source is not None and expected_sha256 is not None:
            observed = hashlib.sha256(expected_source.read_bytes()).hexdigest()
            if observed != expected_sha256:
                raise ValueError(
                    f"SSMD source changed while bindings were being materialized: {expected_source}"
                )
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


_VALIDATION_TIMEOUT_SECONDS = 30


def _tool_version() -> str | None:
    try:
        return version("ssmd")
    except PackageNotFoundError:
        return None


def _stream_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value


def _cli_diagnostics(
    payload: dict[str, Any],
) -> tuple[tuple[ValidationDiagnostic, ...], str | None]:
    result = payload.get("result")
    if (
        not isinstance(result, dict)
        or not isinstance(result.get("files"), list)
        or not result["files"]
    ):
        return (), "ssmd CLI JSON result must contain a non-empty files list"

    diagnostics: list[ValidationDiagnostic] = []
    for file_result in result["files"]:
        if not isinstance(file_result, dict) or not isinstance(file_result.get("issues"), list):
            return (), "ssmd CLI JSON file result must contain an issues list"
        if not isinstance(file_result.get("ok"), bool):
            return (), "ssmd CLI JSON file result must contain a boolean ok field"
        file_diagnostic_start = len(diagnostics)
        for issue in file_result["issues"]:
            if not isinstance(issue, dict):
                return (), "ssmd CLI JSON diagnostics must be objects"
            severity = issue.get("severity")
            code = issue.get("code")
            message = issue.get("message")
            line = issue.get("line")
            if (
                not isinstance(severity, str)
                or not severity
                or not isinstance(code, str)
                or not code
                or not isinstance(message, str)
                or not message
            ):
                return (), "ssmd CLI JSON diagnostics require severity, code, and message strings"
            if line is not None and (not isinstance(line, int) or isinstance(line, bool)):
                return (), "ssmd CLI JSON diagnostic line must be an integer or null"
            diagnostics.append(
                ValidationDiagnostic(
                    severity="warning" if severity == "warn" else severity,
                    code=code,
                    message=message,
                    line=line,
                )
            )
        if not file_result["ok"] and not any(
            item.severity == "error" for item in diagnostics[file_diagnostic_start:]
        ):
            diagnostics.append(
                ValidationDiagnostic(
                    severity="error",
                    code="ssmd.cli.file_failed",
                    message="ssmd CLI reported a failed file check without error diagnostics",
                )
            )
    return tuple(diagnostics), None


def check_ssmd(
    source: Path,
    *,
    roundtrip: bool = True,
    fail_on_warn: bool = False,
    config: Path | None = None,
    dialect: str = "0.9",
) -> ValidationResult:
    """Run SSMD's structural lint/roundtrip checker for one file.

    The executable is invoked with an argv array, without a shell, and is
    bounded to 30 seconds. Missing tools are reported as ``unavailable``;
    malformed output and validation failures are reported as ``failed``.
    """
    if dialect not in {"auto", "0.8", "0.9"}:
        raise ValueError("dialect must be 'auto', '0.8', or '0.9'")
    source_path = Path(source).expanduser()
    _source_suffix(source_path)
    if not source_path.is_file():
        raise FileNotFoundError(source_path)
    source_path = source_path.resolve()
    source_sha256 = hashlib.sha256(source_path.read_bytes()).hexdigest()

    config_path: Path | None = None
    if config is not None:
        config_path = Path(config).expanduser()
        if not config_path.is_file():
            raise FileNotFoundError(config_path)
        config_path = config_path.resolve()

    executable = shutil.which("ssmd")
    if executable is None:
        return ValidationResult(
            source=source_path,
            state="unavailable",
            dialect=dialect,
            roundtrip=roundtrip,
            tool_version=None,
            diagnostics=(),
            returncode=None,
            source_sha256=source_sha256,
            message="ssmd executable is not installed or not on PATH",
        )

    command = [executable, "--json"]
    if config_path is not None:
        command.extend(("--config", str(config_path)))
    command.extend(("lint", str(source_path), "--dialect", dialect))
    if roundtrip:
        command.append("--roundtrip")
    if fail_on_warn:
        command.append("--fail-on-warn")

    try:
        completed = subprocess.run(
            command,
            shell=False,
            capture_output=True,
            text=True,
            timeout=_VALIDATION_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        stdout = _stream_text(error.stdout)
        stderr = _stream_text(error.stderr)
        diagnostic = ValidationDiagnostic(
            severity="error",
            code="ssmd.cli.timeout",
            message=f"ssmd lint exceeded {_VALIDATION_TIMEOUT_SECONDS} seconds",
        )
        return ValidationResult(
            source=source_path,
            state="failed",
            dialect=dialect,
            roundtrip=roundtrip,
            tool_version=_tool_version(),
            diagnostics=(diagnostic,),
            returncode=None,
            source_sha256=source_sha256,
            command=tuple(command),
            stdout=stdout,
            stderr=stderr,
            message=diagnostic.message,
        )
    except FileNotFoundError:
        return ValidationResult(
            source=source_path,
            state="unavailable",
            dialect=dialect,
            roundtrip=roundtrip,
            tool_version=None,
            diagnostics=(),
            returncode=None,
            source_sha256=source_sha256,
            command=tuple(command),
            message="ssmd executable disappeared before it could be started",
        )
    except OSError as error:
        diagnostic = ValidationDiagnostic(
            severity="error",
            code="ssmd.cli.spawn_failed",
            message=f"could not start ssmd lint: {error}",
        )
        return ValidationResult(
            source=source_path,
            state="failed",
            dialect=dialect,
            roundtrip=roundtrip,
            tool_version=_tool_version(),
            diagnostics=(diagnostic,),
            returncode=None,
            source_sha256=source_sha256,
            command=tuple(command),
            message=diagnostic.message,
        )

    stdout = _stream_text(completed.stdout)
    stderr = _stream_text(completed.stderr)
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        diagnostic = ValidationDiagnostic(
            severity="error",
            code="ssmd.cli.invalid_json",
            message="ssmd CLI returned malformed JSON",
        )
        return ValidationResult(
            source=source_path,
            state="failed",
            dialect=dialect,
            roundtrip=roundtrip,
            tool_version=_tool_version(),
            diagnostics=(diagnostic,),
            returncode=completed.returncode,
            source_sha256=source_sha256,
            command=tuple(command),
            stdout=stdout,
            stderr=stderr,
            message=diagnostic.message,
        )

    if not isinstance(payload, dict) or not isinstance(payload.get("ok"), bool):
        shape_message = "ssmd CLI JSON must be an object with a boolean ok field"
        diagnostics: tuple[ValidationDiagnostic, ...] = (
            ValidationDiagnostic("error", "ssmd.cli.invalid_json_shape", shape_message),
        )
        return ValidationResult(
            source=source_path,
            state="failed",
            dialect=dialect,
            roundtrip=roundtrip,
            tool_version=_tool_version(),
            diagnostics=diagnostics,
            returncode=completed.returncode,
            source_sha256=source_sha256,
            command=tuple(command),
            stdout=stdout,
            stderr=stderr,
            message=shape_message,
        )

    diagnostics, shape_error = _cli_diagnostics(payload)
    if shape_error is not None:
        diagnostics = (ValidationDiagnostic("error", "ssmd.cli.invalid_json_shape", shape_error),)
    failed = (
        completed.returncode != 0
        or payload["ok"] is not True
        or any(item.severity == "error" for item in diagnostics)
        or (fail_on_warn and any(item.severity == "warning" for item in diagnostics))
        or shape_error is not None
    )
    if failed and not diagnostics:
        diagnostics = (
            ValidationDiagnostic(
                severity="error",
                code="ssmd.cli.nonzero_exit"
                if completed.returncode
                else "ssmd.cli.reported_failure",
                message=(
                    f"ssmd lint exited with code {completed.returncode}"
                    if completed.returncode
                    else "ssmd CLI reported a failed lint result"
                ),
            ),
        )
    if hashlib.sha256(source_path.read_bytes()).hexdigest() != source_sha256:
        diagnostics = (
            *diagnostics,
            ValidationDiagnostic(
                severity="error",
                code="ssmd.source_changed",
                message="SSMD source changed while validation was running",
            ),
        )
        failed = True
    return ValidationResult(
        source=source_path,
        state="failed" if failed else "passed",
        dialect=dialect,
        roundtrip=roundtrip,
        tool_version=_tool_version(),
        diagnostics=diagnostics,
        returncode=completed.returncode,
        source_sha256=source_sha256,
        command=tuple(command),
        stdout=stdout,
        stderr=stderr,
        message=(stderr.strip() or None) if failed else None,
    )


def materialize_voice_bindings(
    source: Path,
    bindings: Mapping[str, str],
    *,
    provider: str,
    output: Path | None = None,
    in_place: bool = False,
    force: bool = False,
) -> BindingResult:
    """Materialize explicit role bindings without consulting any renderer config.

    Existing ``.ssmd`` and ``.ssmd.md`` inputs are accepted. New output defaults
    to ``<logical-stem>.bound.ssmd.md``. Front matter is parsed and serialized
    through SSMD's public, version-bounded API; its formatting is normalized to
    LF while the document body, including its original CRLF/LF policy, is kept
    byte-for-byte after UTF-8 decoding.
    """
    source_path = Path(source).expanduser()
    _source_suffix(source_path)
    if source_path.is_symlink():
        raise ValueError(f"SSMD source must not be a symlink: {source_path}")
    if not source_path.is_file():
        raise FileNotFoundError(source_path)
    source_path = source_path.resolve()

    if not isinstance(provider, str) or not _PROVIDER_RE.fullmatch(provider):
        raise ValueError(
            "provider must be a safe namespace identifier (letters, digits, '_' or '-')"
        )
    normalized = _normalize_bindings(bindings)
    if in_place and output is not None:
        raise ValueError("--in-place cannot be combined with --output")

    if in_place:
        target = source_path
    else:
        requested_target = (
            Path(output).expanduser() if output is not None else _binding_output_path(source_path)
        )
        if requested_target.is_symlink():
            raise ValueError(f"refusing to write through a symlink: {requested_target}")
        target = requested_target.resolve()
    if not in_place and target == source_path:
        raise ValueError("refusing to overwrite the SSMD source; use in_place=True explicitly")
    if target.exists() and not in_place and not force:
        raise FileExistsError(f"output already exists: {target}; pass force=True to replace it")
    if target.is_symlink():
        raise ValueError(f"refusing to write through a symlink: {target}")

    api = _ssmd_api()
    source_bytes, source_text = _read_utf8(source_path)
    source_sha256 = hashlib.sha256(source_bytes).hexdigest()
    header, body, _dialect = _parse_document(source_text, source=source_path, api=api)

    raw_voice_bindings = header.get("voice_bindings", {})
    if raw_voice_bindings is None:
        raw_voice_bindings = {}
        header["voice_bindings"] = {}
    if not isinstance(raw_voice_bindings, Mapping):
        raise TypeError("SSMD voice_bindings front matter must be a mapping")
    existing_provider_bindings = raw_voice_bindings.get(provider, {})
    if not isinstance(existing_provider_bindings, Mapping):
        raise TypeError(f"SSMD voice_bindings.{provider} must be a mapping")

    generated: dict[str, Any] = {"voice_bindings": {provider: dict(normalized)}}
    if "ssmd_version" not in header:
        generated["ssmd_version"] = "0.9"
    merged = api.merge_generated_header(header, generated)

    all_bindings = dict(merged.get("voice_bindings", {}))
    provider_bindings = dict(all_bindings.get(provider, {}))
    provider_bindings.update(normalized)
    all_bindings[provider] = provider_bindings
    merged["voice_bindings"] = all_bindings

    marker = f"\x00SSMDSTUDIO_BODY_{uuid4().hex}\x00"
    while marker in source_text:
        marker = f"\x00SSMDSTUDIO_BODY_{uuid4().hex}\x00"
    serialized = api.serialize_front_matter(merged, marker + body)
    marker_at = serialized.find(marker)
    if marker_at < 0:
        raise ValueError("SSMD serializer did not preserve the body boundary")
    serialized = serialized[:marker_at] + serialized[marker_at + len(marker) :]

    _parse_document(serialized, source=source_path, api=api)
    output_bytes = serialized.encode("utf-8")
    mode = stat.S_IMODE(source_path.stat().st_mode) if in_place else None
    _atomic_write(
        target,
        output_bytes,
        overwrite=in_place or force,
        expected_source=source_path if in_place else None,
        expected_sha256=source_sha256 if in_place else None,
        mode=mode,
    )
    return BindingResult(
        source=source_path,
        output=target,
        provider=provider,
        bindings=MappingProxyType(dict(normalized)),
        in_place=in_place,
        source_sha256=source_sha256,
        output_sha256=hashlib.sha256(output_bytes).hexdigest(),
    )


__all__ = [
    "BindingResult",
    "SSMDUnavailableError",
    "ValidationDiagnostic",
    "ValidationResult",
    "check_ssmd",
    "materialize_voice_bindings",
]
