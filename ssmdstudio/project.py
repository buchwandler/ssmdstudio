from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .models import (
    Character,
    Feedback,
    ProjectConfig,
    Scene,
    SSMDRole,
    validate_ssmd_role,
)
from .prompts import STAGE_SPECS, STAGES, PromptPack, render_template
from .store import (
    atomic_write_text,
    dump_yaml,
    hash_files,
    load_yaml,
    slugify,
    write_json,
    write_yaml,
)


def _remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.exists():
        shutil.rmtree(path)


class Studio:
    """A filesystem-backed SSMD authoring project."""

    def __init__(self, root: Path, config: ProjectConfig):
        self.root = root.resolve()
        self.config = config

    @classmethod
    def init(
        cls,
        path: str | Path,
        *,
        title: str,
        brief: str,
        project_id: str | None = None,
        recipe: str = "funny-story",
        language: str = "en",
        audience: str = "general",
        tone: str = "warm comic",
        duration_minutes: float | None = None,
        constraints: list[str] | None = None,
        allow_nested: bool = False,
        prompt_pack: str | Path | None = None,
    ) -> Studio:
        root = Path(path).resolve()
        if (root / "project.yaml").exists():
            raise FileExistsError(f"project already exists at {root}")
        if not allow_nested:
            for ancestor in root.parents:
                if (ancestor / "project.yaml").is_file():
                    raise ValueError(
                        f"refusing to create an SSMD Studio project inside existing project {ancestor}\n"
                        "hint: create a sibling project, use a workspace, or pass --allow-nested"
                    )
        if recipe != "funny-story":
            raise ValueError("the MVP currently supports only recipe='funny-story'")

        if prompt_pack is not None:
            PromptPack.open(prompt_pack)
        root.mkdir(parents=True, exist_ok=True)
        for name in ("characters", "scenes", "feedback", "drafts", "output", "runs"):
            (root / name).mkdir(exist_ok=True)

        config = ProjectConfig(
            id=slugify(project_id or root.name),
            title=title,
            brief=brief,
            recipe=recipe,
            language=language,
            audience=audience,
            tone=tone,
            duration_minutes=duration_minutes,
            constraints=constraints or [],
        )
        write_yaml(root / "project.yaml", config.to_dict())
        studio = cls(root, config)
        if prompt_pack is not None:
            studio.install_prompt_pack(prompt_pack)
        return studio

    @classmethod
    def open(cls, path: str | Path = ".") -> Studio:
        root = cls.find_root(Path(path))
        config = ProjectConfig.from_dict(load_yaml(root / "project.yaml"))
        return cls(root, config)

    @staticmethod
    def find_root(path: Path) -> Path:
        current = path.resolve()
        if current.is_file():
            current = current.parent
        for candidate in (current, *current.parents):
            if (candidate / "project.yaml").is_file():
                return candidate
        raise FileNotFoundError(f"no ssmdstudio project found from {path}")

    def save_config(self) -> None:
        write_yaml(self.root / "project.yaml", self.config.to_dict())

    @property
    def prompt_pack_path(self) -> Path:
        return self.root / "prompts"

    def _require_prompt_pack(self) -> PromptPack:
        manifest = self.prompt_pack_path / "prompt-pack.yaml"
        if not manifest.is_file():
            raise FileNotFoundError(
                f"no workflow prompt pack is installed for project {self.config.id!r}\n"
                "hint: ssmdstudio prompt pack install PATH"
            )
        return PromptPack.open(self.prompt_pack_path)

    def install_prompt_pack(self, source: str | Path, *, replace: bool = False) -> Path:
        source_pack = PromptPack.open(source)
        target = self.prompt_pack_path
        target_exists = target.exists() or target.is_symlink()
        if target_exists and not replace:
            raise FileExistsError(
                f"project prompt pack already exists at {target}; pass replace=True to replace it"
            )

        for path in source_pack.root.rglob("*"):
            if path.is_symlink():
                raise ValueError(f"prompt pack cannot contain symlinks: {path}")

        staging = Path(tempfile.mkdtemp(prefix=".prompts-staging-", dir=self.root))
        backup = self.root / f".prompts-backup-{uuid4().hex}"
        try:
            shutil.copytree(source_pack.root, staging, dirs_exist_ok=True)
            PromptPack.open(staging)
            if not replace and (target.exists() or target.is_symlink()):
                raise FileExistsError(
                    f"project prompt pack already exists at {target}; pass replace=True to replace it"
                )
            if target.exists() or target.is_symlink():
                os.replace(target, backup)
            os.replace(staging, target)
            if backup.exists() or backup.is_symlink():
                _remove_path(backup)
            return target
        finally:
            if staging.exists():
                shutil.rmtree(staging)
            if backup.exists() or backup.is_symlink():
                if target.exists() or target.is_symlink():
                    _remove_path(backup)
                else:
                    os.replace(backup, target)

    def add_character(
        self,
        *,
        id: str,
        name: str,
        role: str,
        description: str,
        traits: list[str] | None = None,
        goals: list[str] | None = None,
        voice_notes: str = "",
        ssmd_role: SSMDRole | None = None,
        constraints: list[str] | None = None,
    ) -> Character:
        character = Character(
            id=slugify(id),
            name=name,
            role=role,
            description=description,
            traits=traits or [],
            goals=goals or [],
            voice_notes=voice_notes,
            ssmd_role=ssmd_role,
            constraints=constraints or [],
        )
        if ssmd_role is not None:
            validate_ssmd_role(ssmd_role)
            self._ensure_unique_ssmd_role(character.id, ssmd_role)
        write_yaml(self.root / "characters" / f"{character.id}.yaml", character.to_dict())
        return character

    def put_character(self, character: Character) -> None:
        if character.ssmd_role is not None:
            validate_ssmd_role(character.ssmd_role)
            self._ensure_unique_ssmd_role(character.id, character.ssmd_role)
        write_yaml(self.root / "characters" / f"{character.id}.yaml", character.to_dict())

    def _ensure_unique_ssmd_role(self, character_id: str, role: str) -> None:
        for existing in self.characters():
            if existing.id != character_id and existing.ssmd_role == role:
                raise ValueError(
                    f"SSMD role {role!r} is already assigned to character {existing.id!r}"
                )

    def characters(self) -> list[Character]:
        return [
            Character.from_dict(load_yaml(path))
            for path in sorted((self.root / "characters").glob("*.yaml"))
        ]

    @staticmethod
    def _canonical_id(value: object, entity: str) -> str:
        if not isinstance(value, str) or not value or slugify(value) != value:
            raise ValueError(f"{entity} ID must be lowercase kebab-case")
        return value

    @staticmethod
    def _require_fields(item: dict[str, Any], fields: tuple[str, ...], entity: str) -> None:
        missing = [
            name for name in fields if not isinstance(item.get(name), str) or not item[name].strip()
        ]
        if missing:
            raise ValueError(f"{entity} requires non-empty fields: {', '.join(missing)}")

    @staticmethod
    def _validate_list_fields(item: dict[str, Any], fields: tuple[str, ...], entity: str) -> None:
        for name in fields:
            values = item.get(name, [])
            if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
                raise ValueError(f"{entity} field {name!r} must be a list of strings")

    @staticmethod
    def _validate_character_set(characters: list[Character]) -> None:
        ids: set[str] = set()
        roles: set[str] = set()
        for character in characters:
            if character.id in ids:
                raise ValueError(f"duplicate character ID {character.id!r}")
            ids.add(character.id)
            if character.ssmd_role is not None:
                validate_ssmd_role(character.ssmd_role)
                if character.ssmd_role in roles:
                    raise ValueError(f"duplicate SSMD role {character.ssmd_role!r}")
                roles.add(character.ssmd_role)

    def _replace_entity_set(self, directory: str, items: list[Character] | list[Scene]) -> None:
        target = self.root / directory
        staging = Path(tempfile.mkdtemp(prefix=f".{directory}-", dir=self.root))
        backup = self.root / f".{directory}-backup-{uuid4().hex}"
        try:
            for item in items:
                write_yaml(staging / f"{item.id}.yaml", item.to_dict())
            if target.exists():
                os.replace(target, backup)
            try:
                os.replace(staging, target)
            except Exception:
                if backup.exists():
                    os.replace(backup, target)
                raise
            if backup.exists():
                shutil.rmtree(backup)
        finally:
            if staging.exists():
                shutil.rmtree(staging)

    def import_characters(self, source: str | Path, *, merge: bool = False) -> list[Character]:
        import yaml

        try:
            data = yaml.safe_load(Path(source).read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise ValueError(f"invalid character YAML: {exc}") from exc
        if not isinstance(data, dict) or not isinstance(data.get("characters"), list):
            raise ValueError(  # noqa: TRY004
                "character import expects a YAML mapping with a 'characters' list"
            )
        imported: list[Character] = []
        for item in data["characters"]:
            if not isinstance(item, dict):
                raise ValueError(  # noqa: TRY004
                    "every imported character must be a YAML mapping"
                )
            self._require_fields(item, ("id", "name", "role", "description"), "character")
            self._validate_list_fields(item, ("traits", "goals", "constraints"), "character")
            character_id = self._canonical_id(item["id"], "character")
            character = Character.from_dict(item)
            character.id = character_id
            imported.append(character)
        self._validate_character_set(imported)

        if merge:
            combined = {item.id: item for item in self.characters()}
            combined.update({item.id: item for item in imported})
            result = list(combined.values())
            self._validate_character_set(result)
        else:
            result = imported
        self._replace_entity_set("characters", result)
        return imported

    def add_scene(
        self,
        *,
        id: str,
        title: str,
        purpose: str,
        characters: list[str] | None = None,
        events: list[str] | None = None,
        comic_function: str = "",
        constraints: list[str] | None = None,
        locked: bool = False,
    ) -> Scene:
        scene = Scene(
            id=slugify(id),
            title=title,
            purpose=purpose,
            characters=[slugify(item) for item in (characters or [])],
            events=events or [],
            comic_function=comic_function,
            constraints=constraints or [],
            locked=locked,
        )
        known = {character.id for character in self.characters()}
        unknown = sorted(set(scene.characters) - known)
        if unknown:
            raise ValueError(f"scene references unknown character(s): {', '.join(unknown)}")
        write_yaml(self.root / "scenes" / f"{scene.id}.yaml", scene.to_dict())
        return scene

    def put_scene(self, scene: Scene) -> None:
        write_yaml(self.root / "scenes" / f"{scene.id}.yaml", scene.to_dict())

    def scenes(self) -> list[Scene]:
        return [
            Scene.from_dict(load_yaml(path))
            for path in sorted((self.root / "scenes").glob("*.yaml"))
        ]

    @staticmethod
    def _validate_scene_set(scenes: list[Scene], character_ids: set[str]) -> None:
        ids: set[str] = set()
        for scene in scenes:
            if scene.id in ids:
                raise ValueError(f"duplicate scene ID {scene.id!r}")
            ids.add(scene.id)
            unknown = sorted(set(scene.characters) - character_ids)
            if unknown:
                raise ValueError(
                    f"scene {scene.id!r} references unknown character(s): {', '.join(unknown)}"
                )

    def import_scenes(self, source: str | Path, *, merge: bool = False) -> list[Scene]:
        import yaml

        try:
            data = yaml.safe_load(Path(source).read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise ValueError(f"invalid scene YAML: {exc}") from exc
        if not isinstance(data, dict) or not isinstance(data.get("scenes"), list):
            raise ValueError(  # noqa: TRY004
                "scene import expects a YAML mapping with a 'scenes' list"
            )
        imported: list[Scene] = []
        for item in data["scenes"]:
            if not isinstance(item, dict):
                raise ValueError(  # noqa: TRY004
                    "every imported scene must be a YAML mapping"
                )
            self._require_fields(item, ("id", "title", "purpose"), "scene")
            self._validate_list_fields(item, ("characters", "events", "constraints"), "scene")
            scene_id = self._canonical_id(item["id"], "scene")
            scene = Scene.from_dict(item)
            scene.id = scene_id
            scene.characters = [
                self._canonical_id(value, "scene character reference") for value in scene.characters
            ]
            if "locked" in item and not isinstance(item["locked"], bool):
                raise ValueError("scene field 'locked' must be a boolean")
            imported.append(scene)

        character_ids = {item.id for item in self.characters()}
        if merge:
            combined = {item.id: item for item in self.scenes()}
            combined.update({item.id: item for item in imported})
            result = list(combined.values())
        else:
            result = imported
        self._validate_scene_set(result, character_ids)
        self._replace_entity_set("scenes", result)
        return imported

    def add_feedback(
        self,
        *,
        id: str,
        instructions: list[str],
        scope: list[str] | None = None,
        locked: list[str] | None = None,
    ) -> Feedback:
        feedback = Feedback(
            id=slugify(id),
            instructions=instructions,
            scope=scope or [],
            locked=locked or [],
        )
        write_yaml(self.root / "feedback" / f"{feedback.id}.yaml", feedback.to_dict())
        return feedback

    def feedback(self, *, open_only: bool = False) -> list[Feedback]:
        items = [
            Feedback.from_dict(load_yaml(path))
            for path in sorted((self.root / "feedback").glob("*.yaml"))
        ]
        if open_only:
            items = [item for item in items if item.status == "open"]
        return items

    def set_draft(self, source: str | Path) -> Path:
        source_path = Path(source)
        text = source_path.read_text(encoding="utf-8")
        target = self.root / "drafts" / "current.md"
        atomic_write_text(target, text)
        return target

    def draft_text(self) -> str:
        path = self.root / "drafts" / "current.md"
        return path.read_text(encoding="utf-8") if path.is_file() else ""

    def set_output(self, source: str | Path) -> Path:
        source_path = Path(source)
        text = source_path.read_text(encoding="utf-8")
        target = self.root / "output" / "current.ssmd.md"
        atomic_write_text(target, text)
        return target

    def output_text(self) -> str:
        path = self.root / "output" / "current.ssmd.md"
        return path.read_text(encoding="utf-8") if path.is_file() else ""

    def validate_output(self) -> dict[str, Any]:
        output = self.root / "output" / "current.ssmd.md"
        if not output.is_file():
            raise FileNotFoundError("no SSMD output to validate")
        output_hash = hashlib.sha256(output.read_bytes()).hexdigest()
        validator = shutil.which("ssmd")
        checked_at = datetime.now(timezone.utc).isoformat()
        if validator is None:
            result: dict[str, Any] = {
                "state": "unavailable",
                "path": "output/current.ssmd.md",
                "message": "ssmd runtime is not installed",
                "command": None,
                "returncode": None,
                "stdout": "",
                "stderr": "",
            }
        else:
            command = [
                validator,
                "--json",
                "lint",
                "output/current.ssmd.md",
                "--roundtrip",
                "--fail-on-warn",
            ]
            completed = subprocess.run(
                command,
                cwd=self.root,
                capture_output=True,
                text=True,
                check=False,
            )
            result = {
                "state": "passed" if completed.returncode == 0 else "failed",
                "path": "output/current.ssmd.md",
                "command": command,
                "returncode": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            }
        result["checked_at"] = checked_at
        result["output_sha256"] = output_hash
        write_json(self.root / "output" / "validation.json", result)
        return result

    def validation_status(self) -> str:
        record_path = self.root / "output" / "validation.json"
        if not record_path.is_file():
            return "not_run"
        output = self.root / "output" / "current.ssmd.md"
        if not output.is_file():
            return "stale"
        record = json.loads(record_path.read_text(encoding="utf-8"))
        output_hash = hashlib.sha256(output.read_bytes()).hexdigest()
        if record.get("output_sha256") != output_hash:
            return "stale"
        return str(record["state"])

    def _workflow_state(self) -> dict[str, bool]:
        characters = bool(self.characters())
        scenes = bool(self.scenes())
        draft = bool(self.draft_text())
        open_feedback = bool(self.feedback(open_only=True))
        output = (self.root / "output" / "current.ssmd.md").is_file()
        return {
            "characters": characters,
            "scenes": scenes,
            "draft": draft,
            "open_feedback": open_feedback,
            "approved_draft": draft and not open_feedback,
            "output": output,
        }

    def next_stage(self) -> str | None:
        state = self._workflow_state()
        if state["output"]:
            return None
        for stage in STAGES:
            spec = STAGE_SPECS[stage]
            if stage in {"revise", "ssmd"}:
                if all(state[name] for name in spec.prerequisites):
                    return stage
            elif not state[stage] and all(state[name] for name in spec.prerequisites):
                return stage
        return None

    def _apply_snapshot(self, stage: str) -> dict[str, bytes]:
        directories = {
            "characters": ("characters",),
            "scenes": ("scenes",),
            "draft": ("drafts",),
            "revise": ("drafts", "feedback"),
            "ssmd": ("output",),
        }[stage]
        snapshot: dict[str, bytes] = {}
        for directory in directories:
            for path in sorted((self.root / directory).glob("*")):
                if path.is_file():
                    snapshot[path.relative_to(self.root).as_posix()] = path.read_bytes()
        return snapshot

    def _latest_run_dir(self, stage: str) -> Path | None:
        for manifest in sorted((self.root / "runs").glob("*/manifest.json"), reverse=True):
            data = json.loads(manifest.read_text(encoding="utf-8"))
            if data.get("stage") == stage:
                return manifest.parent
        return None

    def apply(self, source: str | Path, *, stage: str | None = None) -> dict[str, Any]:
        response_path = Path(source)
        if not response_path.is_file():
            raise FileNotFoundError(response_path)
        if stage is None:
            stage = self.next_stage()
            if stage is None:
                raise ValueError("project is complete; no stage is waiting for an artifact")
        elif stage not in STAGE_SPECS:
            raise ValueError(f"unknown stage {stage!r}; choose from {', '.join(STAGES)}")

        expected_artifact = STAGE_SPECS[stage].expected_artifact(self.config.id)
        if response_path.name != expected_artifact:
            raise ValueError(
                f"stage {stage!r} expects artifact {expected_artifact!r}, got {response_path.name!r}"
            )
        before = self._apply_snapshot(stage)
        action = STAGE_SPECS[stage].apply_action
        if action == "characters":
            self.import_characters(response_path)
        elif action == "scenes":
            self.import_scenes(response_path)
        elif action == "draft":
            self.set_draft(response_path)
            if stage == "revise":
                for feedback_path in sorted((self.root / "feedback").glob("*.yaml")):
                    feedback = Feedback.from_dict(load_yaml(feedback_path))
                    if feedback.status == "open":
                        feedback.status = "applied"
                        write_yaml(feedback_path, feedback.to_dict())
        elif action == "output":
            self.set_output(response_path)
        else:
            raise ValueError(f"stage {stage!r} has unsupported apply action {action!r}")

        after = self._apply_snapshot(stage)
        changed_files = sorted(
            path for path in before.keys() | after.keys() if before.get(path) != after.get(path)
        )
        run_dir = self._latest_run_dir(stage)
        response_file = None
        if run_dir is not None:
            suffix = {"yaml": ".yaml", "markdown": ".md", "ssmd": ".ssmd.md"}[
                STAGE_SPECS[stage].artifact_kind
            ]
            response_file = run_dir / f"response{suffix}"
            if response_path.resolve() != response_file.resolve():
                shutil.copyfile(response_path, response_file)
            manifest_path = run_dir / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["response_file"] = response_file.name
            manifest["applied_at"] = datetime.now(timezone.utc).isoformat()
            manifest["changed_files"] = changed_files
            write_json(manifest_path, manifest)

        return {
            "stage": stage,
            "expected_artifact": expected_artifact,
            "changed_files": changed_files,
            "run": run_dir.name if run_dir is not None else None,
            "response_file": response_file.name if response_file is not None else None,
        }

    def _context_project(self, *, compact: bool = False) -> str:
        data = self.config.to_prompt_dict()
        if compact:
            data = {
                key: data[key]
                for key in ("id", "title", "language", "recipe", "constraints")
                if key in data
            }
        return dump_yaml(data).strip()

    def _context_characters(self) -> str:
        characters = self.characters()
        if not characters:
            return "(none yet)"
        return "\n---\n".join(dump_yaml(item.to_prompt_dict()).strip() for item in characters)

    def _context_speakers(self) -> str:
        speakers = [
            {
                "id": item.id,
                "name": item.name,
                "ssmd_role": item.ssmd_role,
                "voice_notes": item.voice_notes,
            }
            for item in self.characters()
            if item.ssmd_role is not None
        ]
        if not speakers:
            return "(no symbolic speakers assigned)"
        return dump_yaml({"speakers": speakers}).strip()

    def _context_scenes(self) -> str:
        scenes = self.scenes()
        if not scenes:
            return "(none yet)"
        return "\n---\n".join(dump_yaml(item.to_prompt_dict()).strip() for item in scenes)

    def _context_feedback(self) -> str:
        feedback = self.feedback(open_only=True)
        if not feedback:
            return "(no open feedback)"
        records = []
        for item in feedback:
            record = item.to_dict()
            record.pop("schema")
            records.append(dump_yaml(record).strip())
        return "\n---\n".join(records)

    def build_prompt(self, stage: str) -> str:
        if stage not in STAGES:
            raise ValueError(f"unknown stage {stage!r}; choose from {', '.join(STAGES)}")
        state = self._workflow_state()
        missing = [name for name in STAGE_SPECS[stage].prerequisites if not state[name]]
        if missing:
            prerequisite = missing[0]
            if prerequisite == "scenes":
                raise ValueError(f"stage {stage!r} requires at least one scene")
            if prerequisite == "characters":
                raise ValueError(f"stage {stage!r} requires at least one character")
            if prerequisite == "draft":
                raise ValueError(f"{stage} generation requires drafts/current.md")
            if prerequisite == "open_feedback":
                raise ValueError("revision requires open feedback")
            if prerequisite == "approved_draft":
                if not state["draft"]:
                    raise ValueError("SSMD generation requires drafts/current.md")
                raise ValueError("SSMD generation requires a draft with no open feedback")
            raise ValueError(f"stage {stage!r} is missing prerequisite {prerequisite!r}")

        pack = self._require_prompt_pack()
        template = pack.template_text(stage)
        values = {
            "PROJECT": self._context_project(compact=stage == "ssmd"),
            "CHARACTERS": self._context_characters(),
            "SPEAKERS": self._context_speakers(),
            "SCENES": self._context_scenes(),
            "FEEDBACK": self._context_feedback(),
            "DRAFT": self.draft_text() or "(no draft yet)",
            "ARTIFACT_NAME": STAGE_SPECS[stage].expected_artifact(self.config.id),
        }
        return render_template(template, values).rstrip() + "\n"

    def _stage_input_paths(self, stage: str) -> list[Path]:
        manifest = self.prompt_pack_path / "prompt-pack.yaml"
        if manifest.is_file():
            pack = self._require_prompt_pack()
            prompt_paths = [manifest, pack.template_path(stage)]
        else:
            prompt_paths = [manifest, self.prompt_pack_path / f"{stage}.md"]
        paths = [self.root / "project.yaml", *prompt_paths]
        paths.extend(sorted((self.root / "characters").glob("*.yaml")))
        if stage in {"draft", "revise"}:
            paths.extend(sorted((self.root / "scenes").glob("*.yaml")))
        if stage == "revise":
            paths.extend(sorted((self.root / "feedback").glob("*.yaml")))
        if stage in {"revise", "ssmd"}:
            draft = self.root / "drafts" / "current.md"
            if draft.is_file():
                paths.append(draft)
        return paths

    def save_prompt_run(self, stage: str, prompt: str | None = None) -> Path:
        if stage not in STAGE_SPECS:
            raise ValueError(f"unknown prompt stage {stage!r}; choose from {', '.join(STAGES)}")
        pack = self._require_prompt_pack()
        template_path = pack.template_path(stage)
        template_sha256 = hashlib.sha256(template_path.read_bytes()).hexdigest()
        template_name = template_path.relative_to(pack.root).as_posix()
        prompt = prompt if prompt is not None else self.build_prompt(stage)
        fingerprint, inputs = hash_files(self._stage_input_paths(stage), root=self.root)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        run_dir = self.root / "runs" / f"{stamp}-{stage}"
        run_dir.mkdir(parents=True, exist_ok=False)
        atomic_write_text(run_dir / "prompt.md", prompt)
        write_json(
            run_dir / "manifest.json",
            {
                "schema": "ssmdstudio.run.v1",
                "stage": stage,
                "expected_artifact": STAGE_SPECS[stage].expected_artifact(self.config.id),
                "prompt_pack": {
                    "id": pack.id,
                    "schema": pack.schema,
                    "template": template_name,
                    "template_sha256": template_sha256,
                },
                "created_at": datetime.now(timezone.utc).isoformat(),
                "input_fingerprint": fingerprint,
                "inputs": inputs,
                "response_file": None,
                "applied_at": None,
                "changed_files": [],
            },
        )
        return run_dir

    def run_statuses(self) -> list[dict[str, Any]]:
        import json

        statuses: list[dict[str, Any]] = []
        for manifest_path in sorted((self.root / "runs").glob("*/manifest.json")):
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            stage = str(data["stage"])
            current_fingerprint, _ = hash_files(self._stage_input_paths(stage), root=self.root)
            statuses.append(
                {
                    "run": manifest_path.parent.name,
                    "stage": stage,
                    "state": (
                        "current"
                        if current_fingerprint == data.get("input_fingerprint")
                        else "stale"
                    ),
                }
            )
        return statuses

    def status(self) -> dict[str, Any]:
        manifest = self.prompt_pack_path / "prompt-pack.yaml"
        prompt_pack = PromptPack.open(self.prompt_pack_path) if manifest.is_file() else None
        return {
            "root": str(self.root),
            "project": self.config.id,
            "recipe": self.config.recipe,
            "characters": len(self.characters()),
            "scenes": len(self.scenes()),
            "open_feedback": len(self.feedback(open_only=True)),
            "draft": (self.root / "drafts" / "current.md").is_file(),
            "output": (self.root / "output" / "current.ssmd.md").is_file(),
            "validation": self.validation_status(),
            "next_stage": self.next_stage(),
            "runs": self.run_statuses(),
            "prompt_pack": {
                "installed": prompt_pack is not None,
                "id": prompt_pack.id if prompt_pack is not None else None,
                "path": "prompts",
            },
        }
