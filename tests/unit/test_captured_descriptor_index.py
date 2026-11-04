"""Batch admission keeps strict rows, edition scope and detached inspection values."""

import json
from types import SimpleNamespace

import pytest

from hop_design.design.construction.editions.descriptors import CapturedDescriptors
from hop_design.models.construction.editions.descriptors import CapturedDescriptorIndex
from tests.unit.test_molecular_similarity import molecule


def index_fixture():
    row = molecule()
    snapshot = "sha256:" + "a" * 64
    raw = {
        "schema": "hop.molecular-descriptor-index/v1",
        "snapshot_digest": snapshot,
        "preparations": [row.model_dump(mode="json")],
    }
    edition = SimpleNamespace(
        _store=SimpleNamespace(
            manifest=SimpleNamespace(
                snapshot_digest=snapshot,
                members=[SimpleNamespace(materialized_realization_id=row.identity)],
            )
        ),
        resolution={"intent": {"product": "released_insert", "stem_arm": row.stem}},
    )
    return raw, edition, row


def test_batch_index_retains_exact_molecular_values_and_detaches_copies():
    raw, edition, row = index_fixture()
    encoded = json.dumps(raw)
    assert CapturedDescriptorIndex.model_validate_json(encoded).preparations == (row,)
    captured = CapturedDescriptors(encoded.encode(), edition)
    changed = captured.get(row.identity)
    changed.shape.clear()
    changed.sequences.clear()
    changed.interfaces.clear()
    assert captured.all() == (row,)


@pytest.mark.parametrize("corruption", ["schema", "extra", "alias", "shape", "bases"])
def test_batch_index_rejects_invalid_envelope_or_molecular_row(corruption):
    raw, edition, _ = index_fixture()
    if corruption == "schema":
        raw["schema"] = "hop.molecular-descriptor-index/v0"
    elif corruption == "extra":
        raw["extra"] = True
    elif corruption == "alias":
        raw["schema_id"] = raw.pop("schema")
    elif corruption == "shape":
        raw["preparations"][0]["shape"]["loop_nt"] += 1
    else:
        raw["preparations"][0]["sequences"]["loop"][0] = "N"
    with pytest.raises(ValueError):
        CapturedDescriptors(json.dumps(raw).encode(), edition)


@pytest.mark.parametrize("corruption", ["snapshot", "identity", "duplicate", "stem", "endpoint"])
def test_batch_index_keeps_edition_membership_and_scope_checks(corruption):
    raw, edition, _ = index_fixture()
    if corruption == "snapshot":
        raw["snapshot_digest"] = "sha256:" + "b" * 64
    elif corruption == "identity":
        raw["preparations"][0]["identity"] = "foreign"
    elif corruption == "duplicate":
        raw["preparations"] *= 2
    elif corruption == "stem":
        edition.resolution["intent"]["stem_arm"] = "TTTTTTTTTTTTTTTTTTTT"
    else:
        edition.resolution["intent"]["product"] = "hairpin"
    with pytest.raises(ValueError, match=r"snapshot|membership|scope"):
        CapturedDescriptors(json.dumps(raw).encode(), edition)
