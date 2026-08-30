"""
--------------------------------------------------------------------------------
HOP Design
tests/contract/test_construction_source.py

Tests strict file-oriented complete-construction source contracts.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from pydantic import ValidationError

from hop_design.design.source_documents import SourceDocumentLimitError, load_source_mapping
from hop_design.models.construction import ConstructionEndpoint
from hop_design.models.construction.source import ConstructionSource
from hop_design.models.junction import Strand
from hop_design.models.molecular_state import EndChemistry
from tests.contract.test_foldback_construction_discovery import (
    _nickase,
    _request,
    _terminus_enzyme,
)
from tests.integration.test_complete_construction_discovery import _basal_result, _material
from tests.integration.test_complete_construction_pcr import _payload


def _source_document() -> dict[str, object]:
    foldback = _request(_nickase(), _terminus_enzyme())
    return {
        "schema": "hop.construction-source/v2",
        "foldback": foldback.model_dump(mode="json", by_alias=True),
        "basal": None,
        "composition": {
            "endpoint": "ssdna_hairpin",
            "materialization": {
                "source_origin": "synthesized",
                "source_five_prime_end": "hydroxyl",
                "source_three_prime_end": "hydroxyl",
                "source_complement_origin": "synthesized",
                "source_complement_five_prime_end": "phosphate",
                "source_complement_three_prime_end": "hydroxyl",
            },
            "whole_route_constraints": {},
            "enumeration": {
                "pruning": "disabled",
                "max_combinations": 100,
                "max_realizations": 100,
            },
        },
    }


def _pcr_source_document() -> dict[str, object]:
    document = _source_document()
    basal = _basal_result(
        _payload(),
        ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
        nick_strand=Strand.BOTTOM,
    )
    document["basal"] = basal.discovery.request.model_dump(mode="json", by_alias=True)
    composition = dict(document["composition"])  # type: ignore[arg-type]
    composition["endpoint"] = "hairpin_pcr_duplex"
    materialization = dict(composition["materialization"])  # type: ignore[arg-type]
    materialization.update(
        {
            "adapter": _material("adapter", "ACGT").model_dump(mode="json"),
            "forward_primer": _material("forward-primer", "GACA").model_dump(mode="json"),
            "reverse_primer": _material("reverse-primer", "TGTC").model_dump(mode="json"),
        }
    )
    composition["materialization"] = materialization
    document["composition"] = composition
    return document


@pytest.mark.parametrize("suffix", [".json", ".yaml"])
def test_construction_source_loads_strict_json_and_yaml(
    tmp_path: Path,
    suffix: str,
) -> None:
    document = _source_document()
    source_path = tmp_path / f"source{suffix}"
    if suffix == ".json":
        source_path.write_text(json.dumps(document), encoding="utf-8")
    else:
        import yaml

        source_path.write_text(yaml.safe_dump(document), encoding="utf-8")

    loaded = ConstructionSource.model_validate_json(
        json.dumps(load_source_mapping(source_path), separators=(",", ":"))
    )

    assert loaded.schema_id == "hop.construction-source/v2"
    assert loaded.composition.endpoint == "ssdna_hairpin"
    assert loaded.composition.materialization.source_complement_five_prime_end is (
        EndChemistry.PHOSPHATE
    )


def test_construction_source_rejects_the_superseded_contract() -> None:
    document = _source_document()
    document["schema"] = "hop.construction-source/v1"

    with pytest.raises(ValidationError, match=r"hop\.construction-source/v2"):
        ConstructionSource.model_validate_json(json.dumps(document))


def test_construction_source_rejects_unknown_or_internal_schema_fields() -> None:
    unknown = _source_document()
    unknown["unexpected"] = True
    with pytest.raises(ValidationError, match="unexpected"):
        ConstructionSource.model_validate_json(json.dumps(unknown))

    internal = _source_document()
    internal["schema_id"] = internal.pop("schema")
    with pytest.raises(ValidationError, match="schema"):
        ConstructionSource.model_validate_json(json.dumps(internal))

    nested = _source_document()
    foldback = dict(nested["foldback"])  # type: ignore[arg-type]
    foldback["schema_id"] = foldback.pop("schema")
    nested["foldback"] = foldback
    with pytest.raises(ValidationError, match="schema"):
        ConstructionSource.model_validate_json(json.dumps(nested))


def test_construction_source_rejects_endpoint_incoherence() -> None:
    direct_with_basal = _source_document()
    direct_with_basal["basal"] = direct_with_basal["foldback"]
    with pytest.raises(ValidationError, match="direct endpoint must omit basal"):
        ConstructionSource.model_validate_json(json.dumps(direct_with_basal))

    direct_with_auxiliary = _source_document()
    composition = dict(direct_with_auxiliary["composition"])  # type: ignore[arg-type]
    materialization = dict(composition["materialization"])  # type: ignore[arg-type]
    materialization["adapter"] = _material("adapter", "ACGT").model_dump(mode="json")
    composition["materialization"] = materialization
    direct_with_auxiliary["composition"] = composition
    with pytest.raises(ValidationError, match="direct endpoint must omit adapter"):
        ConstructionSource.model_validate_json(json.dumps(direct_with_auxiliary))


@pytest.mark.parametrize("missing", ["basal", "adapter", "forward_primer", "reverse_primer"])
def test_construction_source_rejects_incomplete_pcr_inputs(missing: str) -> None:
    document = _pcr_source_document()
    if missing == "basal":
        document["basal"] = None
    else:
        composition = dict(document["composition"])  # type: ignore[arg-type]
        materialization = dict(composition["materialization"])  # type: ignore[arg-type]
        materialization[missing] = None
        composition["materialization"] = materialization
        document["composition"] = composition

    with pytest.raises(ValidationError, match="PCR-bearing endpoints require"):
        ConstructionSource.model_validate_json(json.dumps(document))


def test_construction_source_rejects_local_endpoint_and_payload_drift() -> None:
    wrong_foldback_endpoint = _source_document()
    foldback = dict(wrong_foldback_endpoint["foldback"])  # type: ignore[arg-type]
    foldback["endpoint"] = "hairpin_pcr_duplex"
    wrong_foldback_endpoint["foldback"] = foldback
    with pytest.raises(ValidationError, match="foldback must describe"):
        ConstructionSource.model_validate_json(json.dumps(wrong_foldback_endpoint))

    wrong_basal_endpoint = _pcr_source_document()
    composition = dict(wrong_basal_endpoint["composition"])  # type: ignore[arg-type]
    composition["endpoint"] = "clone_ready_duplex"
    wrong_basal_endpoint["composition"] = composition
    with pytest.raises(ValidationError, match="Basal discovery must match"):
        ConstructionSource.model_validate_json(json.dumps(wrong_basal_endpoint))

    wrong_payload = _pcr_source_document()
    basal = dict(wrong_payload["basal"])  # type: ignore[arg-type]
    payload = dict(basal["payload"])  # type: ignore[arg-type]
    exact = dict(payload["payload"])  # type: ignore[arg-type]
    exact["sequence"] = "GACT"
    payload["payload"] = exact
    basal["payload"] = payload
    wrong_payload["basal"] = basal
    with pytest.raises(ValidationError, match="same payload space"):
        ConstructionSource.model_validate_json(json.dumps(wrong_payload))


def test_construction_source_loader_rejects_unsafe_or_unsupported_documents(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.json"
    source.write_text(json.dumps(_source_document()), encoding="utf-8")
    link = tmp_path / "linked.json"
    link.symlink_to(source)
    with pytest.raises(ValueError, match="must not be a symlink"):
        load_source_mapping(link)

    oversized = tmp_path / "oversized.json"
    oversized.write_bytes(b"x" * 33)
    with pytest.raises(SourceDocumentLimitError):
        load_source_mapping(oversized, max_bytes=32)

    sequence = tmp_path / "sequence.json"
    sequence.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="root must be a mapping"):
        load_source_mapping(sequence)

    unsupported = tmp_path / "source.txt"
    unsupported.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="extension"):
        load_source_mapping(unsupported)


@pytest.mark.parametrize(
    ("suffix", "content"),
    [
        (".json", '{"schema":"first","schema":"second"}'),
        (".json", '{"outer":{"value":1,"value":2}}'),
        (".yaml", "schema: first\nschema: second\n"),
        (".yaml", "outer:\n  value: 1\n  value: 2\n"),
    ],
)
def test_source_loader_rejects_duplicate_mapping_keys(
    tmp_path: Path,
    suffix: str,
    content: str,
) -> None:
    source = tmp_path / f"duplicate{suffix}"
    source.write_text(content, encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate mapping key"):
        load_source_mapping(source)


@pytest.mark.parametrize(
    "content",
    [
        '1: numeric\n"1": text\n',
        "outer:\n  1: numeric\n",
    ],
)
def test_source_loader_rejects_non_string_yaml_mapping_keys(
    tmp_path: Path,
    content: str,
) -> None:
    source = tmp_path / "non-string-key.yaml"
    source.write_text(content, encoding="utf-8")

    with pytest.raises(ValueError, match="mapping keys must be strings"):
        load_source_mapping(source)


def test_source_loader_rejects_yaml_alias_expansion(tmp_path: Path) -> None:
    source = tmp_path / "aliases.yaml"
    source.write_text(
        "base: &base [A, C, G, T]\n"
        "level_1: &level_1 [*base, *base, *base, *base]\n"
        "level_2: [*level_1, *level_1, *level_1, *level_1]\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="aliases, anchors, or merge keys"):
        load_source_mapping(source)


def test_source_loader_rejects_path_replacement_during_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source.json"
    source.write_text('{"schema":"safe"}', encoding="utf-8")
    replacement = tmp_path / "replacement.json"
    replacement.write_text('{"schema":"replacement"}', encoding="utf-8")
    original_lstat = os.lstat
    replaced = False

    def replace_before_lstat(path: str | bytes | os.PathLike[str] | os.PathLike[bytes]):
        nonlocal replaced
        if Path(path) == source and not replaced:
            replaced = True
            os.replace(replacement, source)
        return original_lstat(path)

    monkeypatch.setattr(os, "lstat", replace_before_lstat)

    with pytest.raises(ValueError, match="changed while it was being opened"):
        load_source_mapping(source)
