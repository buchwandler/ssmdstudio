from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from ssmdstudio import Studio
from ssmdstudio.models import Character
from ssmdstudio.prompts import STAGE_SPECS


def make_studio(tmp_path: Path) -> Studio:
    studio = Studio.init(
        tmp_path / "story",
        title="Picnic trouble",
        brief="Anna prepares a picnic while a dog keeps stealing napkins.",
    )
    studio.install_prompt_pack(Path(__file__).parents[1] / "prompts" / "workflows" / "funny-story")
    return studio


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

    ssmd_prompt = studio.build_prompt("ssmd")
    assert 'ssmd_version: "0.9"' in ssmd_prompt
    assert "Do not use `::{...}` for directive openings." in ssmd_prompt
    studio.add_feedback(
        id="slower",
        scope=["scene:setup"],
        instructions=["Give Anna one more attempt before the consequence."],
        locked=["character:anna"],
    )

    revise_prompt = studio.build_prompt("revise")
    assert "Give Anna one more attempt" in revise_prompt
    assert "Anna put down a napkin" in revise_prompt

    with pytest.raises(ValueError, match="no open feedback"):
        studio.build_prompt("ssmd")


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


def test_prompt_compilation_requires_a_project_prompt_pack(tmp_path: Path) -> None:
    studio = Studio.init(tmp_path / "story", title="Test", brief="A story.")

    with pytest.raises(
        FileNotFoundError,
        match="(?s)no workflow prompt pack is installed.*ssmdstudio prompt pack install PATH",
    ):
        studio.build_prompt("characters")


def test_compiler_uses_custom_template_and_rejects_unknown_placeholders(
    tmp_path: Path,
) -> None:
    studio = make_studio(tmp_path)
    template_path = studio.prompt_pack_path / "characters.md"
    template_path.write_text(
        "Custom user prompt for {{ARTIFACT_NAME}} in {{PROJECT}}.", encoding="utf-8"
    )

    prompt = studio.build_prompt("characters")

    assert "Custom user prompt for characters.yaml" in prompt
    assert "id: story" in prompt

    template_path.write_text("Use {{SOURCE_NOTES}}", encoding="utf-8")
    with pytest.raises(ValueError, match=r"unresolved placeholder.*\{\{SOURCE_NOTES\}\}"):
        studio.build_prompt("characters")


def test_prompt_run_tracks_template_fingerprint_and_provenance(tmp_path: Path) -> None:
    studio = make_studio(tmp_path)
    run_dir = studio.save_prompt_run("characters")
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    template_path = studio.prompt_pack_path / "characters.md"
    provenance = manifest["prompt_pack"]

    assert provenance["id"] == "funny-story"
    assert provenance["schema"] == "ssmdstudio.prompt-pack.v1"
    assert provenance["template"] == "characters.md"
    assert provenance["template_sha256"] == hashlib.sha256(template_path.read_bytes()).hexdigest()
    assert {"prompts/prompt-pack.yaml", "prompts/characters.md"} <= {
        item["path"] for item in manifest["inputs"]
    }
    assert studio.run_statuses()[-1]["state"] == "current"

    template_path.write_text(
        template_path.read_text(encoding="utf-8") + "\\nUser edit.\\n", encoding="utf-8"
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


def test_stage_prompts_use_named_artifacts_and_compact_context(tmp_path: Path) -> None:
    studio = make_studio(tmp_path)
    studio.add_character(
        id="narrator",
        name="Narrator",
        role="non-diegetic narrator",
        description="Keeps the action clear.",
        voice_notes="Warm and unobtrusive.",
        ssmd_role="narrator",
    )
    studio.add_character(
        id="office-printer",
        name="Office Printer",
        role="counterpart",
        description="A precise machine.",
        voice_notes="Measured and bureaucratic.",
        ssmd_role="machine-voice",
    )
    studio.add_scene(
        id="scene-01",
        title="Secret scene title",
        purpose="Introduce the problem.",
        characters=["narrator", "office-printer"],
        events=["The printer refuses a page."],
    )
    draft = tmp_path / "draft.md"
    draft.write_text("The printer refused the page.\n", encoding="utf-8")
    studio.set_draft(draft)

    assert STAGE_SPECS["ssmd"].expected_artifact(studio.config.id) == "story.ssmd.md"
    for stage, filename in (
        ("characters", "characters.yaml"),
        ("scenes", "scenes.yaml"),
        ("draft", "draft.md"),
        ("ssmd", "story.ssmd.md"),
    ):
        prompt = studio.build_prompt(stage)
        assert f"Create exactly one artifact named `{filename}`" in prompt
        assert "create downloadable files" in prompt
        assert "schema:" not in prompt

    characters_prompt = studio.build_prompt("characters")
    assert "lowercase kebab-case" in characters_prompt
    assert "include a narrator speaker brief" in characters_prompt
    assert "ssmd_role: narrator" in characters_prompt

    scenes_prompt = studio.build_prompt("scenes")
    assert "complete currently approved scene plan" in scenes_prompt
    assert "lowercase kebab-case" in scenes_prompt

    draft_prompt = studio.build_prompt("draft")
    assert "locally and unambiguously attributable" in draft_prompt
    assert "screenplay-style `NAME:` labels" in draft_prompt

    ssmd_prompt = studio.build_prompt("ssmd")
    assert "id: narrator" in ssmd_prompt
    assert "ssmd_role: narrator" in ssmd_prompt
    assert "machine-voice" in ssmd_prompt
    assert "Secret scene title" not in ssmd_prompt
    assert "should normally be adjacent fenced directives" in ssmd_prompt

    studio.add_feedback(id="revision", instructions=["Clarify the refusal."])
    revise_prompt = studio.build_prompt("revise")
    assert "story text" in revise_prompt
    assert "complete revised draft, not a patch" in revise_prompt
    assert "draft.md" in revise_prompt


def test_symbolic_roles_are_open_but_validated() -> None:
    character = Character.from_dict(
        {
            "id": "announcer",
            "name": "Announcer",
            "role": "voice",
            "description": "",
            "ssmd_role": "alternate_voice.2",
        }
    )
    assert character.ssmd_role == "alternate_voice.2"

    with pytest.raises(ValueError, match="symbolic identifier without whitespace"):
        Character.from_dict(
            {
                "id": "announcer",
                "name": "Announcer",
                "role": "voice",
                "description": "",
                "ssmd_role": "Voice Over",
            }
        )


def _write_yaml(tmp_path: Path, filename: str, key: str, items: list[dict]) -> Path:
    path = tmp_path / filename
    path.write_text(yaml.safe_dump({key: items}, sort_keys=False), encoding="utf-8")
    return path


def test_character_import_is_atomic_replace_by_default_and_merge_on_request(
    tmp_path: Path,
) -> None:
    studio = make_studio(tmp_path)
    anna = {
        "id": "anna",
        "name": "Anna",
        "role": "protagonist",
        "description": "Patient.",
        "ssmd_role": "host",
    }
    jo = {
        "id": "jo",
        "name": "Jo",
        "role": "friend",
        "description": "Observant.",
        "ssmd_role": "guest",
    }
    initial = _write_yaml(tmp_path, "characters.yaml", "characters", [anna, jo])
    studio.import_characters(initial)
    original = {
        path.name: path.read_bytes() for path in (studio.root / "characters").glob("*.yaml")
    }

    invalid_second = _write_yaml(
        tmp_path,
        "invalid.yaml",
        "characters",
        [anna | {"description": "Changed."}, {"id": "bad", "name": "Bad", "role": "other"}],
    )
    with pytest.raises(ValueError, match="description"):
        studio.import_characters(invalid_second)
    assert {
        path.name: path.read_bytes() for path in (studio.root / "characters").glob("*.yaml")
    } == original

    duplicate = _write_yaml(tmp_path, "duplicate.yaml", "characters", [anna, anna])
    with pytest.raises(ValueError, match="duplicate character ID"):
        studio.import_characters(duplicate)

    duplicate_roles = _write_yaml(
        tmp_path,
        "duplicate-roles.yaml",
        "characters",
        [anna, jo | {"ssmd_role": "host"}],
    )
    with pytest.raises(ValueError, match="duplicate SSMD role"):
        studio.import_characters(duplicate_roles)
    assert {
        path.name: path.read_bytes() for path in (studio.root / "characters").glob("*.yaml")
    } == original

    replacement = _write_yaml(tmp_path, "replacement.yaml", "characters", [anna])
    studio.import_characters(replacement)
    assert [item.id for item in studio.characters()] == ["anna"]

    merge = _write_yaml(tmp_path, "merge.yaml", "characters", [jo])
    studio.import_characters(merge, merge=True)
    assert {item.id for item in studio.characters()} == {"anna", "jo"}


def test_scene_import_is_atomic_replace_by_default_and_merge_on_request(
    tmp_path: Path,
) -> None:
    studio = make_studio(tmp_path)
    studio.add_character(id="hero", name="Hero", role="protagonist", description="Ready.")
    studio.add_scene(id="old-scene", title="Old", purpose="Existing.", characters=["hero"])
    original = {path.name: path.read_bytes() for path in (studio.root / "scenes").glob("*.yaml")}

    invalid = _write_yaml(
        tmp_path,
        "invalid-scenes.yaml",
        "scenes",
        [
            {"id": "new-scene", "title": "New", "purpose": "Start."},
            {"id": "bad-scene", "title": "Bad", "purpose": "Fail.", "characters": ["missing"]},
        ],
    )
    with pytest.raises(ValueError, match="unknown character"):
        studio.import_scenes(invalid)
    assert {
        path.name: path.read_bytes() for path in (studio.root / "scenes").glob("*.yaml")
    } == original

    duplicate = _write_yaml(
        tmp_path,
        "duplicate-scenes.yaml",
        "scenes",
        [
            {"id": "repeat", "title": "One", "purpose": "First."},
            {"id": "repeat", "title": "Two", "purpose": "Second."},
        ],
    )
    with pytest.raises(ValueError, match="duplicate scene ID"):
        studio.import_scenes(duplicate)
    assert {
        path.name: path.read_bytes() for path in (studio.root / "scenes").glob("*.yaml")
    } == original

    replacement = _write_yaml(
        tmp_path,
        "replacement-scenes.yaml",
        "scenes",
        [{"id": "new-scene", "title": "New", "purpose": "Start.", "characters": ["hero"]}],
    )
    studio.import_scenes(replacement)
    assert [item.id for item in studio.scenes()] == ["new-scene"]

    merge = _write_yaml(
        tmp_path,
        "merge-scenes.yaml",
        "scenes",
        [{"id": "next-scene", "title": "Next", "purpose": "Continue.", "characters": ["hero"]}],
    )
    studio.import_scenes(merge, merge=True)
    assert {item.id for item in studio.scenes()} == {"new-scene", "next-scene"}


def test_next_stage_apply_and_run_response_provenance(tmp_path: Path) -> None:
    studio = make_studio(tmp_path)
    assert studio.next_stage() == "characters"
    assert studio.status()["next_stage"] == "characters"

    characters = _write_yaml(
        tmp_path,
        "characters.yaml",
        "characters",
        [{"id": "hero", "name": "Hero", "role": "protagonist", "description": "Ready."}],
    )
    character_run = studio.save_prompt_run("characters")
    character_manifest = json.loads((character_run / "manifest.json").read_text(encoding="utf-8"))
    assert character_manifest["expected_artifact"] == "characters.yaml"
    assert character_manifest["response_file"] is None
    applied = studio.apply(characters)
    assert applied["stage"] == "characters"
    assert applied["changed_files"] == ["characters/hero.yaml"]
    assert studio.next_stage() == "scenes"
    assert (character_run / "response.yaml").read_text(encoding="utf-8") == characters.read_text(
        encoding="utf-8"
    )
    character_manifest = json.loads((character_run / "manifest.json").read_text(encoding="utf-8"))
    assert character_manifest["response_file"] == "response.yaml"
    assert character_manifest["applied_at"]
    assert character_manifest["changed_files"] == ["characters/hero.yaml"]

    scenes = _write_yaml(
        tmp_path,
        "scenes.yaml",
        "scenes",
        [
            {
                "id": "scene-01",
                "title": "Start",
                "purpose": "Introduce the task.",
                "characters": ["hero"],
            }
        ],
    )
    scene_run = studio.save_prompt_run("scenes")
    studio.apply(scenes)
    assert studio.next_stage() == "draft"
    assert (scene_run / "response.yaml").is_file()

    draft = tmp_path / "draft.md"
    draft.write_text("Hero tried the task.\n", encoding="utf-8")
    studio.save_prompt_run("draft")
    studio.apply(draft)
    assert studio.next_stage() == "ssmd"

    studio.add_feedback(id="revision", instructions=["Clarify the task."])
    assert studio.next_stage() == "revise"
    revision_run = studio.save_prompt_run("revise")
    revised = tmp_path / "draft.md"
    revised.write_text("Hero tried the task twice.\n", encoding="utf-8")
    studio.apply(revised)
    assert studio.next_stage() == "ssmd"
    assert not studio.feedback(open_only=True)
    assert (revision_run / "response.md").is_file()

    ssmd_run = studio.save_prompt_run("ssmd")
    output = tmp_path / "story.ssmd.md"
    output.write_text('---\\nssmd_version: "0.9"\\n---\\nNarration.\\n', encoding="utf-8")
    result = studio.apply(output)
    assert result["changed_files"] == ["output/current.ssmd.md"]
    assert (ssmd_run / "response.ssmd.md").is_file()
    assert studio.next_stage() is None


def test_apply_explicit_stage_override(tmp_path: Path) -> None:
    studio = make_studio(tmp_path)
    scene_file = _write_yaml(
        tmp_path,
        "scenes.yaml",
        "scenes",
        [{"id": "scene-01", "title": "Start", "purpose": "Begin."}],
    )
    result = studio.apply(scene_file, stage="scenes")
    assert result["stage"] == "scenes"
    assert studio.scenes()[0].id == "scene-01"
    assert studio.next_stage() == "characters"
