"""Frozen coordinates preserve preparation multiplicity and filtering context."""

import json

import pytest

from hop_design.design.construction.navigation.similarity_layout import build_molecular_landscape
from hop_design.models.construction.variants.landscape import MolecularLandscape
from hop_design.serialization import canonical_json_bytes
from tests.unit.test_molecular_similarity import molecule

SNAPSHOT = "sha256:" + "a" * 64


@pytest.fixture
def recorded_landscape(tmp_path):
    """Exercise real checked reads without compiling unrelated molecular routes."""
    from types import SimpleNamespace

    from hop_design.design.construction.editions.reader import AtlasEdition
    from hop_design.design.construction.editions.storage import EditionStore
    from hop_design.export.publication import ProtectedRoot
    from hop_design.serialization import sha256_digest

    model = build_molecular_landscape((molecule(),), snapshot_digest=SNAPSHOT)
    raw = json.dumps(model.model_dump(mode="json", by_alias=True), indent=3).encode()
    target = tmp_path / "landscape.json"
    target.write_bytes(raw)
    store = object.__new__(EditionStore)
    store.root = ProtectedRoot.capture(tmp_path)
    store.manifest = SimpleNamespace(
        artifacts={"landscape.json": SimpleNamespace(bytes=len(raw), sha256=sha256_digest(raw))}
    )
    edition = object.__new__(AtlasEdition)
    edition._store = store
    answer = {
        "snapshot_digest": SNAPSHOT,
        "paths": [{"materialized_realization_id": molecule().identity, "matches": False}],
    }
    return edition, answer, model, target


def test_saved_landscape_digest_reuses_admission_but_checks_bytes_each_time(
    recorded_landscape, monkeypatch
):
    from hop_design.design.construction.navigation.landscape_source import landscape_digest

    edition, answer, model, target = recorded_landscape
    reads, validations = [], []
    read, validate = edition._store.read, MolecularLandscape.model_validate_json

    def counted_read(name):
        reads.append(name)
        return read(name)

    def counted_validate(cls, raw, **kwargs):
        validations.append(raw)
        return validate(raw, **kwargs)

    monkeypatch.setattr(edition._store, "read", counted_read)
    monkeypatch.setattr(MolecularLandscape, "model_validate_json", classmethod(counted_validate))
    for _ in range(3):
        assert landscape_digest(edition, answer=answer) == model.digest
    assert reads == ["landscape.json"] * 3
    assert len(validations) == 1
    reopened = object.__new__(type(edition))
    reopened._store = edition._store
    assert landscape_digest(reopened, answer=answer) == model.digest
    assert len(validations) == 2, "Admission belongs to one edition object"
    # Formatting is not semantic identity; never substitute the raw artifact hash.
    assert model.digest != edition._store.manifest.artifacts["landscape.json"].sha256
    raw = target.read_bytes()
    target.write_bytes(raw.replace(b'"coincident"', b'"classicaL" '))
    assert target.stat().st_size == len(raw)
    with pytest.raises(ValueError, match="digest disagrees"):
        landscape_digest(edition, answer=answer)


def test_saved_landscape_admission_keeps_snapshot_membership_and_mutation_boundaries(
    recorded_landscape,
):
    from hop_design.design.construction.navigation.landscape_source import (
        landscape_digest,
        molecular_landscape,
    )

    edition, answer, model, target = recorded_landscape
    bad = [{**answer, "snapshot_digest": "sha256:" + "b" * 64}, {**answer, "paths": []}]
    for changed in bad:
        with pytest.raises(ValueError, match="snapshot"):
            landscape_digest(edition, answer=changed)
    assert getattr(edition, "_landscape_admission", None) is None
    expected = landscape_digest(edition, answer=answer)
    for changed in bad:
        with pytest.raises(ValueError, match="snapshot"):
            landscape_digest(edition, answer=changed)
    public = molecular_landscape(edition, answer=answer)
    public.versions["injected"] = "different"
    assert landscape_digest(edition, answer=answer) == expected == model.digest
    assert "injected" not in molecular_landscape(edition, answer=answer).versions
    raw = target.read_bytes()
    other = target.with_suffix(".copy")
    other.write_bytes(raw)
    target.unlink()
    target.symlink_to(other)
    with pytest.raises(ValueError, match="symlink"):
        landscape_digest(edition, answer=answer)


def test_opening_map_admits_coordinates_once_for_first_pin(recorded_landscape, monkeypatch):
    from hop_design.design.construction.navigation.inspection_projection import map_index
    from hop_design.design.construction.navigation.landscape_source import landscape_digest

    edition, answer, model, target = recorded_landscape
    reads, validations = [], []
    read, validate = edition._store.read, MolecularLandscape.model_validate_json

    def counted_read(name):
        reads.append(name)
        return read(name)

    def counted_validate(cls, raw, **kwargs):
        validations.append(raw)
        return validate(raw, **kwargs)

    monkeypatch.setattr(edition._store, "read", counted_read)
    monkeypatch.setattr(MolecularLandscape, "model_validate_json", classmethod(counted_validate))
    mapped = map_index(edition, answer)
    assert len(mapped["points"]) == 1
    assert landscape_digest(edition, answer=answer) == model.digest
    assert len(validations) == 1, "Pinning must reuse the map's completed admission"
    assert reads == ["landscape.json"] * 2, "Each operation must check its current bytes"
    raw = target.read_bytes()
    target.write_bytes(raw.replace(b'"coincident"', b'"classicaL" '))
    with pytest.raises(ValueError, match="digest disagrees"):
        landscape_digest(edition, answer=answer)


@pytest.mark.parametrize("change", ["snapshot", "membership"])
def test_invalid_map_never_leaves_a_successful_admission(recorded_landscape, change):
    from hop_design.design.construction.navigation.inspection_projection import map_index

    edition, answer, _, _ = recorded_landscape
    invalid = (
        {**answer, "snapshot_digest": "sha256:" + "b" * 64}
        if change == "snapshot"
        else {**answer, "paths": []}
    )
    with pytest.raises(ValueError, match="snapshot"):
        map_index(edition, invalid)
    assert getattr(edition, "_landscape_admission", None) is None


def test_coincident_preparations_remain_individual_and_use_no_embedding(monkeypatch):
    import sys

    monkeypatch.setitem(sys.modules, "umap", None)
    a, b = molecule(), molecule(identity="another-route")
    result = build_molecular_landscape((a, b), snapshot_digest=SNAPSHOT)
    assert result.algorithm == "coincident"
    assert len(result.preparations) == 2 and len(result.coordinates) == 1
    assert result.coordinates[0].x == result.coordinates[0].y == 0
    assert result == build_molecular_landscape((b, a), snapshot_digest=SNAPSHOT)
    assert MolecularLandscape.model_validate_json(canonical_json_bytes(result)) == result


def test_saved_coordinates_reject_omitted_stale_and_nonfinite_members():
    result = build_molecular_landscape((molecule(),), snapshot_digest=SNAPSHOT)
    raw = result.model_dump(mode="json", by_alias=True)
    raw["coordinates"] = []
    with pytest.raises(ValueError, match="coordinate"):
        MolecularLandscape.model_validate_json(canonical_json_bytes(raw))
    raw = result.model_dump(mode="json", by_alias=True)
    raw["coordinates"][0]["x"] = float("nan")
    with pytest.raises(ValueError, match="finite"):
        MolecularLandscape.model_validate_json(json.dumps(raw))
    raw = result.model_dump(mode="json", by_alias=True)
    raw["preparations"][0]["shape"]["loop_nt"] += 1
    with pytest.raises(ValueError):
        MolecularLandscape.model_validate_json(canonical_json_bytes(raw))


def test_small_pool_coordinates_are_deterministic_and_full_pool_is_bounded():
    pytest.importorskip("numpy")
    rows = (molecule(), molecule(identity="b", loop="AAAC"), molecule(identity="c", end="AGTT"))
    first = build_molecular_landscape(rows, snapshot_digest=SNAPSHOT)
    assert first.algorithm == "classical_mds"
    assert first == build_molecular_landscape(rows[::-1], snapshot_digest=SNAPSHOT)
    assert len({(c.x, c.y) for c in first.coordinates}) == 3
    with pytest.raises(ValueError, match="distinct preparations"):
        build_molecular_landscape((rows[0], rows[0]), snapshot_digest=SNAPSHOT)


def test_umap_is_reproducible_and_does_not_add_or_drop_preparations():
    pytest.importorskip("umap")
    rows = tuple(
        molecule(identity=str(i), loop=word)
        for i, word in enumerate(("AAAA", "AAAC", "AACA", "ACAA", "CAAA"))
    )
    first = build_molecular_landscape(rows, snapshot_digest=SNAPSHOT)
    second = build_molecular_landscape(rows[::-1], snapshot_digest=SNAPSHOT)
    assert first == second
    assert first.algorithm == "umap"
    assert first.versions["umap-learn"]
    assert {r.identity for r in first.preparations} == {r.identity for r in rows}


def test_molecular_plot_exposes_every_preparation_and_keeps_raw_positions():
    from xml.etree import ElementTree as ET

    from hop_design.export.construction.survey.similarity import render_molecular_landscape

    a, b = molecule(), molecule(identity="another-route")
    landscape = build_molecular_landscape((a, b), snapshot_digest=SNAPSHOT)
    tree = ET.fromstring(
        render_molecular_landscape(landscape, eligible={a.identity}, selected_identity=a.identity)
    )
    marks = [e for e in tree.iter() if "data-preparation" in e.attrib]
    assert len(marks) == 2
    assert {e.attrib["data-preparation"] for e in marks} == {a.identity, b.identity}
    assert len({(e.attrib["data-molecular-x"], e.attrib["data-molecular-y"]) for e in marks}) == 1
    assert {e.attrib["data-eligible"] for e in marks} == {"true", "false"}
    assert all(e.attrib["tabindex"] == "0" for e in marks)


def test_map_fit_frame_contains_complete_marks_without_changing_molecular_coordinates():
    from xml.etree import ElementTree as ET

    from hop_design.export.construction.survey.similarity import render_molecular_landscape

    rows = (molecule(), molecule(identity="another-route"))
    landscape = build_molecular_landscape(rows, snapshot_digest=SNAPSHOT)
    tree = ET.fromstring(render_molecular_landscape(landscape, eligible={r.identity for r in rows}))
    x, y, width, height = map(float, tree.attrib["data-map-frame"].split())
    assert 0 < width < 1200 and 0 < height < 480
    for mark in tree.iter():
        if mark.get("data-preparation"):
            circle = next(e for e in mark if e.tag.endswith("}circle"))
            cx, cy, radius = (float(circle.attrib[k]) for k in ("cx", "cy", "r"))
            assert x < cx - radius < cx + radius < x + width
            assert y < cy - radius < cy + radius < y + height
            assert float(mark.attrib["data-molecular-x"]) == 0
            assert float(mark.attrib["data-molecular-y"]) == 0
    assert len([e for e in tree.iter() if e.get("data-map-context")]) == 2
