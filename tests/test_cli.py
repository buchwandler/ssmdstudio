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
