from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from ssmdstudio import Studio
from ssmdstudio.prompts import STAGES, PromptPack, render_template


def _make_pack(root: Path) -> dict[str, str]:
    root.mkdir(parents=True, exist_ok=True)
    stages = {stage: f"{stage}.md" for stage in STAGES}
    for stage, filename in stages.items():
        (root / filename).write_text(f"{stage} template\n", encoding="utf-8")
    _write_manifest(root, stages)
    return stages


def _write_manifest(root: Path, stages: dict[str, str], **overrides: object) -> None:
    manifest: dict[str, object] = {
        "schema": "ssmdstudio.prompt-pack.v1",
        "id": "test-pack",
        "kind": "workflow",
        "stages": stages,
    }
    manifest.update(overrides)
    (root / "prompt-pack.yaml").write_text(
        yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8"
    )


def test_valid_pack_opens_and_reads_utf8_templates(tmp_path: Path) -> None:
    stages = _make_pack(tmp_path / "pack")

    pack = PromptPack.open(tmp_path / "pack")

    assert pack.id == "test-pack"
    assert pack.schema == "ssmdstudio.prompt-pack.v1"
    assert tuple(pack.stages) == STAGES
    assert pack.template_path("characters") == (tmp_path / "pack" / stages["characters"]).resolve()
    assert pack.template_text("characters") == "characters template\n"
    with pytest.raises(TypeError):
        pack.stages["extra"] = tmp_path / "extra.md"  # type: ignore[index]


def test_missing_manifest_fails_explicitly(tmp_path: Path) -> None:
    pack_dir = tmp_path / "pack"
    pack_dir.mkdir()
    with pytest.raises(FileNotFoundError, match="prompt pack manifest not found"):
        PromptPack.open(pack_dir)


def test_wrong_schema_and_non_workflow_kind_fail(tmp_path: Path) -> None:
    root = tmp_path / "pack"
    stages = _make_pack(root)
    _write_manifest(root, stages, schema="ssmdstudio.prompt-pack.v2")
    with pytest.raises(ValueError, match="unsupported prompt pack schema"):
        PromptPack.open(root)

    _write_manifest(root, stages, kind="standalone")
    with pytest.raises(ValueError, match="kind must be 'workflow'"):
        PromptPack.open(root)


def test_missing_and_unknown_stages_fail_explicitly(tmp_path: Path) -> None:
    root = tmp_path / "pack"
    stages = _make_pack(root)
    missing_stage = dict(stages)
    missing_stage.pop("revise")
    _write_manifest(root, missing_stage)
    with pytest.raises(ValueError, match="missing stage.*revise"):
        PromptPack.open(root)

    extra_stage = dict(stages, custom="custom.md")
    (root / "custom.md").write_text("custom\n", encoding="utf-8")
    _write_manifest(root, extra_stage)
    with pytest.raises(ValueError, match="unknown stage.*custom"):
        PromptPack.open(root)


def test_duplicate_stage_keys_are_rejected(tmp_path: Path) -> None:
    root = tmp_path / "pack"
    _make_pack(root)
    (root / "prompt-pack.yaml").write_text(
        "schema: ssmdstudio.prompt-pack.v1\n"
        "id: test-pack\n"
        "kind: workflow\n"
        "stages:\n"
        "  characters: characters.md\n"
        "  characters: another.md\n"
        "  scenes: scenes.md\n"
        "  draft: draft.md\n"
        "  revise: revise.md\n"
        "  ssmd: ssmd.md\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate key 'characters'"):
        PromptPack.open(root)


@pytest.mark.parametrize("unsafe_path", ["/absolute.md", "../outside.md", "C:\\outside.md"])
def test_absolute_and_traversing_template_paths_are_rejected(
    tmp_path: Path, unsafe_path: str
) -> None:
    root = tmp_path / "pack"
    stages = _make_pack(root)
    _write_manifest(root, {**stages, "characters": unsafe_path})
    with pytest.raises(ValueError, match="safe relative path"):
        PromptPack.open(root)


def test_symlink_escaping_pack_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "pack"
    stages = _make_pack(root)
    outside = tmp_path / "outside.md"
    outside.write_text("outside\n", encoding="utf-8")
    (root / stages["characters"]).unlink()
    (root / stages["characters"]).symlink_to(outside)

    with pytest.raises(ValueError, match="escapes prompt pack"):
        PromptPack.open(root)


def test_missing_template_and_directory_mapping_fail(tmp_path: Path) -> None:
    root = tmp_path / "pack"
    stages = _make_pack(root)
    missing = dict(stages, characters="missing.md")
    _write_manifest(root, missing)
    with pytest.raises(FileNotFoundError, match="template not found for stage 'characters'"):
        PromptPack.open(root)

    (root / "characters.md").unlink()
    (root / "characters.md").mkdir()
    _write_manifest(root, stages)
    with pytest.raises(ValueError, match="not a regular file"):
        PromptPack.open(root)


def test_invalid_utf8_manifest_and_template_fail_cleanly(tmp_path: Path) -> None:
    root = tmp_path / "pack"
    _make_pack(root)
    (root / "characters.md").write_bytes(b"\xff\xfe")
    with pytest.raises(ValueError, match="template is not valid UTF-8 for stage 'characters'"):
        PromptPack.open(root)

    (root / "characters.md").write_text("valid\n", encoding="utf-8")
    (root / "prompt-pack.yaml").write_bytes(b"\xff\xfe")
    with pytest.raises(ValueError, match="manifest is not valid UTF-8"):
        PromptPack.open(root)


def test_unknown_stage_lookup_fails_with_supported_stages(tmp_path: Path) -> None:
    root = tmp_path / "pack"
    _make_pack(root)
    pack = PromptPack.open(root)
    with pytest.raises(ValueError, match="unknown prompt stage 'unknown'"):
        pack.template_path("unknown")


def test_renderer_is_pure_and_rejects_unresolved_all_caps_placeholders() -> None:
    assert (
        render_template(
            "Hello {{PROJECT}}: {{ARTIFACT_NAME}}",
            {
                "PROJECT": "Picnic",
                "ARTIFACT_NAME": "characters.yaml",
            },
        )
        == "Hello Picnic: characters.yaml"
    )
    assert render_template("{{project}} {{lower-case}}", {}) == "{{project}} {{lower-case}}"
    with pytest.raises(ValueError, match=r"unresolved placeholder.*\{\{SOURCE_NOTES\}\}"):
        render_template("Use {{PROJECT}} and {{SOURCE_NOTES}}", {"PROJECT": "story"})


def test_prompt_pack_install_copies_source_into_project(tmp_path: Path) -> None:
    source = tmp_path / "source"
    _make_pack(source)
    studio = Studio.init(tmp_path / "story", title="Test", brief="A test story.")

    installed = studio.install_prompt_pack(source)

    assert installed == studio.prompt_pack_path
    assert PromptPack.open(installed).id == "test-pack"
    assert (installed / "characters.md").read_text(encoding="utf-8") == "characters template\n"
    assert studio.status()["prompt_pack"] == {
        "installed": True,
        "id": "test-pack",
        "path": "prompts",
    }


def test_prompt_pack_install_refuses_overwrite_and_replaces_complete_pack(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    _make_pack(source)
    studio = Studio.init(tmp_path / "story", title="Test", brief="A test story.")
    installed = studio.install_prompt_pack(source)
    original = {
        path.relative_to(installed): path.read_bytes()
        for path in installed.rglob("*")
        if path.is_file()
    }

    with pytest.raises(FileExistsError, match="pass replace=True"):
        studio.install_prompt_pack(source)
    assert {
        path.relative_to(installed): path.read_bytes()
        for path in installed.rglob("*")
        if path.is_file()
    } == original

    (installed / "obsolete.md").write_text("remove me\n", encoding="utf-8")
    replacement = tmp_path / "replacement"
    replacement_stages = _make_pack(replacement)
    (replacement / replacement_stages["characters"]).write_text("replacement\n", encoding="utf-8")
    _write_manifest(replacement, replacement_stages, id="replacement-pack")

    studio.install_prompt_pack(replacement, replace=True)

    assert PromptPack.open(installed).id == "replacement-pack"
    assert (installed / "characters.md").read_text(encoding="utf-8") == "replacement\n"
    assert not (installed / "obsolete.md").exists()


def test_invalid_prompt_pack_replacement_preserves_existing_project(tmp_path: Path) -> None:
    source = tmp_path / "source"
    _make_pack(source)
    studio = Studio.init(tmp_path / "story", title="Test", brief="A test story.")
    installed = studio.install_prompt_pack(source)
    original = {
        path.relative_to(installed): path.read_bytes()
        for path in installed.rglob("*")
        if path.is_file()
    }
    invalid = tmp_path / "invalid"
    invalid_stages = _make_pack(invalid)
    invalid_stages.pop("revise")
    _write_manifest(invalid, invalid_stages)

    with pytest.raises(ValueError, match="missing stage.*revise"):
        studio.install_prompt_pack(invalid, replace=True)

    assert {
        path.relative_to(installed): path.read_bytes()
        for path in installed.rglob("*")
        if path.is_file()
    } == original
    assert Studio.open(studio.root).config.id == studio.config.id


def test_init_accepts_optional_prompt_pack_and_status_reports_absence(tmp_path: Path) -> None:
    without_pack = Studio.init(
        tmp_path / "without-pack", title="Plain", brief="No prompt data yet."
    )
    assert without_pack.status()["prompt_pack"] == {
        "installed": False,
        "id": None,
        "path": "prompts",
    }

    source = tmp_path / "source"
    _make_pack(source)
    initialized = Studio.init(
        tmp_path / "with-pack",
        title="Ready",
        brief="Prompt pack installed at init.",
        prompt_pack=source,
    )
    assert PromptPack.open(initialized.prompt_pack_path).id == "test-pack"


def test_install_prompt_pack_rejects_symlinks_before_copy(tmp_path: Path) -> None:
    source = tmp_path / "source"
    _make_pack(source)
    outside = tmp_path / "outside.md"
    outside.write_text("outside\n", encoding="utf-8")
    (source / "unreferenced.md").symlink_to(outside)
    studio = Studio.init(tmp_path / "story", title="Test", brief="A test story.")

    with pytest.raises(ValueError, match="cannot contain symlinks"):
        studio.install_prompt_pack(source)
    assert not studio.prompt_pack_path.exists()
