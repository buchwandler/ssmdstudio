from __future__ import annotations

from pathlib import Path

import pytest

from ssmdstudio.store import load_yaml


def test_load_yaml_requires_a_mapping_root(tmp_path: Path) -> None:
    source = tmp_path / "invalid.yaml"
    source.write_text("- item\n", encoding="utf-8")

    with pytest.raises(TypeError, match="expected a YAML mapping"):
        load_yaml(source)
