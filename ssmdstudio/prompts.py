from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from types import MappingProxyType
from typing import Literal

import yaml


@dataclass(frozen=True, slots=True)
class StageSpec:
    name: str
    artifact_name: str
    artifact_kind: Literal["yaml", "markdown", "ssmd"]
    prerequisites: tuple[str, ...]
    apply_action: str

    def expected_artifact(self, project_id: str) -> str:
        return self.artifact_name.format(project_id=project_id)


STAGE_SPECS = {
    "characters": StageSpec("characters", "characters.yaml", "yaml", (), "characters"),
    "scenes": StageSpec("scenes", "scenes.yaml", "yaml", ("characters",), "scenes"),
    "draft": StageSpec("draft", "draft.md", "markdown", ("scenes",), "draft"),
    "revise": StageSpec("revise", "draft.md", "markdown", ("draft", "open_feedback"), "draft"),
    "ssmd": StageSpec("ssmd", "{project_id}.ssmd.md", "ssmd", ("approved_draft",), "output"),
}
STAGES = tuple(STAGE_SPECS)

_PROMPT_PACK_SCHEMA = "ssmdstudio.prompt-pack.v1"
_PROMPT_PACK_MANIFEST = "prompt-pack.yaml"
_PLACEHOLDER_RE = re.compile(r"\{\{([A-Z][A-Z0-9_]*)\}\}")


class _UniqueKeySafeLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects ambiguous duplicate mapping keys."""

    def construct_mapping(self, node: yaml.MappingNode, deep: bool = False) -> dict[object, object]:
        self.flatten_mapping(node)
        mapping: dict[object, object] = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            try:
                duplicate = key in mapping
            except TypeError as exc:
                raise yaml.constructor.ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    "found an unhashable mapping key",
                    key_node.start_mark,
                ) from exc
            if duplicate:
                raise yaml.constructor.ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    f"found duplicate key {key!r}",
                    key_node.start_mark,
                )
            mapping[key] = self.construct_object(value_node, deep=deep)
        return mapping


@dataclass(frozen=True, slots=True)
class PromptPack:
    root: Path
    id: str
    schema: str
    stages: Mapping[str, Path]

    @classmethod
    def open(cls, path: str | Path) -> PromptPack:
        requested_root = Path(path).expanduser()
        try:
            root = requested_root.resolve(strict=True)
        except FileNotFoundError as exc:
            raise FileNotFoundError(f"prompt pack directory not found: {requested_root}") from exc
        if not root.is_dir():
            raise ValueError(f"prompt pack path is not a directory: {root}")

        manifest_path = root / _PROMPT_PACK_MANIFEST
        try:
            manifest_resolved = manifest_path.resolve(strict=True)
        except FileNotFoundError as exc:
            raise FileNotFoundError(f"prompt pack manifest not found: {manifest_path}") from exc
        if not _is_within(root, manifest_resolved):
            raise ValueError("prompt pack manifest escapes prompt pack directory")
        if not manifest_resolved.is_file():
            raise ValueError(f"prompt pack manifest is not a regular file: {manifest_path}")

        try:
            manifest_text = manifest_resolved.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(f"prompt pack manifest is not valid UTF-8: {manifest_path}") from exc
        try:
            raw = yaml.load(manifest_text, Loader=_UniqueKeySafeLoader)
        except yaml.YAMLError as exc:
            raise ValueError(f"invalid prompt pack manifest {manifest_path}: {exc}") from exc
        if not isinstance(raw, dict):
            raise TypeError("prompt-pack.yaml must contain a mapping")

        unknown_fields = set(raw) - {"schema", "id", "kind", "stages"}
        if unknown_fields:
            names = ", ".join(sorted(repr(key) for key in unknown_fields))
            raise ValueError(f"prompt pack has unknown manifest field(s): {names}")
        if raw.get("schema") != _PROMPT_PACK_SCHEMA:
            raise ValueError(f"unsupported prompt pack schema; expected {_PROMPT_PACK_SCHEMA!r}")
        pack_id = raw.get("id")
        if not isinstance(pack_id, str) or not pack_id.strip() or pack_id != pack_id.strip():
            raise ValueError("prompt pack id must be a non-empty stable identifier")
        if any(char.isspace() for char in pack_id):
            raise ValueError("prompt pack id must not contain whitespace")
        if raw.get("kind") != "workflow":
            raise ValueError("prompt pack kind must be 'workflow'")

        stage_mappings = raw.get("stages")
        if not isinstance(stage_mappings, dict):
            raise TypeError("prompt pack stages must be a mapping")
        stage_names = set(stage_mappings)
        missing = set(STAGES) - stage_names
        unknown = stage_names - set(STAGES)
        if missing or unknown:
            details: list[str] = []
            if missing:
                details.append("missing stage(s): " + ", ".join(sorted(missing)))
            if unknown:
                details.append(
                    "unknown stage(s): " + ", ".join(sorted(repr(name) for name in unknown))
                )
            raise ValueError(
                "prompt pack must map exactly the supported stages (" + "; ".join(details) + ")"
            )

        stage_files: dict[str, Path] = {}
        for stage in STAGES:
            relative = stage_mappings[stage]
            if (
                not isinstance(relative, str)
                or not relative.strip()
                or relative != relative.strip()
            ):
                raise ValueError(f"prompt stage {stage!r} must map to a relative file path")
            posix_path = PurePosixPath(relative)
            windows_path = PureWindowsPath(relative)
            if (
                posix_path.is_absolute()
                or windows_path.is_absolute()
                or windows_path.drive
                or "\\" in relative
                or ".." in posix_path.parts
                or ".." in windows_path.parts
                or "\x00" in relative
            ):
                raise ValueError(f"prompt template path must be a safe relative path: {relative!r}")

            candidate = root.joinpath(*posix_path.parts)
            try:
                template_path = candidate.resolve(strict=True)
            except FileNotFoundError as exc:
                raise FileNotFoundError(
                    f"prompt template not found for stage {stage!r}: {relative}"
                ) from exc
            if not _is_within(root, template_path):
                raise ValueError(f"prompt template escapes prompt pack directory: {relative}")
            if not template_path.is_file():
                raise ValueError(
                    f"prompt template is not a regular file for stage {stage!r}: {relative}"
                )
            try:
                template_path.read_text(encoding="utf-8")
            except UnicodeDecodeError as exc:
                raise ValueError(
                    f"prompt template is not valid UTF-8 for stage {stage!r}: {relative}"
                ) from exc
            stage_files[stage] = template_path

        return cls(
            root=root,
            id=pack_id,
            schema=_PROMPT_PACK_SCHEMA,
            stages=MappingProxyType(stage_files),
        )

    def template_path(self, stage: str) -> Path:
        try:
            return self.stages[stage]
        except KeyError as exc:
            raise ValueError(
                f"unknown prompt stage {stage!r}; choose from {', '.join(STAGES)}"
            ) from exc

    def template_text(self, stage: str) -> str:
        path = self.template_path(stage)
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(
                f"prompt template is not valid UTF-8 for stage {stage!r}: {path}"
            ) from exc


def _is_within(root: Path, path: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def render_template(template: str, values: Mapping[str, str]) -> str:
    """Substitute standard placeholders in plain text without evaluating a template language."""
    if not isinstance(template, str):
        raise TypeError("prompt template must be text")
    if any(not isinstance(key, str) or not isinstance(value, str) for key, value in values.items()):
        raise TypeError("prompt template values must map strings to strings")

    rendered = _PLACEHOLDER_RE.sub(
        lambda match: values.get(match.group(1), match.group(0)), template
    )
    unresolved = sorted(set(_PLACEHOLDER_RE.findall(rendered)))
    if unresolved:
        placeholders = ", ".join("{{" + name + "}}" for name in unresolved)
        raise ValueError(f"prompt template contains unresolved placeholder(s): {placeholders}")
    return rendered
