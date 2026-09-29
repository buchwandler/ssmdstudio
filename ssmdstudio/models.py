from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

SSMDRole = Literal["narrator", "host", "guest", "analyst"]


def _clean_strings(values: list[str] | None) -> list[str]:
    return [str(value).strip() for value in (values or []) if str(value).strip()]


@dataclass(slots=True)
class ProjectConfig:
    id: str
    title: str
    brief: str
    recipe: str = "funny-story"
    language: str = "en"
    audience: str = "general"
    tone: str = "warm comic"
    duration_minutes: float | None = None
    constraints: list[str] = field(default_factory=list)
    schema: str = "ssmdstudio.project.v1"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["constraints"] = _clean_strings(self.constraints)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProjectConfig:
        return cls(
            id=str(data["id"]),
            title=str(data["title"]),
            brief=str(data.get("brief", "")),
            recipe=str(data.get("recipe", "funny-story")),
            language=str(data.get("language", "en")),
            audience=str(data.get("audience", "general")),
            tone=str(data.get("tone", "warm comic")),
            duration_minutes=(
                float(data["duration_minutes"])
                if data.get("duration_minutes") is not None
                else None
            ),
            constraints=_clean_strings(data.get("constraints")),
            schema=str(data.get("schema", "ssmdstudio.project.v1")),
        )


@dataclass(slots=True)
class Character:
    id: str
    name: str
    role: str
    description: str
    traits: list[str] = field(default_factory=list)
    goals: list[str] = field(default_factory=list)
    voice_notes: str = ""
    ssmd_role: SSMDRole | None = None
    constraints: list[str] = field(default_factory=list)
    schema: str = "ssmdstudio.character.v1"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["traits"] = _clean_strings(self.traits)
        data["goals"] = _clean_strings(self.goals)
        data["constraints"] = _clean_strings(self.constraints)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Character:
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            role=str(data.get("role", "")),
            description=str(data.get("description", "")),
            traits=_clean_strings(data.get("traits")),
            goals=_clean_strings(data.get("goals")),
            voice_notes=str(data.get("voice_notes", "")),
            ssmd_role=data.get("ssmd_role"),
            constraints=_clean_strings(data.get("constraints")),
            schema=str(data.get("schema", "ssmdstudio.character.v1")),
        )


@dataclass(slots=True)
class Scene:
    id: str
    title: str
    purpose: str
    characters: list[str] = field(default_factory=list)
    events: list[str] = field(default_factory=list)
    comic_function: str = ""
    constraints: list[str] = field(default_factory=list)
    locked: bool = False
    schema: str = "ssmdstudio.scene.v1"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["characters"] = _clean_strings(self.characters)
        data["events"] = _clean_strings(self.events)
        data["constraints"] = _clean_strings(self.constraints)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Scene:
        return cls(
            id=str(data["id"]),
            title=str(data["title"]),
            purpose=str(data.get("purpose", "")),
            characters=_clean_strings(data.get("characters")),
            events=_clean_strings(data.get("events")),
            comic_function=str(data.get("comic_function", "")),
            constraints=_clean_strings(data.get("constraints")),
            locked=bool(data.get("locked", False)),
            schema=str(data.get("schema", "ssmdstudio.scene.v1")),
        )


@dataclass(slots=True)
class Feedback:
    id: str
    instructions: list[str]
    scope: list[str] = field(default_factory=list)
    locked: list[str] = field(default_factory=list)
    status: Literal["open", "applied"] = "open"
    schema: str = "ssmdstudio.feedback.v1"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["instructions"] = _clean_strings(self.instructions)
        data["scope"] = _clean_strings(self.scope)
        data["locked"] = _clean_strings(self.locked)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Feedback:
        return cls(
            id=str(data["id"]),
            instructions=_clean_strings(data.get("instructions")),
            scope=_clean_strings(data.get("scope")),
            locked=_clean_strings(data.get("locked")),
            status=str(data.get("status", "open")),  # type: ignore[arg-type]
            schema=str(data.get("schema", "ssmdstudio.feedback.v1")),
        )
