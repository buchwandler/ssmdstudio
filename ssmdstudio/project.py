from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from collections.abc import Iterable

from .models import Character, Feedback, ProjectConfig, Scene, SSMDRole
from .prompts import STAGES, render_template
from .store import (
    atomic_write_text,
    dump_yaml,
    hash_files,
    load_yaml,
    slugify,
    write_json,
    write_yaml,
)


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
    ) -> Studio:
        root = Path(path).resolve()
        if (root / "project.yaml").exists():
            raise FileExistsError(f"project already exists at {root}")
        if recipe != "funny-story":
            raise ValueError("the MVP currently supports only recipe='funny-story'")

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
        return cls(root, config)

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
            self._ensure_unique_ssmd_role(character.id, ssmd_role)
        write_yaml(self.root / "characters" / f"{character.id}.yaml", character.to_dict())
        return character

    def put_character(self, character: Character) -> None:
        if character.ssmd_role is not None:
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

    def import_characters(self, source: str | Path) -> list[Character]:
        import yaml

        data = yaml.safe_load(Path(source).read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not isinstance(data.get("characters"), list):
            raise ValueError("character import expects a YAML mapping with a 'characters' list")
        imported: list[Character] = []
        for item in data["characters"]:
            if not isinstance(item, dict):
                raise ValueError("every imported character must be a YAML mapping")
            character = Character.from_dict(item)
            character.id = slugify(character.id)
            self.put_character(character)
            imported.append(character)
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

    def import_scenes(self, source: str | Path) -> list[Scene]:
        import yaml

        data = yaml.safe_load(Path(source).read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not isinstance(data.get("scenes"), list):
            raise ValueError("scene import expects a YAML mapping with a 'scenes' list")
        imported: list[Scene] = []
        for item in data["scenes"]:
            if not isinstance(item, dict):
                raise ValueError("every imported scene must be a YAML mapping")
            scene = Scene.from_dict(item)
            scene.id = slugify(scene.id)
            scene.characters = [slugify(value) for value in scene.characters]
            known = {character.id for character in self.characters()}
            unknown = sorted(set(scene.characters) - known)
            if unknown:
                raise ValueError(
                    f"scene {scene.id!r} references unknown character(s): {', '.join(unknown)}"
                )
            self.put_scene(scene)
            imported.append(scene)
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

    def _context_project(self) -> str:
        return dump_yaml(self.config.to_dict()).strip()

    def _context_characters(self) -> str:
        characters = self.characters()
        if not characters:
            return "(none yet)"
        return "\n---\n".join(dump_yaml(item.to_dict()).strip() for item in characters)

    def _context_scenes(self) -> str:
        scenes = self.scenes()
        if not scenes:
            return "(none yet)"
        return "\n---\n".join(dump_yaml(item.to_dict()).strip() for item in scenes)

    def _context_feedback(self) -> str:
        feedback = self.feedback(open_only=True)
        if not feedback:
            return "(no open feedback)"
        return "\n---\n".join(dump_yaml(item.to_dict()).strip() for item in feedback)

    def build_prompt(self, stage: str) -> str:
        if stage not in STAGES:
            raise ValueError(f"unknown stage {stage!r}; choose from {', '.join(STAGES)}")
        if stage in {"draft", "revise", "ssmd"} and not self.scenes():
            raise ValueError(f"stage {stage!r} requires at least one scene")
        if stage == "revise" and not self.draft_text():
            raise ValueError("revision requires drafts/current.md")
        if stage == "ssmd" and not self.draft_text():
            raise ValueError("SSMD generation requires drafts/current.md")

        return (
            render_template(
                stage,
                {
                    "PROJECT": self._context_project(),
                    "CHARACTERS": self._context_characters(),
                    "SCENES": self._context_scenes(),
                    "FEEDBACK": self._context_feedback(),
                    "DRAFT": self.draft_text() or "(no draft yet)",
                },
            ).rstrip()
            + "\n"
        )

    def _stage_input_paths(self, stage: str) -> list[Path]:
        paths = [self.root / "project.yaml"]
        # Keep this list aligned with the contexts inserted by build_prompt().
        paths.extend(sorted((self.root / "characters").glob("*.yaml")))
        if stage in {"scenes", "draft", "revise", "ssmd"}:
            paths.extend(sorted((self.root / "scenes").glob("*.yaml")))
        if stage in {"revise", "ssmd"}:
            draft = self.root / "drafts" / "current.md"
            if draft.is_file():
                paths.append(draft)
        if stage == "revise":
            paths.extend(sorted((self.root / "feedback").glob("*.yaml")))
        return paths

    def save_prompt_run(self, stage: str, prompt: str | None = None) -> Path:
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
                "created_at": datetime.now(timezone.utc).isoformat(),
                "input_fingerprint": fingerprint,
                "inputs": inputs,
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
        return {
            "root": str(self.root),
            "project": self.config.id,
            "recipe": self.config.recipe,
            "characters": len(self.characters()),
            "scenes": len(self.scenes()),
            "open_feedback": len(self.feedback(open_only=True)),
            "draft": (self.root / "drafts" / "current.md").is_file(),
            "output": (self.root / "output" / "current.ssmd.md").is_file(),
            "runs": self.run_statuses(),
        }
