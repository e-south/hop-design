"""The route is chronological across compact columns and a full-width finish."""

import json
from itertools import pairwise
from xml.etree import ElementTree as ET

import pytest

from hop_design import construction
from tests.integration.test_molecular_atlas import atlas_request


def test_atlas_packs_columns_and_centers_the_wide_finishing_states(loop_pool):
    choices, request = atlas_request(loop_pool)
    packet = construction.inspect_scaffold_atlas(loop_pool, choices, request)
    root = ET.fromstring(packet.svg_bytes)
    rows = [e for e in root.iter() if "data-atlas-state" in e.attrib]
    assert root.get("data-atlas-layout") == "columns-with-finish"
    assert [int(e.get("data-atlas-order")) for e in rows] == list(range(11))
    assert [e.get("data-atlas-phase") for e in rows[-2:]] == [
        "hairpin_pcr_duplex",
        "clone_ready_duplex",
    ]
    assert [e.get("data-atlas-column") for e in rows[-2:]] == ["full", "full"]
    groups = [[e for e in rows if e.get("data-atlas-column") == str(i)] for i in (0, 1)]
    assert all(groups)
    assert float(groups[0][0].get("data-atlas-y")) == float(groups[1][0].get("data-atlas-y"))
    bottoms = [
        float(g[-1].get("data-atlas-y")) + float(g[-1].get("data-atlas-height")) for g in groups
    ]
    for group in groups:
        for previous, following in pairwise(group):
            gap = (
                float(following.get("data-atlas-y"))
                - float(previous.get("data-atlas-y"))
                - float(previous.get("data-atlas-height"))
            )
            # Clearance is inside each measured block; do not add another gap.
            assert gap == pytest.approx(0)
            arrow = next(e for e in previous.iter() if e.get("data-operation-arrow"))
            _, top, _, height = map(float, arrow.get("data-drawing-box").split())
            assert float(previous.get("data-atlas-height")) - top - height >= 24 - 1e-9
    assert float(rows[-2].get("data-atlas-y")) > max(bottoms)
    width = float(root.get("viewBox").split()[2])
    for row in rows[-2:]:
        assert float(row.get("data-atlas-x")) + float(
            row.get("data-atlas-width")
        ) / 2 == pytest.approx(width / 2)
    assert any(e.get("data-column-continuation") for e in root.iter())
    expected = json.loads(packet.json_bytes)["atlas"]
    assert [e.get("data-atlas-state") for e in rows] == [
        s["state"]["state_id"] for s in expected["states"]
    ]


def test_stage_titles_are_centered_over_bases_with_a_larger_hierarchy(loop_pool):
    choices, request = atlas_request(loop_pool)
    packet = construction.inspect_scaffold_atlas(loop_pool, choices, request)
    for row in (
        e for e in ET.fromstring(packet.svg_bytes).iter() if "data-atlas-state" in e.attrib
    ):
        bases = [e for e in row.iter() if "data-base-index" in e.attrib]
        centers, sizes = [], []
        for base in bases:
            rect = next(e for e in base if e.tag.endswith("}rect"))
            text = next(e for e in base if e.tag.endswith("}text"))
            centers.append(float(rect.get("x")) + float(rect.get("width")) / 2)
            sizes.append(float(text.get("font-size")))
        title = next(e for e in row.iter() if e.get("data-stage-title") == "true")
        assert title.get("text-anchor") == "middle"
        assert float(title.get("x")) == pytest.approx((min(centers) + max(centers)) / 2)
        assert set(sizes) == {16}
        assert float(title.get("font-size")) * 0.5 == 28
        assert float(title.get("font-size")) >= 3 * max(sizes)


def test_operation_names_are_beside_large_arrows_in_the_same_row(loop_pool):
    choices, request = atlas_request(loop_pool)
    root = ET.fromstring(construction.inspect_scaffold_atlas(loop_pool, choices, request).svg_bytes)
    for row in (e for e in root.iter() if e.get("data-atlas-state")):
        arrows = [e for e in row.iter() if e.get("data-operation-arrow")]
        if not arrows:
            continue
        arrow = arrows[0]
        label = next(e for e in row.iter() if e.get("data-operation"))
        x, y, width, height = map(float, arrow.get("data-drawing-box").split())
        assert height >= 90
        assert float(label.get("x")) > x + width
        assert float(label.get("y")) - float(label.get("font-size")) * 0.35 == pytest.approx(
            y + height / 2
        )

    rows = [e for e in root.iter() if e.get("data-atlas-state")]
    last_left = [row for row in rows if row.get("data-atlas-column") == "0"][-1]
    assert not any(e.get("data-operation-arrowhead") for e in last_left)
    arrow = next(e for e in last_left if e.get("data-operation-arrow"))
    x, y, width, height = map(float, arrow.get("data-drawing-box").split())
    start = (
        float(last_left.get("data-atlas-x")) + x + width / 2,
        float(last_left.get("data-atlas-y")) + y + height - 22,
    )
    connector = next(e for e in root.iter() if e.get("data-column-continuation"))
    assert connector[0].get("d").startswith(f"M{start[0]},{start[1]}")


def test_molecular_annotations_are_readable_and_do_not_collide(loop_pool):
    choices, request = atlas_request(loop_pool)
    packet = construction.inspect_scaffold_atlas(loop_pool, choices, request)
    root = ET.fromstring(packet.svg_bytes)
    labels = [e for e in root.iter() if e.get("data-label-box")]
    assert labels
    assert min(float(e.get("font-size")) for e in labels) >= 32
    assert all(
        float(e.get("font-size")) >= 48
        for e in labels
        if e.get("data-label-kind")
        not in {"terminus", "primer-chemistry", "material-name", "material-context"}
    )
    for row in (e for e in root.iter() if e.get("data-atlas-state")):
        boxes = [json.loads(e.get("data-label-box")) for e in row.iter() if e.get("data-label-box")]
        for i, (x, y, w, h) in enumerate(boxes):
            assert y >= 40
            for a, b, c, d in boxes[i + 1 :]:
                assert x + w <= a or a + c <= x or y + h <= b or b + d <= y


def test_exact_comparison_details_do_not_expand_the_molecular_canvas(loop_pool):
    choices, request = atlas_request(loop_pool)
    query = json.loads(choices.json_bytes)
    reference, target = query["compatible_options"][:2]
    choices = construction.query_scaffold_variants(
        loop_pool, {**query["query"], "reference": reference}
    )
    request.update(query_digest=json.loads(choices.json_bytes)["query_digest"], option_label=target)
    packet = construction.inspect_scaffold_atlas(loop_pool, choices, request)
    root = ET.fromstring(packet.svg_bytes)
    assert not any(e.get("data-material-comparison") for e in root.iter())
    details = ET.fromstring(dict(packet._files)["comparison.svg"])
    assert any(e.get("data-material-comparison") for e in details.iter())
    assert "comparison.svg" in packet.report_text
    assert any(e.get("data-change-legend") for e in root.iter())


def test_terminal_labels_share_collision_layout_with_enzyme_and_primer_names(loop_pool):
    choices, request = atlas_request(loop_pool)
    packet = construction.inspect_scaffold_atlas(loop_pool, choices, request)
    atlas = json.loads(packet.json_bytes)["atlas"]
    terminals = [
        e for e in ET.fromstring(packet.svg_bytes).iter() if e.get("data-label-kind") == "terminus"
    ]
    assert len(terminals) == 2 * sum(len(s["state"]["molecules"]) for s in atlas["states"])
    assert {e.get("data-terminal-chemistry") for e in terminals} == {
        "5\u2032OH",
        "5\u2032P",
        "3\u2032OH",
    }


def test_narrative_names_preserve_all_footprints_and_partial_site_warnings(loop_pool):
    from hop_design.export.construction.molecular.atlas import render_molecular_atlas
    from hop_design.models.construction.projections.atlas import MolecularAtlas

    choices, request = atlas_request(loop_pool)
    packet = construction.inspect_scaffold_atlas(loop_pool, choices, request)
    model = MolecularAtlas.model_validate_json(json.dumps(json.loads(packet.json_bytes)["atlas"]))
    full = ET.fromstring(render_molecular_atlas(model, site_labels="all"))
    narrative = ET.fromstring(render_molecular_atlas(model))

    def names(root):
        return [e for e in root.iter() if e.get("data-site-labels")]

    assert len(names(narrative)) < len(names(full))
    for key in ("data-site-id", "data-cut", "data-occurrence"):
        assert [e.get(key) for e in narrative.iter() if e.get(key)] == [
            e.get(key) for e in full.iter() if e.get(key)
        ]
    assert any(e.get("data-site-key") for e in narrative.iter())
    for site in (
        e for e in narrative.iter() if e.get("data-presence") in {"partial", "unresolved"}
    ):
        assert all(e.get("stroke-dasharray") for e in site if e.get("data-recognition-footprint"))


def test_recorded_primer_bindings_replace_duplicate_sequence_lists(loop_pool):
    choices, request = atlas_request(loop_pool)
    packet = construction.inspect_scaffold_atlas(loop_pool, choices, request)
    root = ET.fromstring(packet.svg_bytes)
    inputs = json.loads(packet.json_bytes)["atlas"]["inputs"]
    for item in inputs:
        use_id = item["material_use"]["use_id"]
        drawings = [
            e
            for e in root.iter()
            if any(
                e.get(key) == use_id
                for key in ("data-primer-binding", "data-atlas-input", "data-staged-material")
            )
        ]
        assert len(drawings) == 1
        if item["binding"] is not None:
            stage = next(
                e
                for e in root.iter()
                if drawings[0] in list(e.iter()) and e.get("data-atlas-state")
            )
            assert stage.get("data-atlas-state") == item["pre_state_id"]
        if item["binding_context"] == "recorded_state":
            assert (
                "".join(e.text for e in drawings[0] if e.get("data-input-base-index") is not None)
                == item["material"]["sequence_5prime"]
            )
            assert any(e.get("data-primer-chemistry") for e in drawings[0].iter())


def test_terminal_shorthand_keeps_explicit_chemistry_in_the_record(loop_pool):
    choices, request = atlas_request(loop_pool)
    root = ET.fromstring(construction.inspect_scaffold_atlas(loop_pool, choices, request).svg_bytes)
    terminals = [e for e in root.iter() if e.get("data-label-kind") == "terminus"]
    assert terminals and all(
        e.get("data-terminal-chemistry") in {"5\u2032OH", "3\u2032OH", "5\u2032P", "3\u2032P"}
        for e in terminals
    )
    assert all(e.text == e.get("data-terminal-chemistry").replace("OH", "") for e in terminals)
    assert "Unmarked termini: OH" in "".join(root.itertext())
    key = next(e for e in root.iter() if e.get("data-site-key"))
    notes = next(e for e in root.iter() if e.get("data-atlas-notes"))
    key_bottom = max(
        float(e.get("y")) + float(e.get("font-size")) * 0.25
        for e in key.iter()
        if e.tag.endswith("}text")
    )
    notes_top = min(
        float(e.get("y")) - float(e.get("font-size")) * 0.8
        for e in notes.iter()
        if e.tag.endswith("}text")
    )
    assert notes_top >= key_bottom + 4


def test_cut_and_join_marks_have_distinct_event_shapes(loop_pool):
    choices, request = atlas_request(loop_pool)
    root = ET.fromstring(construction.inspect_scaffold_atlas(loop_pool, choices, request).svg_bytes)
    cuts = [e for e in root.iter() if e.get("data-cut")]
    joins = [e for e in root.iter() if e.get("data-formed-bond")]
    assert cuts and joins
    assert all(e.get("data-cut-timing") in {"planned", "applied"} for e in cuts)
    assert all(e.get("data-event-glyph") == "bond-bridge" for e in joins)
    assert all(
        any(c.get("data-cut-notch") for c in e)
        for e in cuts
        if e.get("data-cut-timing") == "applied"
    )


def test_released_end_labels_name_the_recorded_words_and_gaps(loop_pool):
    choices, request = atlas_request(loop_pool)
    packet = construction.inspect_scaffold_atlas(loop_pool, choices, request)
    model = json.loads(packet.json_bytes)["atlas"]
    root = ET.fromstring(packet.svg_bytes)
    for state in model["states"]:
        row = next(
            e for e in root.iter() if e.get("data-atlas-state") == state["state"]["state_id"]
        )
        for interface in state["interfaces"]:
            group = next(e for e in row.iter() if e.get("data-interface") == interface["side"])
            assert f"{interface['sequence']} · {interface['distance_bp']} bp" in "".join(
                group.itertext()
            )
            assert group.get("data-end-polarity") == interface["polarity"]


def test_primer_names_and_chemistry_share_an_attached_label_group(loop_pool):
    choices, request = atlas_request(loop_pool)
    root = ET.fromstring(construction.inspect_scaffold_atlas(loop_pool, choices, request).svg_bytes)
    for primer in (e for e in root.iter() if e.get("data-primer-binding")):
        group = next(e for e in primer if e.get("data-annotation-block"))
        assert all(e.get("data-label-kind") == "material-name" for e in group)
        assert group.get("data-primer-chemistry")
        assert len({e.get("x") for e in group}) == 1


def test_route_titles_attach_to_measured_content_instead_of_fixed_top_padding(loop_pool):
    from hop_design.export.construction.molecular.primitives.extent import scene_extent

    choices, request = atlas_request(loop_pool)
    root = ET.fromstring(construction.inspect_scaffold_atlas(loop_pool, choices, request).svg_bytes)
    for row in (e for e in root.iter() if e.get("data-atlas-state")):
        content = next((e for e in row if e.get("data-scene-content")), None)
        assert content is not None, (
            "Molecular content needs its own measured placement, independent of the title"
        )
        assert float(row.get("data-atlas-height")) >= scene_extent(content)[1]
