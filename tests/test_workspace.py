from __future__ import annotations

import json
from pathlib import Path

import pytest

from ssmdstudio import Studio, Workspace
from ssmdstudio.cli import main


def test_workspace_creates_lists_and_resolves_sibling_projects(tmp_path: Path) -> None:
    workspace = Workspace.init(tmp_path / "stories")
    first = workspace.create_project("first-story", title="First", brief="The first story.")
    second = workspace.create_project("second-story", title="Second", brief="The second story.")

    assert first.root.parent == second.root.parent == workspace.projects_root
    assert [project.config.id for project in workspace.list_projects()] == [
        "first-story",
        "second-story",
    ]
    with pytest.raises(ValueError, match="no active project"):
        workspace.resolve_project()

    workspace.use_project("first-story")
    reopened = Workspace.open(workspace.root)
    assert reopened.resolve_project().config.id == "first-story"
    assert reopened.resolve_project("second-story").config.id == "second-story"
    assert Studio.open(first.root).config.id == "first-story"


def test_cli_workspace_commands_and_explicit_project_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "stories"
    main(["workspace", "init", str(root)])
    monkeypatch.chdir(root)

    main(["project", "create", "first-story", "--title", "First", "--brief", "First brief."])
    main(["project", "create", "second-story", "--title", "Second", "--brief", "Second brief."])
    assert (root / "projects" / "first-story" / "project.yaml").is_file()
    assert (root / "projects" / "second-story" / "project.yaml").is_file()

    main(["project", "list"])
    listing = capsys.readouterr().out
    assert "first-story\tFirst" in listing
    assert "second-story\tSecond" in listing

    main(["project", "use", "first-story"])
    capsys.readouterr()
    main(["status", "--json"])
    active_status = json.loads(capsys.readouterr().out)
    assert active_status["project"] == "first-story"

    main(["status", "--json", "--project", "second-story"])
    explicit_status = json.loads(capsys.readouterr().out)
    assert explicit_status["project"] == "second-story"

    main(["project", "show"])
    assert "first-story (active)" in capsys.readouterr().out


def test_nested_projects_are_refused_unless_explicitly_allowed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    project = Studio.init(tmp_path / "story", title="Story", brief="A story.")
    with pytest.raises(ValueError, match="refusing to create.*inside existing project"):
        Studio.init(project.root / "nested", title="Nested", brief="Nested story.")

    nested = Studio.init(
        project.root / "nested",
        title="Nested",
        brief="Nested story.",
        allow_nested=True,
    )
    assert nested.root == project.root / "nested"

    with pytest.raises(ValueError, match="inside an SSMD Studio project"):
        Workspace.init(project.root / "workspace")

    with pytest.raises(SystemExit) as error:
        main(
            [
                "init",
                str(project.root / "cli-nested"),
                "--title",
                "Nested",
                "--brief",
                "A nested story.",
            ]
        )
    assert error.value.code == 2
    assert "--allow-nested" in capsys.readouterr().err

    main(
        [
            "init",
            str(project.root / "cli-nested"),
            "--title",
            "Nested",
            "--brief",
            "A nested story.",
            "--allow-nested",
        ]
    )
    assert (project.root / "cli-nested" / "project.yaml").is_file()
