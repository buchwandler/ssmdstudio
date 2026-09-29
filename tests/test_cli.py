from __future__ import annotations

import json
from pathlib import Path

from ssmdstudio.cli import main


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
    start = output.rfind("{")
    status = json.loads(output[start:])
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
