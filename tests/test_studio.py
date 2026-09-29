from __future__ import annotations

from pathlib import Path

import pytest

from ssmdstudio import Studio


def make_studio(tmp_path: Path) -> Studio:
    return Studio.init(
        tmp_path / "story",
        title="Picnic trouble",
        brief="Anna prepares a picnic while a dog keeps stealing napkins.",
    )


def test_flat_project_store_and_prompt_pipeline(tmp_path: Path) -> None:
    studio = make_studio(tmp_path)

    studio.add_character(
        id="anna",
        name="Anna",
        role="protagonist",
        description="Patient and organized.",
        traits=["patient"],
        voice_notes="Warm and natural",
        ssmd_role="host",
    )
    studio.add_character(
        id="dog",
        name="Milo",
        role="counterpart",
        description="A curious harmless dog.",
        traits=["curious"],
    )
    studio.add_scene(
        id="setup",
        title="First missing napkin",
        purpose="Introduce the problem.",
        characters=["anna", "dog"],
        events=["Anna sets the table.", "The dog takes a napkin."],
    )

    draft_prompt = studio.build_prompt("draft")
    assert "Anna" in draft_prompt
    assert "First missing napkin" in draft_prompt
    assert "do not add SSMD markup yet" in draft_prompt

    draft_file = tmp_path / "draft.md"
    draft_file.write_text("Anna put down a napkin. Milo removed it.\n", encoding="utf-8")
    studio.set_draft(draft_file)

    studio.add_feedback(
        id="slower",
        scope=["scene:setup"],
        instructions=["Give Anna one more attempt before the consequence."],
        locked=["character:anna"],
    )

    revise_prompt = studio.build_prompt("revise")
    assert "Give Anna one more attempt" in revise_prompt
    assert "Anna put down a napkin" in revise_prompt

    ssmd_prompt = studio.build_prompt("ssmd")
    assert 'ssmd_version: "0.9"' in ssmd_prompt
    assert "Do not use `::{...}` for directive openings." in ssmd_prompt


def test_ssmd_roles_are_unique(tmp_path: Path) -> None:
    studio = make_studio(tmp_path)
    studio.add_character(
        id="anna",
        name="Anna",
        role="protagonist",
        description="",
        ssmd_role="host",
    )
    with pytest.raises(ValueError, match="already assigned"):
        studio.add_character(
            id="jo",
            name="Jo",
            role="friend",
            description="",
            ssmd_role="host",
        )


def test_scene_rejects_unknown_character(tmp_path: Path) -> None:
    studio = make_studio(tmp_path)
    with pytest.raises(ValueError, match="unknown character"):
        studio.add_scene(
            id="setup",
            title="Setup",
            purpose="Start",
            characters=["missing"],
        )


def test_prompt_run_becomes_stale_after_input_change(tmp_path: Path) -> None:
    studio = make_studio(tmp_path)
    studio.add_character(
        id="anna",
        name="Anna",
        role="protagonist",
        description="Patient.",
    )

    prompt = studio.build_prompt("scenes")
    studio.save_prompt_run("scenes", prompt)
    assert studio.run_statuses()[-1]["state"] == "current"

    studio.add_character(
        id="dog",
        name="Milo",
        role="counterpart",
        description="Curious.",
    )
    assert studio.run_statuses()[-1]["state"] == "stale"


def test_ssmd_prompt_requires_draft(tmp_path: Path) -> None:
    studio = make_studio(tmp_path)
    studio.add_character(
        id="anna",
        name="Anna",
        role="protagonist",
        description="Patient.",
    )
    studio.add_scene(
        id="setup",
        title="Setup",
        purpose="Start",
        characters=["anna"],
    )
    with pytest.raises(ValueError, match="requires drafts/current.md"):
        studio.build_prompt("ssmd")


def test_import_model_yaml(tmp_path: Path) -> None:
    studio = make_studio(tmp_path)
    characters = tmp_path / "characters.yaml"
    characters.write_text(
        "characters:\n"
        "  - id: anna\n"
        "    name: Anna\n"
        "    role: protagonist\n"
        "    description: Patient.\n"
        "    ssmd_role: host\n",
        encoding="utf-8",
    )
    imported = studio.import_characters(characters)
    assert [item.id for item in imported] == ["anna"]

    scenes = tmp_path / "scenes.yaml"
    scenes.write_text(
        "scenes:\n"
        "  - id: setup\n"
        "    title: Setup\n"
        "    purpose: Start the problem.\n"
        "    characters: [anna]\n"
        "    events: [Anna starts.]\n",
        encoding="utf-8",
    )
    imported_scenes = studio.import_scenes(scenes)
    assert [item.id for item in imported_scenes] == ["setup"]


def test_character_prompt_run_tracks_existing_characters(tmp_path: Path) -> None:
    studio = make_studio(tmp_path)
    studio.save_prompt_run("characters")
    assert studio.run_statuses()[-1]["state"] == "current"
    studio.add_character(id="anna", name="Anna", role="protagonist", description="Patient.")
    assert studio.run_statuses()[-1]["state"] == "stale"
