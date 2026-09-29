from __future__ import annotations

import json
from pathlib import Path

import yaml

from ssmdstudio.cli import main
from ssmdstudio.prompts import STAGES


def _write_prompt_pack(root: Path) -> Path:
    root.mkdir(parents=True)
    stages = {stage: f"{stage}.md" for stage in STAGES}
    for stage, filename in stages.items():
        (root / filename).write_text(f"{stage} prompt\n", encoding="utf-8")
    manifest = {
        "schema": "ssmdstudio.prompt-pack.v1",
        "id": "cli-test-pack",
        "kind": "workflow",
        "stages": stages,
    }
    (root / "prompt-pack.yaml").write_text(
        yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8"
    )
    return root


def test_cli_smoke(tmp_path: Path, capsys) -> None:
    project = tmp_path / "story"
    main(
        [
            "init",
            str(project),
            "--title",
            "Test",
            "--brief",
            "A small funny story.",
        ]
    )
    assert (project / "project.yaml").is_file()

    main(
        [
            "character",
            "add",
            "hero",
            "--project",
            str(project),
            "--name",
            "Hero",
            "--role",
            "protagonist",
            "--description",
            "Trying to finish a simple task.",
        ]
    )

    main(["status", "--project", str(project), "--json"])
    output = capsys.readouterr().out
    status = json.loads(output[output.index("{") :])
    assert status["characters"] == 1


def test_cli_next_prompt_next_and_apply(tmp_path: Path, capsys) -> None:
    project = tmp_path / "story"
    main(
        [
            "init",
            str(project),
            "--title",
            "Test",
            "--brief",
            "A small funny story.",
            "--prompt-pack",
            str(Path(__file__).parents[1] / "prompts" / "workflows" / "funny-story"),
        ]
    )
    capsys.readouterr()

    main(["next", "--project", str(project)])
    guidance = capsys.readouterr().out
    assert "next stage: characters" in guidance
    assert "expected artifact: characters.yaml" in guidance
    assert "ssmdstudio apply characters.yaml" in guidance

    main(["prompt", "next", "--save", "--project", str(project)])
    prompt_output = capsys.readouterr()
    assert "Create exactly one artifact named `characters.yaml`" in prompt_output.out
    assert "saved prompt: runs/" in prompt_output.err
    assert "apply with: ssmdstudio apply characters.yaml" in prompt_output.err

    characters = tmp_path / "characters.yaml"
    characters.write_text(
        "characters:\n"
        "  - id: hero\n"
        "    name: Hero\n"
        "    role: protagonist\n"
        "    description: Ready.\n",
        encoding="utf-8",
    )
    main(["apply", str(characters), "--project", str(project)])
    applied = capsys.readouterr().out
    assert "stage: characters" in applied
    assert "characters/hero.yaml" in applied

    main(["status", "--project", str(project), "--json"])
    status = json.loads(capsys.readouterr().out)
    assert status["next_stage"] == "scenes"


def test_prompt_pack_cli_validate_install_path_and_status(tmp_path: Path, capsys) -> None:
    source = _write_prompt_pack(tmp_path / "pack")
    project = tmp_path / "story"

    main(["prompt", "pack", "validate", str(source)])
    assert "valid workflow prompt pack: cli-test-pack" in capsys.readouterr().out

    main(["init", str(project), "--title", "Test", "--brief", "Prompt pack CLI."])
    capsys.readouterr()

    main(["prompt", "pack", "path", "--project", str(project)])
    assert capsys.readouterr().out.strip() == str(project / "prompts")

    main(["prompt", "pack", "install", str(source), "--project", str(project)])
    assert capsys.readouterr().out.strip() == str(project / "prompts")

    main(["status", "--project", str(project)])
    human = capsys.readouterr().out
    assert "prompt pack: cli-test-pack" in human
    assert "prompt path: prompts/" in human

    main(["status", "--project", str(project), "--json"])
    status = json.loads(capsys.readouterr().out)
    assert status["prompt_pack"] == {
        "installed": True,
        "id": "cli-test-pack",
        "path": "prompts",
    }


def test_workspace_project_create_accepts_prompt_pack(tmp_path: Path, capsys, monkeypatch) -> None:
    workspace = tmp_path / "workspace"
    source = _write_prompt_pack(tmp_path / "pack")
    main(["workspace", "init", str(workspace)])
    capsys.readouterr()
    monkeypatch.chdir(workspace)

    main(
        [
            "project",
            "create",
            "picnic",
            "--title",
            "Picnic",
            "--brief",
            "A short story.",
            "--prompt-pack",
            str(source),
        ]
    )

    assert (workspace / "projects" / "picnic" / "prompts" / "prompt-pack.yaml").is_file()
    assert "projects/picnic" in capsys.readouterr().out


def test_init_cli_accepts_optional_prompt_pack(tmp_path: Path, capsys) -> None:
    project = tmp_path / "story"
    source = _write_prompt_pack(tmp_path / "pack")

    main(
        [
            "init",
            str(project),
            "--title",
            "Test",
            "--brief",
            "Prompt pack selected at init.",
            "--prompt-pack",
            str(source),
        ]
    )

    assert (project / "prompts" / "prompt-pack.yaml").is_file()
    assert str(project) in capsys.readouterr().out
