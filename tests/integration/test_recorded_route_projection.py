"""Rendering an already verified route does not recompile it or invent endpoint evidence."""

from types import SimpleNamespace
from xml.etree import ElementTree as ET

import pytest

from hop_design.design.construction.projections.atlas import (
    project_molecular_atlas,
    project_recorded_molecular_atlas,
)


def test_recorded_projection_preserves_every_occurrence_without_compiler_admission(loop_pool):
    route = loop_pool._routes[0][1]
    view = SimpleNamespace(
        **{
            key: getattr(route, key)
            for key in (
                "materialized_realization_id",
                "source_preparation",
                "construction_program",
                "payload_source_map",
                "material_uses",
                "foldback_authority",
                "basal_authority",
                "design",
                "final_product",
            )
        }
    )
    expected = project_molecular_atlas(route).model_dump(exclude={"construction_cost"})
    actual = project_recorded_molecular_atlas(view)
    assert actual.model_dump(exclude={"construction_cost"}) == expected
    assert actual.construction_cost is None
    assert len(actual.states) == 11
    assert len(actual.inputs) == 5
    assert actual.materialized_realization_id == route.materialized_realization_id


def test_operation_labels_keep_all_site_footprints_and_all_bases(loop_pool):
    from hop_design.export.construction.molecular.atlas import render_molecular_atlas

    atlas = project_molecular_atlas(loop_pool._routes[0][1])
    full = ET.fromstring(render_molecular_atlas(atlas))
    compact = ET.fromstring(render_molecular_atlas(atlas, site_labels="operations"))
    for attr in ("data-occurrence", "data-site-id", "data-cut"):
        assert [e.get(attr) for e in compact.iter() if e.get(attr)] == [
            e.get(attr) for e in full.iter() if e.get(attr)
        ]
    inactive = [
        g for g in compact.iter() if g.get("data-site-id") and not g.get("data-operation-timing")
    ]
    assert inactive
    assert all(not any(e.tag.endswith("}text") for e in g.iter()) for g in inactive)
    assert all(any(e.tag.endswith("}title") for e in g.iter()) for g in inactive)


@pytest.mark.parametrize("presentation", ["complete", "assembly"])
def test_route_draws_recorded_chemistry_and_formed_bonds(loop_pool, presentation):
    from hop_design.export.construction.molecular.atlas import render_molecular_atlas

    atlas = project_molecular_atlas(loop_pool._routes[0][1])
    svg = ET.fromstring(
        render_molecular_atlas(atlas, site_labels="operations", presentation=presentation)
    )
    joins = [e for e in svg.iter() if e.get("data-formed-bond")]
    assert len(joins) == sum(len(s.state.formed_bonds) for s in atlas.states)
    for state in atlas.states:
        assert len(state.formed_bond_boundaries) == len(state.state.formed_bonds)
        for boundary in state.formed_bond_boundaries:
            assert boundary.before.strand_id == boundary.after.strand_id
            assert boundary.after.index == boundary.before.index + 1
    inputs = {}
    for element in svg.iter():
        use_id = (
            element.get("data-atlas-input")
            or element.get("data-primer-binding")
            or element.get("data-staged-material")
        )
        if use_id:
            assert use_id not in inputs, "An input must not be duplicated as a glyph and list."
            inputs[use_id] = element
    assert set(inputs) == {item.material_use.use_id for item in atlas.inputs}
    for item in atlas.inputs:
        text = " ".join(inputs[item.material_use.use_id].itertext())
        bases = [
            e.text
            for e in inputs[item.material_use.use_id].iter()
            if e.get("data-input-base-index") is not None
        ]
        if bases:
            assert "".join(bases) == item.material.sequence_5prime
        else:
            assert item.material.sequence_5prime in text
        assert (
            "5\u2032P" if item.material.five_prime_end.value == "phosphate" else "5\u2032OH"
        ) in text
        assert "3\u2032OH" in text
    assert "enzyme phase" not in " ".join(svg.itertext())
    assert "end generation" not in " ".join(svg.itertext())
