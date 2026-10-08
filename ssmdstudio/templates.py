"""User-scoped, safe management for editable SSMD starter documents."""

from __future__ import annotations

import os
import re
import sys
import tempfile
from importlib import resources
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .ssmd import ValidationResult

_RESOURCE_PACKAGE = "ssmdstudio.resources.templates"
_SUFFIXES = (".ssmd.md", ".ssmd")
_NAME_RE = re.compile(r"[a-z0-9](?:[a-z0-9_-]*[a-z0-9])?\Z")


def _user_config_directory() -> Path:
    """Return the platform's conventional per-user configuration directory."""
    if sys.platform == "win32":
        base = os.environ.get("APPDATA")
        return (Path(base) if base else Path.home() / "AppData" / "Roaming") / "ssmdstudio"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "ssmdstudio"
    base = os.environ.get("XDG_CONFIG_HOME")
    return (Path(base) if base else Path.home() / ".config") / "ssmdstudio"


def _parse_name(name: str) -> tuple[str, str | None]:
    if not isinstance(name, str) or not name.strip():
        raise ValueError("template name must not be empty")
    if name != name.strip() or "/" in name or "\\" in name or Path(name).is_absolute():
        raise ValueError(f"unsafe template name: {name!r}")
    lowered = name.casefold()
    suffix = next((item for item in _SUFFIXES if lowered.endswith(item)), None)
    logical = name[: -len(suffix)] if suffix else name
    if suffix is None and "." in logical:
        raise ValueError("template names may only use the .ssmd or .ssmd.md extension")
    if not _NAME_RE.fullmatch(logical):
        raise ValueError(f"unsafe template name: {name!r}")
    return logical, suffix


def _logical_name(filename: str) -> str | None:
    lowered = filename.casefold()
    suffix = next((item for item in _SUFFIXES if lowered.endswith(item)), None)
    if suffix is None:
        return None
    logical, _ = _parse_name(filename)
    return logical


def _builtin_templates() -> dict[str, str]:
    package = resources.files(_RESOURCE_PACKAGE)
    templates: dict[str, str] = {}
    for entry in package.iterdir():
        if not entry.name.endswith(".ssmd"):
            continue
        logical, _suffix = _parse_name(entry.name)
        templates[logical] = entry.read_text(encoding="utf-8")
    return dict(sorted(templates.items()))


def _atomic_write_text(path: Path, content: str, *, replace: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError(f"refusing to write through a template symlink: {path}")
    if path.exists() and not replace:
        raise FileExistsError(f"file already exists: {path}; pass force=True to replace it")
    if path.exists() and not path.is_file():
        raise ValueError(f"output is not a regular file: {path}")

    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        if path.is_symlink():
            raise ValueError(f"refusing to replace a template symlink: {path}")
        if path.exists() and not replace:
            raise FileExistsError(f"file already exists: {path}; pass force=True to replace it")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def create_empty_draft(output: Path, *, force: bool = False) -> Path:
    """Create an empty standalone draft without overwriting an existing file."""
    target = Path(output).expanduser()
    if not target.name or target.name in {".", ".."}:
        raise ValueError("draft output must name a file")
    if target.exists() and target.is_dir():
        raise ValueError(f"draft output must be a file, not a directory: {target}")
    _atomic_write_text(target, "", replace=force)
    return target


class TemplateLibrary:
    """Manage a user's editable templates independently of a Studio project.

    ``root`` injects the library directory for tests or explicit local setups.
    Logical names are lowercase ASCII kebab/underscore names; storage accepts
    ``.ssmd`` and ``.ssmd.md``. A logical name may have only one stored file,
    regardless of suffix. Existing source suffixes are retained by ``path`` and
    ``use``; new templates default to ``.ssmd`` and unsuffixed use targets to
    ``.ssmd.md``.
    """

    def __init__(self, root: Path | None = None) -> None:
        self._root = (
            Path(root).expanduser() if root is not None else _user_config_directory() / "templates"
        )
        self._root = self._root.resolve()

    def directory(self) -> Path:
        """Return the user-scoped library directory without creating it."""
        return self._root

    def _candidates(self, logical: str) -> tuple[Path, ...]:
        if not self._root.exists():
            return ()
        if not self._root.is_dir():
            raise ValueError(f"template library is not a directory: {self._root}")
        paths: list[Path] = []
        for suffix in _SUFFIXES:
            candidate = self._root / f"{logical}{suffix}"
            if candidate.is_symlink():
                raise ValueError(f"template path must not be a symlink: {candidate}")
            if candidate.exists():
                if not candidate.is_file():
                    raise ValueError(f"template path is not a regular file: {candidate}")
                if candidate.resolve().parent != self._root:
                    raise ValueError(f"template path escapes the library directory: {candidate}")
                paths.append(candidate)
        if len(paths) > 1:
            raise ValueError(
                f"template suffix collision for {logical!r}: only one of .ssmd or .ssmd.md may exist"
            )
        return tuple(paths)

    def list(self) -> tuple[str, ...]:
        """Return sorted logical names for templates in the user library."""
        if not self._root.exists():
            return ()
        if not self._root.is_dir():
            raise ValueError(f"template library is not a directory: {self._root}")
        names: set[str] = set()
        for entry in self._root.iterdir():
            logical = _logical_name(entry.name)
            if logical is None:
                continue
            if entry.is_symlink():
                raise ValueError(f"template path must not be a symlink: {entry}")
            if not entry.is_file():
                raise ValueError(f"template path is not a regular file: {entry}")
            if logical in names:
                raise ValueError(
                    f"template suffix collision for {logical!r}: only one of .ssmd or .ssmd.md may exist"
                )
            names.add(logical)
        return tuple(sorted(names))

    def path(self, name: str) -> Path:
        """Resolve a logical template name to its existing file path."""
        logical, requested_suffix = _parse_name(name)
        candidates = self._candidates(logical)
        if not candidates:
            raise FileNotFoundError(f"template not found: {logical}")
        path = candidates[0]
        if requested_suffix is not None and not path.name.endswith(requested_suffix):
            raise FileNotFoundError(f"template not found: {name}")
        return path

    def show(self, name: str) -> str:
        """Read a stored template as UTF-8 text."""
        return self.path(name).read_text(encoding="utf-8")

    def seed(self, *, overwrite: bool = False) -> tuple[Path, ...]:
        """Copy built-in templates into the user library without replacing edits."""
        paths: list[Path] = []
        for logical, content in _builtin_templates().items():
            existing = self._candidates(logical)
            if existing and not overwrite:
                paths.append(existing[0])
                continue
            target = self._root / f"{logical}.ssmd"
            if existing and existing[0] != target:
                raise ValueError(
                    f"template suffix collision for {logical!r}; remove the existing template first"
                )
            _atomic_write_text(target, content, replace=overwrite)
            paths.append(target)
        return tuple(paths)

    def add(self, name: str, *, source: Path, force: bool = False) -> Path:
        """Add a user template from a file, preserving its requested suffix."""
        logical, suffix = _parse_name(name)
        source_path = Path(source).expanduser()
        if not source_path.is_file():
            raise FileNotFoundError(source_path)
        content = source_path.read_text(encoding="utf-8")
        if not content.strip():
            raise ValueError("template source is empty")
        existing = self._candidates(logical)
        source_suffix = next(
            (item for item in _SUFFIXES if source_path.name.casefold().endswith(item)), ".ssmd"
        )
        target = self._root / f"{logical}{suffix or source_suffix}"
        if existing and existing[0] != target:
            raise ValueError(
                f"template suffix collision for {logical!r}; remove the existing template first"
            )
        _atomic_write_text(target, content, replace=force)
        return target

    def remove(self, name: str) -> None:
        """Remove a stored user template."""
        self.path(name).unlink()

    def reset(self, name: str | None = None, *, all: bool = False) -> tuple[Path, ...]:
        """Restore one or all built-ins without deleting custom templates."""
        if all and name is not None:
            raise ValueError("template reset accepts a name or all=True, not both")
        if all:
            names = tuple(_builtin_templates())
        elif name is not None:
            logical, _suffix = _parse_name(name)
            if logical not in _builtin_templates():
                raise ValueError(f"unknown built-in template: {logical}")
            names = (logical,)
        else:
            raise ValueError("template reset requires a name or all=True")

        builtins = _builtin_templates()
        paths: list[Path] = []
        for logical in names:
            existing = self._candidates(logical)
            target = self._root / f"{logical}.ssmd"
            if existing and existing[0] != target:
                raise ValueError(
                    f"template suffix collision for {logical!r}; remove the existing template first"
                )
            _atomic_write_text(target, builtins[logical], replace=True)
            paths.append(target)
        return tuple(paths)

    def use(self, name: str, *, output: Path, force: bool = False) -> Path:
        """Copy a template to an output path, defaulting suffixless names to .ssmd.md."""
        source = self.path(name)
        target = Path(output).expanduser()
        if not target.name or target.name in {".", ".."}:
            raise ValueError("template output must name a file")
        if target.exists() and target.is_dir():
            raise ValueError(f"template output must be a file, not a directory: {target}")
        if not target.suffix:
            target = target.with_name(f"{target.name}.ssmd.md")
        _atomic_write_text(target, source.read_text(encoding="utf-8"), replace=force)
        return target

    def validate(self, name: str, *, roundtrip: bool = True) -> ValidationResult:
        """Validate a stored template using the standalone SSMD authoring checker."""
        from .ssmd import check_ssmd

        return check_ssmd(self.path(name), roundtrip=roundtrip)


__all__ = ["TemplateLibrary"]
