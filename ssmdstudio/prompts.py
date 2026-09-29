from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files
from collections.abc import Mapping
from typing import Literal


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


def template_text(stage: str) -> str:
    if stage not in STAGE_SPECS:
        raise ValueError(f"unknown prompt stage {stage!r}; choose from {', '.join(STAGES)}")
    resource = files("ssmdstudio").joinpath("resources", "prompts", "funny-story", f"{stage}.md")
    return resource.read_text(encoding="utf-8")


def render_template(stage: str, values: Mapping[str, str]) -> str:
    text = template_text(stage)
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    return text
