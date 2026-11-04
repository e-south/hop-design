"""Assembly composition keeps the complete authority beneath a shorter drawing."""

import json
from xml.etree import ElementTree as ET

import pytest

from hop_design import construction
from hop_design.export.construction.molecular.atlas import render_molecular_atlas
from hop_design.models.construction.projections.atlas import MolecularAtlas
from tests.integration.test_molecular_atlas import atlas_request


@pytest.fixture(scope="module")
def atlas(loop_pool):
    choices, request = atlas_request(loop_pool)
    packet = construction.inspect_scaffold_atlas(loop_pool, choices, request)
    return MolecularAtlas.model_validate_json(json.dumps(json.loads(packet.json_bytes)["atlas"]))


def test_assembly_view_collapses_cleanup_without_changing_the_record(atlas):
    before = atlas.model_dump_json()
    root = ET.fromstring(render_molecular_atlas(atlas, presentation="assembly"))
    rows = [e for e in root.iter() if e.get("data-atlas-state")]
    assert [r.get("data-atlas-phase") for r in rows] == [
        "source_ssdna",
        "duplex",
        "cleaved_duplex",
        "annealed_complex",
        "foldback_closed_hairpin",
        "adapter_annealed",
        "adapter_ligated",
        "hairpin_pcr_duplex",
        "clone_ready_duplex",
    ]
    assert [int(r.get("data-atlas-order")) for r in rows] == list(range(9))
    assert "Heat · cleanup · reanneal" in "".join(rows[2].itertext())
    assert "Retained and annealed" in "".join(rows[3].itertext())
    assert json.loads(rows[2].get("data-transition-ids")) == [
        t.authority_id for t in atlas.transitions[2:5]
    ]
    assert root.get("data-recorded-state-count") == "11"
    assert atlas.model_dump_json() == before
    complete = ET.fromstring(render_molecular_atlas(atlas))
    assert len([e for e in complete.iter() if e.get("data-atlas-state")]) == 11


def _base_points(root, state):
    elements = {
        (e.get("data-strand-id"), int(e.get("data-base-index"))): e
        for e in root.iter()
        if e.get("data-state-id") == state.state.state_id and e.get("data-base-index") is not None
    }
    result = {}
    for b in state.bases:
        element = elements[b.address.strand_id, b.address.index]
        rect = next(e for e in element if e.tag.endswith("}rect"))
        text = next(e for e in element if e.tag.endswith("}text"))
        result[b.origin.origin_id, b.origin.origin_strand, b.origin.origin_index] = (
            float(rect.get("x")) + float(rect.get("width")) / 2,
            float(text.get("y")) - 5,
        )
    return result


def test_assembly_holds_shared_bases_in_register_and_preserves_contacts(atlas):
    root = ET.fromstring(render_molecular_atlas(atlas, presentation="assembly"))
    stages = [
        s
        for s in atlas.states
        if s.state.phase.value
        in {"annealed_complex", "foldback_closed_hairpin", "adapter_annealed", "adapter_ligated"}
    ]
    frame = _base_points(root, stages[-1])
    for state in stages:
        assert _base_points(root, state) == {k: frame[k] for k in _base_points(root, state)}
        row = next(e for e in root.iter() if e.get("data-atlas-state") == state.state.state_id)
        assert len([e for e in row.iter() if e.get("data-edge-kind") == "pair"]) == len(
            state.state.pairings
        )


def test_assembly_inputs_are_complete_but_not_incorporated_bases(atlas):
    root = ET.fromstring(render_molecular_atlas(atlas, presentation="assembly"))
    staged = [e for e in root.iter() if e.get("data-staged-material")]
    assert {g.get("data-staged-material") for g in staged} == {
        i.material_use.use_id for i in atlas.inputs if i.binding_state_id != i.pre_state_id
    }
    for glyph in staged:
        item = next(
            i for i in atlas.inputs if i.material_use.use_id == glyph.get("data-staged-material")
        )
        assert (
            "".join(e.text for e in glyph.iter() if e.get("data-input-base-index") is not None)
            == item.material.sequence_5prime
        )
        assert not any(
            e.get("data-base-index") is not None or e.get("data-primer-binding")
            for e in glyph.iter()
        )
        if item.binding_context == "derived_template":
            assert "after copying" in "".join(glyph.itertext())
            assert glyph.get("data-binding-context") == "derived_template"
    assert len([e for e in root.iter() if e.get("data-foldback-cue")]) == 1
    assert any(e.get("data-primer-shape") == "integrated-wedge" for e in root.iter())


def test_incoming_adapter_has_its_destination_shape(atlas):
    from hop_design.export.construction.molecular.assembly.inputs import incoming_materials
    from hop_design.export.construction.molecular.assembly.placement import (
        assembly_points,
        origin_points,
    )

    frames = assembly_points(atlas)
    closed = next(s for s in atlas.states if s.state.phase.value == "foldback_closed_hairpin")
    (placed,) = incoming_materials(atlas, closed, frames)
    target = next(s for s in atlas.states if s.state.state_id == placed.item.post_state_id)
    origins = origin_points(target, frames[target.state.state_id])
    actual = [
        origins[placed.item.material_use.use_id, "primary", i] for i in range(len(placed.positions))
    ]
    offsets = {(x - a, y - b) for (x, y), (a, b) in zip(placed.positions, actual, strict=True)}
    assert len(offsets) == 1
    assert next(iter(offsets))[1] > 0


@pytest.mark.parametrize("presentation", ["complete", "assembly"])
def test_input_introduction_is_independent_of_scene_composition(atlas, presentation):
    root = ET.fromstring(render_molecular_atlas(atlas, presentation=presentation))
    rows = {e.get("data-atlas-state"): e for e in root.iter() if e.get("data-atlas-state")}
    for item in atlas.inputs:
        row = rows[item.pre_state_id]
        glyphs = [
            e
            for e in row.iter()
            if (e.get("data-staged-material") or e.get("data-primer-binding"))
            == item.material_use.use_id
        ]
        assert len(glyphs) == 1, item.material_use.role
        assert (
            "".join(e.text for e in glyphs[0].iter() if e.get("data-input-base-index") is not None)
            == item.material.sequence_5prime
        )
        if item.binding_state_id != item.pre_state_id and item.binding:
            assert glyphs[0].get("data-primer-binding") is None
            assert "after copying" in "".join(glyphs[0].itertext())


def test_incoming_primer_reference_rejects_wrong_sequence_in_partial_scenes(atlas):
    from hop_design.models.construction.projections.atlas import MolecularScenes

    raw = atlas.model_dump(mode="json")
    raw.pop("transitions")
    item = next(i for i in raw["inputs"] if i["introduction_reference"])
    reference = item["introduction_reference"]
    assert len(reference) == item["annealing_length_nt"]
    state = next(s for s in raw["states"] if s["state"]["state_id"] == item["pre_state_id"])
    bases = {b["address"]["index"]: b["base"] for b in state["bases"]}
    original = bases[reference[0]["index"]]
    reference[0]["index"] = next(i for i, base in bases.items() if base != original)
    with pytest.raises(ValueError, match=r"primer.*sequence"):
        MolecularScenes.model_validate_json(json.dumps(raw))


def test_ambiguous_ancestry_keeps_the_existing_layout(atlas):
    from hop_design.export.construction.molecular.assembly.placement import assembly_points

    frame = next(s for s in atlas.states if s.state.phase.value == "adapter_ligated")
    ambiguous = frame.model_copy(update={"bases": (*frame.bases, frame.bases[0])})
    changed = atlas.model_copy(
        update={"states": tuple(ambiguous if s is frame else s for s in atlas.states)}
    )
    assert assembly_points(changed) == {}


def test_assembly_print_preserves_every_displayed_base_and_external_input(atlas):
    from collections import Counter

    from hop_design.export.construction.molecular.printing.atlas import paginate_atlas

    svg = render_molecular_atlas(atlas, presentation="assembly")
    root = ET.fromstring(svg)
    pages, _ = paginate_atlas(svg)
    roots = [ET.fromstring(p) for p in pages]
    assert Counter(
        e.get("data-occurrence") for e in root.iter() if e.get("data-occurrence")
    ) == Counter(
        e.get("data-occurrence") for page in roots for e in page.iter() if e.get("data-occurrence")
    )

    def inputs(roots):
        return Counter(
            (
                group.get("data-staged-material") or group.get("data-primer-binding"),
                e.get("data-input-base-index"),
                e.text,
            )
            for root in roots
            for group in root.iter()
            if group.get("data-staged-material") or group.get("data-primer-binding")
            for e in group.iter()
            if e.get("data-input-base-index") is not None
        )

    assert inputs([root]) == inputs(roots)


def test_assembly_titles_and_site_bands_explain_without_numbering_or_label_arrows(atlas):
    root = ET.fromstring(render_molecular_atlas(atlas, presentation="assembly"))
    titles = [e.text for e in root.iter() if e.get("data-stage-title")]
    assert titles and all(not title[0].isdigit() for title in titles)
    names = [e.text for e in root.iter() if e.get("data-label-kind") == "recognition"]
    assert names and all("→" not in name and "←" not in name for name in names)
    footprints = [e for e in root.iter() if e.get("data-recognition-footprint")]
    assert footprints and all(
        e.tag.endswith("}path") and e.get("fill") != "none" for e in footprints
    )
    assert all(float(e.get("data-recognition-footprint")) > 15 for e in footprints)


def test_complete_primer_silhouettes_clear_the_molecule_and_fit_their_bounds(atlas):
    """Arrowheads must clear strands too, not merely their nucleotide centers."""
    import re
    from math import hypot

    root = ET.fromstring(render_molecular_atlas(atlas, presentation="assembly"))
    for row in (e for e in root.iter() if e.get("data-atlas-state")):
        centers = []
        for base in (e for e in row.iter() if e.get("data-base-index") is not None):
            rect = next(e for e in base if e.tag.endswith("}rect"))
            text = next(e for e in base if e.tag.endswith("}text"))
            centers.append((float(rect.get("x")) + 7, float(text.get("y")) - 5))
        for glyph in (
            e for e in row.iter() if e.get("data-primer-binding") or e.get("data-staged-material")
        ):
            contour = next((e for e in glyph if e.get("data-primer-contour")), None)
            if contour is None:
                continue
            outline = [
                tuple(map(float, p))
                for p in re.findall(r"(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)", contour.get("d"))
            ]
            assert min(hypot(x - a, y - b) for x, y in outline for a, b in centers) >= 21
            left, top, width, height = map(float, glyph.get("data-drawing-box").split())
            assert all(left <= x <= left + width and top <= y <= top + height for x, y in outline)


def test_input_annotations_keep_modifications_without_repeating_ordinary_oh(atlas):
    root = ET.fromstring(render_molecular_atlas(atlas, presentation="assembly"))
    glyphs = [
        e for e in root.iter() if e.get("data-primer-binding") or e.get("data-staged-material")
    ]
    for glyph in glyphs:
        visible = " ".join(e.text or "" for e in glyph.iter() if e.tag.endswith("}text"))
        assert "OH" not in visible
        assert "OH" in " ".join(e.text or "" for e in glyph.iter() if e.tag.endswith("}title"))
    assert "after copying" in "".join(root.itertext())
    assert any("5\u2032P" in "".join(e.itertext()) for e in glyphs)


def test_partial_route_draws_only_requested_scenes_with_complete_route_context(atlas, monkeypatch):
    from hop_design.export.construction.molecular import atlas_layout
    from hop_design.export.construction.molecular.atlas_blocks import route_blocks

    for presentation in ("complete", "assembly"):
        complete = route_blocks(atlas, None, [], presentation=presentation)
        expected = [
            b
            for b in complete
            if b.element.get("data-atlas-phase")
            in {"foldback_closed_hairpin", "hairpin_pcr_duplex"}
        ]
        requested = tuple(b.element.get("data-atlas-state") for b in expected)
        calls = []
        original = atlas_layout.molecular_inspection_element

        def measured(state, _calls=calls, _original=original, **kwargs):
            _calls.append(state.state.state_id)
            return _original(state, **kwargs)

        with monkeypatch.context() as patch:
            patch.setattr(atlas_layout, "molecular_inspection_element", measured)
            actual = route_blocks(atlas, None, [], presentation=presentation, state_ids=requested)
        assert calls == list(requested)
        assert [ET.tostring(b.element) for b in actual] == [
            ET.tostring(b.element) for b in expected
        ]
        assert [b.extent for b in actual] == [b.extent for b in expected]


def test_partial_route_rejects_unknown_duplicate_or_hidden_states_before_drawing(
    atlas, monkeypatch
):
    from hop_design.export.construction.molecular import atlas_layout
    from hop_design.export.construction.molecular.atlas_blocks import route_blocks

    def forbidden(*args, **kwargs):
        pytest.fail("Reject invalid scene selection before drawing")

    monkeypatch.setattr(atlas_layout, "molecular_inspection_element", forbidden)
    first = atlas.states[0].state.state_id
    for requested in (("missing",), (first, first)):
        with pytest.raises(ValueError, match="scene"):
            route_blocks(atlas, None, [], state_ids=requested)
    hidden = next(
        s.state.state_id for s in atlas.states if s.state.phase.value == "denatured_fragments"
    )
    with pytest.raises(ValueError, match="scene"):
        route_blocks(atlas, None, [], presentation="assembly", state_ids=(hidden,))
