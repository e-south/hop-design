from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from hop_design.api import create_spec
from hop_design.design.loading import SpecSourceLimitError, load_spec


def test_yaml_and_json_load_to_the_same_strict_spec(tmp_path: Path) -> None:
    spec = create_spec(sequence="NRY", design_id="load-demo")
    payload = spec.model_dump(mode="json", by_alias=True)
    json_path = tmp_path / "design.json"
    yaml_path = tmp_path / "design.yaml"
    json_path.write_text(__import__("json").dumps(payload), encoding="utf-8")
    yaml_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    assert load_spec(json_path) == spec
    assert load_spec(yaml_path) == spec


def test_spec_loader_rejects_unknown_schema_and_extensions(tmp_path: Path) -> None:
    unknown_schema = tmp_path / "unknown.json"
    unknown_extension = tmp_path / "design.txt"
    unknown_schema.write_text('{"schema":"hop.design/v99"}', encoding="utf-8")
    unknown_extension.write_text("irrelevant", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported HOP spec schema"):
        load_spec(unknown_schema)
    with pytest.raises(ValueError, match="extension"):
        load_spec(unknown_extension)


def test_spec_loader_enforces_byte_limit_and_rejects_symlinks(tmp_path: Path) -> None:
    spec = create_spec(sequence="ACGT", design_id="bounded-spec")
    source = tmp_path / "design.json"
    source.write_text(spec.model_dump_json(by_alias=True), encoding="utf-8")

    with pytest.raises(SpecSourceLimitError) as captured:
        load_spec(source, max_bytes=1)
    assert captured.value.actual == source.stat().st_size
    assert captured.value.max_bytes == 1

    linked = tmp_path / "linked.json"
    linked.symlink_to(source)
    with pytest.raises(ValueError, match="symlink"):
        load_spec(linked)
