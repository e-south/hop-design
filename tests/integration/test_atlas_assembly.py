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
        "selected_fragments",
        "annealed_complex",
        "foldback_closed_hairpin",
        "adapter_annealed",
        "adapter_ligated",
        "hairpin_pcr_duplex",
        "clone_ready_duplex",
    ]
    assert [int(r.get("data-atlas-order")) for r in rows] == list(range(9))
    assert "Fold back and anneal" in "".join(rows[2].itertext())
    assert "Cleave, separate and retain" in "".join(rows[1].itertext())
    assert "Folded and annealed" in "".join(rows[3].itertext())
    assert json.loads(rows[2].get("data-transition-ids")) == [
        t.authority_id for t in atlas.transitions[4:5]
    ]
    assert root.get("data-recorded-state-count") == "11"
    assert atlas.model_dump_json() == before
    complete = ET.fromstring(render_molecular_atlas(atlas))
    assert len([e for e in complete.iter() if e.get("data-atlas-state")]) == 11


def test_browser_scenes_keep_every_repeated_cleanup_site(tmp_path):
    from collections import Counter

    from hop_design.export.construction.molecular.atlas_blocks import route_blocks
    from tests.integration.test_design_source_cleanup import cleanup_intent

    designs = construction.discover_designs(
        cleanup_intent(maximum=24),
        tmp_path / "cleanup",
        max_evaluations=1,
        effort={"local_nodes": 100, "local_realizations": 16, "release_site_pairs": 100},
    )
    packet = designs.atlas(designs.sample(seed=1))
    atlas = MolecularAtlas.model_validate_json(json.dumps(json.loads(packet.json_bytes)["atlas"]))
    before = atlas.model_dump_json()
    blocks = route_blocks(atlas, None, [])
    for state, block in zip(atlas.states, blocks, strict=True):
        sites = {e.get("data-site-id"): e for e in block.element.iter() if e.get("data-site-id")}
        assert set(sites) == {s.site_id for s in state.recognition_sites}
        for site in state.recognition_sites:
            painted = any(e.get("data-recognition-footprint") for e in sites[site.site_id].iter())
            assert painted == bool(site.recognition)
        if state.state.phase.value in {"duplex", "cleaved_duplex"}:
            # Two upstream repeats and the required basal site are separate
            # physical operations, even though the enzyme name is shared.
            repeated = Counter(o.enzyme_id for o in state.operations)
            enzyme = next(key for key, count in repeated.items() if count == 3)
            ids = {o.operation_id for o in state.operations if o.enzyme_id == enzyme}
            names = {e.get("data-label-for-site") for e in block.element.iter()}
            assert ids <= names
    assert atlas.model_dump_json() == before


def test_ordinary_transition_is_centered_between_content_and_next_title(atlas):
    from itertools import pairwise

    from hop_design.export.construction.molecular.primitives.extent import scene_bounds

    root = ET.fromstring(render_molecular_atlas(atlas, presentation="assembly"))
    rows = [e for e in root.iter() if e.get("data-atlas-state")]
    for source, target in pairwise(rows):
        if source.get("data-atlas-column") != target.get("data-atlas-column"):
            continue
        arrow = next(e for e in source if e.get("data-operation-arrow"))
        scene = next(e for e in source if e.get("data-scene-content"))
        ax, _, aw, _ = map(float, arrow.get("data-drawing-box").split())
        label = next(e for e in source if e.get("data-operation"))
        from hop_design.export.construction.molecular.primitives.typography import text_width

        right = float(label.get("x")) + text_width(label.text, float(label.get("font-size")))
        _, top, _, height = scene_bounds(scene, horizontal_span=(ax, max(ax + aw, right)))
        bottom = top + height
        title = next(e for e in target if e.get("data-stage-title"))
        title_top = (
            float(target.get("data-atlas-y"))
            - float(source.get("data-atlas-y"))
            + float(title.get("y"))
            - float(title.get("font-size"))
        )
        _, arrow_top, _, arrow_height = map(float, arrow.get("data-drawing-box").split())
        assert arrow_top - bottom == pytest.approx(title_top - arrow_top - arrow_height)
        assert arrow_top - bottom >= 18 - 1e-6


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
    from itertools import pairwise
    from math import hypot

    from hop_design.export.construction.molecular.primitives.typography import text_width

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
            letters = [e for e in glyph.iter() if e.get("data-input-base-index") is not None]
            for a, b in pairwise(letters):
                pitch = hypot(
                    float(b.get("x")) - float(a.get("x")), float(b.get("y")) - float(a.get("y"))
                )
                assert (
                    pitch >= sum(text_width(t.text, float(t.get("font-size"))) for t in (a, b)) / 2
                )
            outline = [
                tuple(map(float, p))
                for p in re.findall(r"(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)", contour.get("d"))
            ]
            assert min(hypot(x - a, y - b) for x, y in outline for a, b in centers) >= 18
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


def test_closed_hairpin_bond_mark_faces_out_of_its_local_helix(atlas):
    root = ET.fromstring(render_molecular_atlas(atlas, presentation="assembly"))
    row = next(e for e in root.iter() if e.get("data-atlas-phase") == "foldback_closed_hairpin")
    bases = {
        (e.get("data-strand-id"), int(e.get("data-base-index"))): (
            float(next(t for t in e if t.tag.endswith("}text")).get("x")),
            float(next(t for t in e if t.tag.endswith("}text")).get("y")) - 5,
        )
        for e in row.iter()
        if e.get("data-base-index") is not None
    }
    for mark in (e for e in row.iter() if e.get("data-formed-bond")):
        sid, index = mark.get("data-bond-strand"), int(mark.get("data-formed-bond"))
        a, b = bases[sid, index - 1], bases[sid, index]
        center = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        paired = []
        for link in (e for e in row.iter() if e.get("data-pair-kind")):
            p, q = (bases[tuple(json.loads(link.get(k)))[-2:]] for k in ("data-from", "data-to"))
            paired.append(((p[0] + q[0]) / 2, (p[1] + q[1]) / 2))
        near = min(paired, key=lambda p: (p[0] - center[0]) ** 2 + (p[1] - center[1]) ** 2)
        x, y, w, h = map(float, mark.get("data-drawing-box").split())
        assert (x + w / 2 - center[0]) * (center[0] - near[0]) + (y + h / 2 - center[1]) * (
            center[1] - near[1]
        ) > 0


def test_visible_terminal_labels_stay_close_to_their_literal_ends(atlas):
    root = ET.fromstring(render_molecular_atlas(atlas, presentation="assembly"))
    for row in (e for e in root.iter() if e.get("data-atlas-state")):
        for label in (
            e for e in row.iter() if e.get("data-terminal-index") and e.get("data-label-box")
        ):
            base = next(
                e
                for e in row.iter()
                if e.get("data-strand-id") == label.get("data-terminal-strand")
                and e.get("data-base-index") == label.get("data-terminal-index")
            )
            text = next(e for e in base if e.tag.endswith("}text"))
            px, py = float(text.get("x")), float(text.get("y")) - 5
            x, y, w, h = json.loads(label.get("data-label-box"))
            # Minimum edge-to-terminal clearance, rather than distance to the
            # label's left edge or an arbitrary scene-wide position.
            dx, dy = max(x - px, 0, px - x - w), max(y - py, 0, py - y - h)
            assert (dx * dx + dy * dy) ** 0.5 <= 24


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


def test_retained_scene_precedes_folding_with_upward_cue_and_exact_selected_content(atlas):
    root = ET.fromstring(render_molecular_atlas(atlas, presentation="assembly"))
    selected = next(s for s in atlas.states if s.state.phase.value == "selected_fragments")
    row = next(e for e in root.iter() if e.get("data-atlas-phase") == "selected_fragments")
    assert row.get("data-atlas-state") == selected.state.state_id
    assert len([e for e in row.iter() if e.get("data-base-index") is not None]) == len(
        selected.bases
    )
    assert not any(e.get("data-pair-kind") for e in row.iter())
    cue = next(e for e in row.iter() if e.get("data-foldback-cue"))
    assert cue.get("data-cue-phase") == "before-folding"
    assert not any(
        e.get("data-foldback-cue")
        for r in root.iter()
        if r.get("data-atlas-phase") == "annealed_complex"
        for e in r.iter()
    )
    for primer in (
        e
        for e in root.iter()
        if e.get("data-primer-binding")
        or (e.get("data-staged-material") and e.get("data-binding-context") == "derived_template")
    ):
        group = next(e for e in primer if e.get("data-annotation-block"))
        a, b, w, h = tuple(map(float, group.get("data-drawing-box").split()))
        anchor = json.loads(group.get("data-material-label-anchor"))
        assert a + w / 2 == pytest.approx(anchor[0])
        if group.get("data-primer-label-side") == "above":
            assert b + h < anchor[1] - 13
        else:
            assert b > anchor[1] + 13


def test_route_uses_quiet_common_annotation_tiers_and_role_only_primer_names(atlas):
    root = ET.fromstring(render_molecular_atlas(atlas, presentation="assembly"))
    titles = [e for e in root.iter() if e.get("data-stage-title")]
    names = [e for e in root.iter() if e.get("data-label-kind") == "material-name"]
    operations = [e for e in root.iter() if e.get("data-operation")]
    recognition = [e for e in root.iter() if e.get("data-label-kind") == "recognition"]
    assert titles and names and operations and recognition
    assert {e.get("font-size") for e in [*titles, *names, *operations, *recognition]} == {"40"}
    assert all(e.get("font-weight", "400") == "400" for e in titles)
    assert all("5\u2032P" not in (e.text or "") for e in names)
    assert not any(e.get("data-label-kind") == "material-context" for e in root.iter())
    source = next(e for e in root.iter() if e.get("data-atlas-phase") == "source_ssdna")
    by_role = {
        e.get("data-material-role"): e
        for e in source.iter()
        if e.get("data-staged-material") or e.get("data-primer-binding")
    }
    for role, side, name in [
        ("source_materialization_reverse_primer", "above", "Source reverse"),
        ("source_materialization_forward_primer", "below", "Source forward"),
    ]:
        glyph = by_role[role]
        label = next(e for e in glyph.iter() if e.get("data-primer-label-side"))
        assert label.get("data-primer-label-side") == side
        assert next(e.text for e in label if e.get("data-label-kind") == "material-name") == name
    assert "after copying" in "".join(source.itertext())


def test_recognition_names_have_strong_curved_center_anchored_leaders(atlas):
    import re

    root = ET.fromstring(render_molecular_atlas(atlas, presentation="assembly"))
    for row in (e for e in root.iter() if e.get("data-atlas-state")):
        base_points = {
            (e.get("data-strand-id"), int(e.get("data-base-index"))): (
                float(next(t for t in e if t.tag.endswith("}rect")).get("x")) + 7,
                float(next(t for t in e if t.tag.endswith("}text")).get("y")) - 5,
            )
            for e in row.iter()
            if e.get("data-base-index") is not None
        }
        state = next(s for s in atlas.states if s.state.state_id == row.get("data-atlas-state"))
        sites = {s.site_id: s for s in state.recognition_sites}
        for label in (e for e in row.iter() if e.get("data-label-for-site")):
            site = sites[label.get("data-label-for-site")]
            leader = next(e for e in label if e.get("data-site-leader"))
            assert "Q" in leader.get("d") or "C" in leader.get("d")
            assert float(leader.get("stroke-width")) >= 2.5
            assert float(leader.get("stroke-opacity")) >= 0.8
            coordinates = list(map(float, re.findall(r"[-+]?\d+(?:\.\d+)?", leader.get("d"))))
            points = [base_points[a.strand_id, a.index] for a in site.recognition]
            assert coordinates[:2] == pytest.approx(
                [
                    (min(x for x, _ in points) + max(x for x, _ in points)) / 2,
                    (min(y for _, y in points) + max(y for _, y in points)) / 2,
                ]
            )
            text = next(e.text for e in label if e.get("data-label-kind") == "recognition")
            assert " *" not in text


def test_retained_discarded_reference_ghosts_preserve_active_state(atlas):
    before = atlas.model_dump_json()
    root = ET.fromstring(render_molecular_atlas(atlas, presentation="assembly"))
    row = next(e for e in root.iter() if e.get("data-atlas-phase") == "selected_fragments")
    selected = next(s for s in atlas.states if s.state.phase.value == "selected_fragments")
    cleaved = next(s for s in atlas.states if s.state.phase.value == "cleaved_duplex")
    retained_origins = {b.origin for b in selected.bases}
    discarded = [b for b in cleaved.bases if b.origin not in retained_origins]
    ghosts = [e for e in row.iter() if e.get("data-ghost-base-index") is not None]
    assert len(ghosts) == len(discarded) > 0
    assert {
        (
            e.get("data-reference-state-id"),
            e.get("data-reference-strand-id"),
            int(e.get("data-ghost-base-index")),
            next(t.text for t in e if t.tag.endswith("}text")),
        )
        for e in ghosts
    } == {(b.address.state_id, b.address.strand_id, b.address.index, b.base) for b in discarded}
    layer = next(e for e in row.iter() if e.get("data-discarded-fragment-ghosts"))
    assert layer.get("pointer-events") == "none"
    assert not any(
        e.get("data-base-index") is not None or e.get("data-pair-kind") for e in layer.iter()
    )
    assert all(
        e.get("fill") == "white" and e.get("stroke-dasharray")
        for e in layer.iter()
        if e.get("data-ghost-ribbon")
    )
    assert len([e for e in row.iter() if e.get("data-base-index") is not None]) == len(
        selected.bases
    )
    assert atlas.model_dump_json() == before


def test_cut_edges_explain_nicks_and_paired_cleavage_without_inventing_cuts(atlas):
    root = ET.fromstring(render_molecular_atlas(atlas, presentation="assembly"))
    for row in (e for e in root.iter() if e.get("data-atlas-state")):
        state = next(s for s in atlas.states if s.state.state_id == row.get("data-atlas-state"))
        for operation in state.operations:
            glyph = next(
                e for e in row.iter() if e.get("data-operation-id") == operation.operation_id
            )
            expected = (
                "nick"
                if len(operation.cuts) == 1
                else "blunt"
                if operation.cuts[0].precursor_offset == operation.cuts[1].precursor_offset
                else "staggered"
            )
            assert glyph.get("data-cleavage-geometry") == expected
            edges = [e for e in glyph.iter() if e.get("data-cleavage-edge")]
            assert len(edges) == 1 and edges[0].get("data-cleavage-edge") == expected
            assert float(edges[0].get("stroke-width")) >= 3.5
            assert len([e for e in glyph.iter() if e.get("data-cut")]) == len(operation.cuts)


@pytest.mark.parametrize(
    "profile_name", ["PUBLICATION_FIGURE", "LANDSCAPE_DETAIL_FIGURE", "INSPECTOR_FIGURE"]
)
def test_teaching_profiles_share_one_primer_and_site_annotation_tier(loop_pool, profile_name):
    from hop_design.export.construction.molecular.teaching_overview import render_teaching_overview
    from hop_design.export.construction.presentation import figure_profile

    choices, request = atlas_request(loop_pool)
    summary = json.loads(
        construction.inspect_scaffold_atlas(loop_pool, choices, request).json_bytes
    )
    profile = getattr(figure_profile, profile_name)
    root = ET.fromstring(render_teaching_overview(summary, profile=profile))
    annotations = [
        e for e in root.iter() if e.get("data-label-kind") in {"material-name", "recognition"}
    ]
    assert annotations and {e.get("font-size") for e in annotations} == {str(profile.teaching_font)}
    assert not any(e.get("font-weight") == "600" for e in root.iter())


def test_late_route_keeps_mapped_handle_footprints_and_site_records(atlas):
    from hop_design.export.construction.molecular.inspection_layout import inspection_points
    from hop_design.export.construction.molecular.recognition_sites import recognition_site_overlays

    selected = next(s for s in atlas.states if s.state.phase.value == "selected_fragments")
    root = ET.fromstring(
        '<svg xmlns="http://www.w3.org/2000/svg">'
        + recognition_site_overlays(selected, inspection_points(selected))
        + "</svg>"
    )
    foldback = [
        e
        for e in root
        if e.get("data-site-role") in {"foldback_nick", "strand_exposure"}
        and any(
            b.neighborhood in {"closing", "loop"}
            for b in selected.bases
            if b.address
            in next(
                s for s in selected.recognition_sites if s.site_id == e.get("data-site-id")
            ).recognition
        )
    ]
    assert foldback
    assert all(any(e.get("data-recognition-footprint") for e in site.iter()) for site in foldback)
    assert len([e for e in root if e.get("data-site-id")]) == len(selected.recognition_sites)


def test_hairpin_pcr_connector_uses_vertical_legs_and_rounded_orthogonal_turns(atlas):
    import re

    root = ET.fromstring(render_molecular_atlas(atlas, presentation="assembly"))
    stage = next(e for e in root.iter() if e.get("data-atlas-phase") == "adapter_ligated")
    arrow = next(e for e in stage if e.get("data-operation-arrow"))
    assert re.fullmatch(
        r"M[-\d.]+,[-\d.]+ V[-\d.]+ Q[-\d., ]+ H[-\d.]+ Q[-\d., ]+ V[-\d.]+", arrow.get("d")
    )
    assert arrow.get("data-connector-target-phase") == "hairpin_pcr_duplex"
    target = next(e for e in root.iter() if e.get("data-atlas-phase") == "hairpin_pcr_duplex")
    title = next(e for e in target if e.get("data-stage-title"))
    head = next(e for e in stage if e.get("data-operation-arrowhead"))
    tip_x = float(re.findall(r"[-\d.]+", head.get("d"))[2])
    assert tip_x + float(stage.get("data-atlas-x")) == pytest.approx(
        float(target.get("data-atlas-x")) + float(title.get("x"))
    )


def test_route_keeps_mapped_sites_visible_at_every_processing_stage(atlas):
    root = ET.fromstring(render_molecular_atlas(atlas, presentation="assembly"))
    quiet = {
        "selected_fragments",
        "annealed_complex",
        "foldback_closed_hairpin",
        "clone_ready_duplex",
    }
    for stage in (e for e in root.iter() if e.get("data-atlas-phase")):
        state = next(s for s in atlas.states if s.state.state_id == stage.get("data-atlas-state"))
        sites = [e for e in stage.iter() if e.get("data-site-id")]
        assert {e.get("data-site-id") for e in sites} == {
            s.site_id for s in state.recognition_sites
        }
        if state.state.phase.value in quiet:
            assert all(
                bool(e.get("data-recognition-addresses") != "[]")
                == any(n.get("data-recognition-footprint") for n in e.iter())
                for e in sites
            )
        if state.state.phase.value in {
            "source_ssdna",
            "duplex",
            "adapter_ligated",
            "hairpin_pcr_duplex",
        }:
            assert any(e.get("data-recognition-footprint") for e in stage.iter())
    cue = next(e for e in root.iter() if e.get("data-foldback-cue"))
    from hop_design.export.construction.molecular.primitives.style import INK

    assert next(e for e in cue if e.get("stroke")).get("stroke") == INK


def test_fold_cue_leaves_lower_strand_and_points_above_the_upper_ghost(atlas):
    import re

    from hop_design.export.construction.molecular.assembly.foldback import foldback_cue
    from hop_design.export.construction.molecular.assembly.placement import assembly_points

    state = next(s for s in atlas.states if s.state.phase.value == "selected_fragments")
    points = assembly_points(atlas)[state.state.state_id]
    cue = ET.fromstring(foldback_cue(atlas, state, points))
    tail = list(map(float, re.findall(r"[-\d.]+", cue[1].get("d"))))[:2]
    tip = list(map(float, re.findall(r"[-\d.]+", cue[2].get("d"))))[:2]
    assert tail[1] == max(y for _, y in points.values())
    assert tip[1] == min(y for _, y in points.values()) - 24


@pytest.mark.parametrize(
    ("presentation", "phase", "origin"),
    [
        ("complete", "selected_fragments", "retained-foldback"),
        ("assembly", "annealed_complex", "loop-cap"),
    ],
)
def test_route_column_turn_leaves_the_recorded_foldback_region_horizontally(
    atlas, presentation, phase, origin
):
    root = ET.fromstring(render_molecular_atlas(atlas, presentation=presentation))
    last = [e for e in root.iter() if e.get("data-atlas-column") == "0"][-1]
    assert last.get("data-atlas-phase") == phase
    assert not any(e.get("data-operation-arrow") for e in last)
    connector = next(e for e in root.iter() if e.get("data-column-continuation"))
    assert connector.get("data-continuation-start") == origin
    assert connector[0].get("d").split(" ", 2)[1].startswith("H")
    label = next(e for e in last if e.get("data-operation"))
    assert label.get("data-operation-label-placement") == origin


def test_route_column_turn_retains_operation_departure_without_loop_geometry(atlas):
    changed = atlas.model_copy(
        update={
            "states": tuple(
                s.model_copy(
                    update={
                        "bases": tuple(
                            b.model_copy(update={"neighborhood": None})
                            if b.neighborhood == "loop"
                            else b
                            for b in s.bases
                        )
                    }
                )
                if s.state.phase.value == "selected_fragments"
                else s
                for s in atlas.states
            )
        }
    )
    root = ET.fromstring(render_molecular_atlas(changed))
    last = [e for e in root.iter() if e.get("data-atlas-column") == "0"][-1]
    assert any(e.get("data-operation-arrow") for e in last)
    connector = next(e for e in root.iter() if e.get("data-column-continuation"))
    assert connector.get("data-continuation-start") == "operation"
    assert connector[0].get("d").split(" ", 2)[1].startswith("V")


def test_assembly_omits_route_notes_and_repeated_end_words_without_losing_exact_records(atlas):
    before = atlas.model_dump_json()
    root = ET.fromstring(render_molecular_atlas(atlas, presentation="assembly"))
    complete = ET.fromstring(render_molecular_atlas(atlas))
    assert not any(e.get("data-site-key") or e.get("data-atlas-notes") for e in root.iter())
    assert any(e.get("data-site-key") for e in complete.iter())
    assert any(e.get("data-atlas-notes") for e in complete.iter())
    compact_rows = {e.get("data-atlas-state"): e for e in root.iter() if e.get("data-atlas-state")}
    full_rows = {e.get("data-atlas-state"): e for e in complete.iter() if e.get("data-atlas-state")}
    for identity, row in compact_rows.items():

        def addresses(element):
            return sorted(
                e.get("data-occurrence") for e in element.iter() if e.get("data-occurrence")
            )

        assert addresses(row) == addresses(full_rows[identity])
        for interface in (e for e in row.iter() if e.get("data-interface")):
            full = next(
                e
                for e in full_rows[identity].iter()
                if e.get("data-interface") == interface.get("data-interface")
            )
            assert interface.attrib == full.attrib
            assert any(e.get("data-overhang") for e in interface)
            assert not any(e.tag.endswith("}text") for e in interface)
            assert (
                next(e for e in interface if e.tag.endswith("}title")).text
                == next(e for e in full if e.tag.endswith("}title")).text
            )
    assert atlas.model_dump_json() == before


@pytest.mark.parametrize(
    "phases",
    [
        ("source_ssdna", "duplex"),
        ("selected_fragments",),
        ("hairpin_pcr_duplex", "clone_ready_duplex"),
    ],
)
def test_isolated_unfolded_scenes_do_not_measure_offscreen_folded_headroom(
    atlas, monkeypatch, phases
):
    from hop_design.export.construction.molecular import atlas_layout

    full = atlas_layout.atlas_scenes(atlas)
    requested = tuple(i for i, s in enumerate(atlas.states) if s.state.phase.value in phases)
    calls = []
    original = atlas_layout.inspection_overlays

    def measured(state, *args, **kwargs):
        calls.append(state.state.phase.value)
        return original(state, *args, **kwargs)

    monkeypatch.setattr(atlas_layout, "inspection_overlays", measured)
    isolated = atlas_layout.atlas_scenes(atlas, record_indices=requested)
    assert not calls, "Unrequested folded states must not add work to early/linear scene inspection"
    assert set(isolated.scenes) == set(requested)
    for index in requested:
        assert ET.tostring(isolated.scenes[index][0]) == ET.tostring(full.scenes[index][0])
        assert isolated.scenes[index][1:] == full.scenes[index][1:]
    assert isolated.staged_ids == full.staged_ids
