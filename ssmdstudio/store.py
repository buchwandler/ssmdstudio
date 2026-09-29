from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any
from collections.abc import Iterable

import yaml


_ID_RE = re.compile(r"[^a-z0-9]+")


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = _ID_RE.sub("-", value).strip("-")
    if not value:
        raise ValueError("identifier must contain at least one letter or number")
    return value


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(
        "w",
        encoding="utf-8",
        newline="\n",
        delete=False,
        dir=path.parent,
        prefix=f".{path.name}.",
    ) as handle:
        handle.write(text)
        temp_name = handle.name
    os.replace(temp_name, path)


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected a YAML mapping in {path}")
    return data


def dump_yaml(data: dict[str, Any]) -> str:
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=100)


def write_yaml(path: Path, data: dict[str, Any]) -> None:
    atomic_write_text(path, dump_yaml(data))


def hash_files(paths: Iterable[Path], *, root: Path) -> tuple[str, list[dict[str, str]]]:
    digest = hashlib.sha256()
    records: list[dict[str, str]] = []

    for path in sorted({p.resolve() for p in paths}):
        if not path.is_file():
            continue
        rel = path.relative_to(root.resolve()).as_posix()
        content = path.read_bytes()
        file_hash = hashlib.sha256(content).hexdigest()
        records.append({"path": rel, "sha256": file_hash})
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(content)
        digest.update(b"\0")

    return digest.hexdigest(), records


def write_json(path: Path, data: dict[str, Any]) -> None:
    atomic_write_text(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")
