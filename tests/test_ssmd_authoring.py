from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

ssmd = pytest.importorskip("ssmd")

from ssmdstudio.cli import main
from ssmdstudio.ssmd import materialize_voice_bindings

FIXTURES = Path(__file__).parent / "fixtures" / "authoring"


def test_binding_roundtrip_preserves_metadata_other_providers_and_body(tmp_path: Path) -> None:
    source = FIXTURES / "binding-preservation.ssmd.md"
    output = tmp_path / "bound.ssmd.md"

    result = materialize_voice_bindings(
        source,
        {"narrator": "replacement-voice", "analyst": "another-id"},
        provider="kokoro",
        output=output,
    )

    content = output.read_text(encoding="utf-8")
    header = ssmd.parse_front_matter(content).data
    original = ssmd.parse_front_matter(source.read_text(encoding="utf-8")).data
    assert header["ssmd_version"] == original["ssmd_version"]
    assert header["title"] == original["title"]
    assert header["custom_metadata"] == original["custom_metadata"]
    assert header["voice_bindings"]["another-provider"] == {"narrator": "keep-this-voice"}
    assert header["voice_bindings"]["kokoro"] == {
        "narrator": "replacement-voice",
        "analyst": "another-id",
    }
    assert content.endswith(
        "# A deliberately preserved body\n\n"
        ':::{voice="narrator"}\n'
        "Hello from Montréal — keep this body exactly as written.\n"
        ":::\n"
    )
    assert result.output == output.resolve()
    assert result.provider == "kokoro"
    assert result.bindings == {"narrator": "replacement-voice", "analyst": "another-id"}
    assert result.to_dict()["schema"] == "ssmdstudio.binding.v1"


def test_binding_preserves_crlf_and_leading_body_blank_lines(tmp_path: Path) -> None:
    body = '\r\n\r\n:::{voice="host"}\r\nCafé.\r\n:::\r\n'
    source = tmp_path / "episode.ssmd"
    source.write_bytes(("---\r\nssmd_version: '0.9'\r\n---\r\n" + body).encode("utf-8"))

    result = materialize_voice_bindings(source, {"host": "id-1"}, provider="piper")
    output_text = result.output.read_bytes().decode("utf-8")

    assert result.output.name == "episode.bound.ssmd.md"
    assert output_text.startswith("---\nssmd_version: '0.9'\nvoice_bindings:")
    assert output_text.endswith(body)


def test_unversioned_input_gets_ssmd_09_and_double_suffix_default_is_deterministic(
    tmp_path: Path,
) -> None:
    source = tmp_path / "episode.ssmd.md"
    source.write_text(':::{voice="host"}\nHello.\n:::\n', encoding="utf-8")

    result = materialize_voice_bindings(source, {"host": "voice-a"}, provider="piper")

    assert result.output.name == "episode.bound.ssmd.md"
    header = ssmd.parse_front_matter(result.output.read_text(encoding="utf-8")).data
    assert header["ssmd_version"] == "0.9"
    assert header["voice_bindings"] == {"piper": {"host": "voice-a"}}


def test_binding_rejects_empty_invalid_and_conflicting_requests(tmp_path: Path) -> None:
    source = tmp_path / "source.ssmd.md"
    source.write_text("Text.\n", encoding="utf-8")

    invalid = (
        ({}, "kokoro"),
        ({"": "voice"}, "kokoro"),
        ({"host": ""}, "kokoro"),
        ({"host": " voice "}, "kokoro"),
        ({"host role": "voice"}, "kokoro"),
        ({"host": "voice"}, "../unsafe"),
    )
    for bindings, provider in invalid:
        with pytest.raises(ValueError):
            materialize_voice_bindings(source, bindings, provider=provider)

    class ConflictingBindings(dict[str, str]):
        def items(self):
            return [("host", "one"), ("host", "two")]

    with pytest.raises(ValueError, match="conflicting"):
        materialize_voice_bindings(source, ConflictingBindings(), provider="kokoro")


def test_binding_rejects_missing_source_wrong_suffix_and_output_conflicts(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="suffix"):
        materialize_voice_bindings(tmp_path / "wrong.txt", {"host": "id"}, provider="kokoro")
    with pytest.raises(FileNotFoundError):
        materialize_voice_bindings(tmp_path / "missing.ssmd", {"host": "id"}, provider="kokoro")

    source = tmp_path / "source.ssmd"
    source.write_text("Body.\n", encoding="utf-8")
    with pytest.raises(ValueError, match="cannot be combined"):
        materialize_voice_bindings(
            source,
            {"host": "id"},
            provider="kokoro",
            output=source,
            in_place=True,
        )
    with pytest.raises(ValueError, match="use in_place"):
        materialize_voice_bindings(source, {"host": "id"}, provider="kokoro", output=source)

    target = tmp_path / "existing.ssmd.md"
    target.write_text("keep\n", encoding="utf-8")
    with pytest.raises(FileExistsError, match="force"):
        materialize_voice_bindings(source, {"host": "id"}, provider="kokoro", output=target)
    assert target.read_text(encoding="utf-8") == "keep\n"


def test_invalid_source_and_atomic_failure_preserve_in_place_content(
    tmp_path: Path, monkeypatch
) -> None:
    invalid = tmp_path / "invalid.ssmd"
    invalid.write_bytes((FIXTURES / "legacy-div.ssmd").read_bytes())
    original = invalid.read_bytes()
    with pytest.raises(ValueError, match="invalid SSMD source"):
        materialize_voice_bindings(invalid, {"narrator": "id"}, provider="kokoro", in_place=True)
    assert invalid.read_bytes() == original

    valid = tmp_path / "valid.ssmd"
    valid.write_text('---\nssmd_version: "0.9"\n---\nText.\n', encoding="utf-8")
    original = valid.read_bytes()

    def fail_replace(_source: os.PathLike[str] | str, _target: os.PathLike[str] | str) -> None:
        raise OSError("simulated atomic replacement failure")

    monkeypatch.setattr("ssmdstudio.ssmd.os.replace", fail_replace)
    with pytest.raises(OSError, match="simulated"):
        materialize_voice_bindings(valid, {"host": "id"}, provider="kokoro", in_place=True)
    assert valid.read_bytes() == original
    assert not list(tmp_path.glob(".valid.ssmd.*"))


def test_cli_binding_emits_json_and_rejects_contradictory_duplicate_roles(
    tmp_path: Path, capsys
) -> None:
    source = tmp_path / "talk.ssmd.md"
    source.write_text(':::{voice="host"}\nHello.\n:::\n', encoding="utf-8")
    output = tmp_path / "talk.bound.ssmd.md"

    main(
        [
            "ssmd",
            "bind",
            str(source),
            "--provider",
            "kokoro",
            "--voice-bind",
            "host=voice-one",
            "--voice-bind",
            "guest=voice-two",
            "--output",
            str(output),
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema"] == "ssmdstudio.binding.v1"
    assert payload["output"] == str(output.resolve())
    assert payload["bindings"] == {"host": "voice-one", "guest": "voice-two"}

    with pytest.raises(SystemExit) as error:
        main(
            [
                "ssmd",
                "bind",
                str(source),
                "--provider",
                "kokoro",
                "--voice-bind",
                "host=one",
                "--voice-bind",
                "host=two",
                "--output",
                str(tmp_path / "other.ssmd.md"),
                "--json",
            ]
        )
    assert error.value.code == 2
    error_payload = json.loads(capsys.readouterr().out)
    assert error_payload["ok"] is False
