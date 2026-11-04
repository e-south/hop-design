"""A read-only preview reuses admitted choices and still checks selected authority."""

import copy
import json
from xml.etree import ElementTree as ET

import pytest
from pydantic import ValidationError

from hop_design.api import _InspectionProjection
from hop_design.export.construction.molecular.teaching_overview import render_teaching_overview
from hop_design.export.construction.presentation.figure_profile import INSPECTOR_FIGURE
from hop_design.models.construction.projections.atlas import MolecularAtlas
from tests.integration.test_atlas_edition import captured_choices as captured_choices


def test_compact_hover_reuses_admitted_context_without_requerying_or_selecting(
    captured_choices, tmp_path, monkeypatch
):
    edition = captured_choices.freeze(tmp_path / "edition", compact=True)
    answer = edition.query()
    identity = answer["paths"][0]["materialized_realization_id"]
    public = edition.preview(identity)
    atlas = json.loads(edition.atlas(edition.select(identity)).json_bytes)
    expected = render_teaching_overview(atlas, profile=INSPECTOR_FIGURE)
    cost = atlas["atlas"]["construction_cost"]
    assert json.loads(public.json_bytes)["construction_cost"] == cost
    malformed = copy.deepcopy(atlas)
    malformed["atlas"]["states"] = []
    with pytest.raises(ValidationError):
        render_teaching_overview(malformed)
    incomplete = copy.deepcopy(atlas)
    incomplete["atlas"].pop("transitions")
    with pytest.raises(ValidationError):
        render_teaching_overview(incomplete)
    malformed = copy.deepcopy(atlas)
    malformed["teaching"]["materialized_realization_id"] = "another-preparation"
    with pytest.raises(ValueError, match="same preparation"):
        render_teaching_overview(malformed)

    def forbidden(*args, **kwargs):
        pytest.fail("Admitted hover must not requery the whole cohort or create a selection")

    monkeypatch.setattr(edition, "query", forbidden)
    monkeypatch.setattr(edition, "select", forbidden)

    def unused_transitions(*args, **kwargs):
        pytest.fail("A teaching preview must not calculate unused processing correspondences")

    monkeypatch.setattr(
        "hop_design.design.construction.projections.atlas.inspection_correspondence",
        unused_transitions,
    )
    from hop_design.design.construction.projections import atlas as projection

    inspected_states = []
    inspect_state = projection.project_molecular_inspection

    def counted_state(route, state_id, *args, **kwargs):
        inspected_states.append(state_id)
        return inspect_state(route, state_id, *args, **kwargs)

    monkeypatch.setattr(projection, "project_molecular_inspection", counted_state)
    serialized_atlas_reads = []
    validate_atlas = MolecularAtlas.model_validate_json

    def counted_atlas_read(cls, data, **kwargs):
        serialized_atlas_reads.append(len(data))
        return validate_atlas(data, **kwargs)

    monkeypatch.setattr(MolecularAtlas, "model_validate_json", classmethod(counted_atlas_read))
    actual, summary = _InspectionProjection.preview(edition, identity, answer)
    assert actual == expected
    # This complete route has eleven states, but its teaching view needs only
    # the source duplex, association, hairpin, release precursor and product.
    # Full-atlas equality above protects the bases, footprints, cuts and labels.
    assert len(atlas["atlas"]["states"]) == 11
    assert len(inspected_states) == 5
    # The authority is checked above the projection. Drawing that typed result
    # must not serialize and admit the entire atlas a second time for one hairpin.
    assert serialized_atlas_reads == []

    def bases(svg):
        return [
            (e.get("data-state-id"), e.get("data-strand-id"), e.get("data-base-index"), e.text)
            for e in ET.fromstring(svg).iter()
            if e.get("data-base-index") is not None
        ]

    # Publication and inspection compose the same exact molecular content.
    assert bases(actual) and bases(actual) == bases(dict(public._files)["overview.svg"])
    assert summary["materialized_realization_id"] == identity
    assert summary["path"] == answer["paths"][0]
    assert summary["construction_cost"] == cost
    with pytest.raises(ValueError, match="recorded pool"):
        _InspectionProjection.preview(edition, "not-a-preparation", answer)
    foreign = copy.deepcopy(answer)
    foreign["snapshot_digest"] = "0" * 64
    with pytest.raises(ValueError, match="snapshot"):
        _InspectionProjection.preview(edition, identity, foreign)

    # Reusing the admitted query never licenses changed molecular authority bytes.
    archive = edition._directory / edition._prefix(identity) / "evidence.zip"
    raw = archive.read_bytes()
    archive.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
    with pytest.raises(ValueError, match="digest"):
        _InspectionProjection.preview(edition, identity, answer)
