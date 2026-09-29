from __future__ import annotations

from importlib.resources import files
from collections.abc import Mapping


STAGES = ("characters", "scenes", "draft", "revise", "ssmd")


def template_text(stage: str) -> str:
    if stage not in STAGES:
        raise ValueError(f"unknown prompt stage {stage!r}; choose from {', '.join(STAGES)}")
    resource = files("ssmdstudio").joinpath("resources", "prompts", "funny-story", f"{stage}.md")
    return resource.read_text(encoding="utf-8")


def render_template(stage: str, values: Mapping[str, str]) -> str:
    text = template_text(stage)
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    return text
