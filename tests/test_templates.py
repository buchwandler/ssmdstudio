from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from ssmdstudio.cli import main
from ssmdstudio.templates import TemplateLibrary


def test_builtin_template_library_seed_list_show_and_suffixes(tmp_path: Path) -> None:
    library = TemplateLibrary(tmp_path / "templates")

    assert library.directory() == (tmp_path / "templates").resolve()
    assert library.list() == ()
    seeded = library.seed()
    assert tuple(path.name for path in seeded) == (
        "briefing.ssmd",
        "dialogue.ssmd",
        "podcast.ssmd",
    )
    assert library.list() == ("briefing", "dialogue", "podcast")
    assert library.path("podcast").name == "podcast.ssmd"
    assert library.path("podcast.ssmd") == library.path("podcast")
    assert library.show("podcast") == (
        Path(__file__).parents[1] / "ssmdstudio/resources/templates/podcast.ssmd"
    ).read_text(encoding="utf-8")


def test_seed_is_idempotent_and_preserves_user_templates(tmp_path: Path) -> None:
    library = TemplateLibrary(tmp_path / "templates")
    library.seed()
    changed = library.path("podcast")
    changed.write_text("my edit\n", encoding="utf-8")
    source = tmp_path / "custom.ssmd.md"
    source.write_text("---\nssmd_version: '0.9'\n---\nCustom.\n", encoding="utf-8")
    custom = library.add("custom", source=source)

    library.seed()

    assert changed.read_text(encoding="utf-8") == "my edit\n"
    assert custom.name == "custom.ssmd.md"
    assert library.show("custom") == source.read_text(encoding="utf-8")
    assert library.list() == ("briefing", "custom", "dialogue", "podcast")


def test_add_preserves_source_suffix_and_requires_force_to_replace(tmp_path: Path) -> None:
    library = TemplateLibrary(tmp_path / "templates")
    source = tmp_path / "source.ssmd.md"
    source.write_text("one\n", encoding="utf-8")

    target = library.add("custom", source=source)
    assert target.name == "custom.ssmd.md"
    with pytest.raises(FileExistsError, match="force"):
        library.add("custom.ssmd.md", source=source)

    source.write_text("two\n", encoding="utf-8")
    assert library.add("custom", source=source, force=True) == target
    assert target.read_text(encoding="utf-8") == "two\n"


def test_reset_restores_only_builtin_names_and_preserves_custom(tmp_path: Path) -> None:
    library = TemplateLibrary(tmp_path / "templates")
    library.seed()
    builtin = library.path("briefing")
    builtin.write_text("edited built-in\n", encoding="utf-8")
    custom_source = tmp_path / "custom.ssmd"
    custom_source.write_text("custom\n", encoding="utf-8")
    custom = library.add("my-custom", source=custom_source)

    assert library.reset("briefing") == (builtin,)
    assert "# Briefing" in builtin.read_text(encoding="utf-8")
    restored = library.reset(all=True)
    assert tuple(path.name for path in restored) == (
        "briefing.ssmd",
        "dialogue.ssmd",
        "podcast.ssmd",
    )
    assert custom.is_file()
    with pytest.raises(ValueError, match="unknown built-in"):
        library.reset("my-custom")
    with pytest.raises(ValueError, match="name or all"):
        library.reset("briefing", all=True)


def test_unsafe_names_and_invalid_extensions_are_rejected(tmp_path: Path) -> None:
    library = TemplateLibrary(tmp_path / "templates")
    source = tmp_path / "source.ssmd"
    source.write_text("content\n", encoding="utf-8")
    for name in ("", "../escape", "/absolute", r"nested\\name", "bad.txt", ".."):
        with pytest.raises(ValueError):
            library.add(name, source=source)


def test_template_suffix_collision_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "templates"
    root.mkdir()
    (root / "clash.ssmd").write_text("one", encoding="utf-8")
    (root / "clash.ssmd.md").write_text("two", encoding="utf-8")
    library = TemplateLibrary(root)

    with pytest.raises(ValueError, match="suffix collision"):
        library.list()
    with pytest.raises(ValueError, match="suffix collision"):
        library.path("clash")


def test_symlinked_template_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "templates"
    root.mkdir()
    outside = tmp_path / "outside.ssmd"
    outside.write_text("outside", encoding="utf-8")
    link = root / "escaped.ssmd"
    try:
        link.symlink_to(outside)
    except OSError as error:
        pytest.skip(f"symlinks unavailable: {error}")
    library = TemplateLibrary(root)

    with pytest.raises(ValueError, match="symlink"):
        library.path("escaped")
    with pytest.raises(ValueError, match="symlink"):
        library.list()


def test_failed_atomic_force_write_preserves_previous_template(tmp_path: Path, monkeypatch) -> None:
    library = TemplateLibrary(tmp_path / "templates")
    library.seed()
    target = library.path("podcast")
    original = target.read_bytes()
    source = tmp_path / "replacement.ssmd"
    source.write_text("replacement", encoding="utf-8")

    def fail_replace(_source: os.PathLike[str] | str, _target: os.PathLike[str] | str) -> None:
        raise OSError("simulated replace failure")

    monkeypatch.setattr("ssmdstudio.templates.os.replace", fail_replace)
    with pytest.raises(OSError, match="simulated"):
        library.add("podcast", source=source, force=True)

    assert target.read_bytes() == original
    assert not list(target.parent.glob(f".{target.name}.*"))


def test_use_defaults_to_ssmd_md_and_never_overwrites_without_force(tmp_path: Path) -> None:
    library = TemplateLibrary(tmp_path / "templates")
    library.seed()
    target = library.use("briefing", output=tmp_path / "new-document")

    assert target.name == "new-document.ssmd.md"
    assert target.read_text(encoding="utf-8") == library.show("briefing")
    with pytest.raises(FileExistsError):
        library.use("briefing", output=target)
    library.use("dialogue", output=target, force=True)
    assert target.read_text(encoding="utf-8") == library.show("dialogue")


def test_template_validation_api_and_validate_all_cli(tmp_path: Path, monkeypatch, capsys) -> None:
    from ssmdstudio.ssmd import ValidationResult

    config_root = tmp_path / "config"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_root))
    library = TemplateLibrary(config_root / "ssmdstudio" / "templates")
    library.seed()
    calls: list[tuple[Path, bool]] = []

    def validate(source: Path, *, roundtrip: bool) -> ValidationResult:
        calls.append((source, roundtrip))
        return ValidationResult(
            source=source,
            state="passed",
            dialect="0.9",
            roundtrip=roundtrip,
            tool_version="0.9.3",
            diagnostics=(),
            returncode=0,
            source_sha256="test-hash",
        )

    monkeypatch.setattr("ssmdstudio.ssmd.check_ssmd", validate)
    result = library.validate("podcast", roundtrip=True)
    assert result.ok is True
    assert calls == [(library.path("podcast"), True)]

    main(["template", "validate", "--all", "--roundtrip", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert [item["source"] for item in payload["templates"]] == [
        str(library.path("briefing")),
        str(library.path("dialogue")),
        str(library.path("podcast")),
    ]
    assert all(item["roundtrip"] is True for item in payload["templates"])


def test_cli_template_and_draft_new_work_without_studio_project(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.chdir(tmp_path)

    main(["template", "reset", "--all"])
    seeded = capsys.readouterr().out.splitlines()
    assert [Path(item).name for item in seeded] == [
        "briefing.ssmd",
        "dialogue.ssmd",
        "podcast.ssmd",
    ]

    main(["template", "list", "--json"])
    listing = json.loads(capsys.readouterr().out)
    assert listing["templates"] == ["briefing", "dialogue", "podcast"]

    main(["draft", "new", "--output", "notes.md"])
    assert (tmp_path / "notes.md").read_text(encoding="utf-8") == ""
    with pytest.raises(SystemExit) as error:
        main(["draft", "new", "--output", "notes.md"])
    assert error.value.code == 2

    main(["draft", "new", "--template", "podcast", "--output", "podcast.ssmd.md"])
    assert (tmp_path / "podcast.ssmd.md").read_text(encoding="utf-8") == TemplateLibrary(
        tmp_path / "config" / "ssmdstudio" / "templates"
    ).show("podcast")


def test_cli_json_errors_emit_one_machine_readable_object(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    config_root = tmp_path / "config"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_root))
    library_root = config_root / "ssmdstudio" / "templates"
    library_root.mkdir(parents=True)
    (library_root / "clash.ssmd").write_text("one", encoding="utf-8")
    (library_root / "clash.ssmd.md").write_text("two", encoding="utf-8")

    with pytest.raises(SystemExit) as error:
        main(["template", "list", "--json"])
    assert error.value.code == 2
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["schema"] == "ssmdstudio.error.v1"
    assert payload["ok"] is False
    assert captured.err == ""
