"""One exact preparation teaches the same parameter meanings in every client."""

import json
from collections import Counter
from xml.etree import ElementTree as ET

from hop_design import construction
from tests.integration.test_atlas_edition import captured_choices, captured_edition  # noqa: F401


def test_overview_teaches_local_relationships_and_both_primer_inputs(captured_edition):  # noqa: F811
    from hop_design.export.construction.molecular.teaching_overview import render_teaching_overview

    selected = captured_edition.sample(seed=0)
    summary = json.loads(captured_edition._inspection_packet(selected).json_bytes)
    drawing = ET.fromstring(render_teaching_overview(summary))
    assert not any(e.get("data-site-key") for e in drawing.iter())
    assert not any(e.get("data-teaching-note") == "release" for e in drawing.iter())
    assert "R = A \u2212 D" in "".join(drawing.itertext())
    hairpin_id = next(
        s["state_id"] for s in summary["teaching"]["scenes"] if s["frame"] == "hairpin"
    )
    expected = {
        i["material_use"]["use_id"]: i["material"]["sequence_5prime"]
        for i in summary["atlas"]["inputs"]
        if i["pre_state_id"] == hairpin_id and i["binding"]
    }
    assert len(expected) == 2
    assert {
        i["material_use"]["role"]
        for i in summary["atlas"]["inputs"]
        if i["material_use"]["use_id"] in expected
    } == {"endpoint_forward_primer", "endpoint_reverse_primer"}
    for identity, sequence in expected.items():
        glyph = next(
            e
            for e in drawing.iter()
            if (e.get("data-staged-material") or e.get("data-primer-binding")) == identity
        )
        assert (
            "".join(e.text for e in glyph.iter() if e.get("data-input-base-index") is not None)
            == sequence
        )
        assert glyph.get("data-material-role") in {
            "endpoint_forward_primer",
            "endpoint_reverse_primer",
        }
    assert {
        e.get("data-staged-material") or e.get("data-primer-binding")
        for e in drawing.iter()
        if e.get("data-staged-material") or e.get("data-primer-binding")
    } == set(expected)
    assert any(e.get("data-label-kind") == "recognition" for e in drawing.iter())


def test_inspector_overview_retains_every_base_and_fits_larger_annotations(captured_edition):  # noqa: F811
    from hop_design.export.construction.molecular.teaching_overview import render_teaching_overview
    from hop_design.export.construction.presentation.figure_profile import INSPECTOR_FIGURE

    selected = captured_edition.sample(seed=0)
    summary = json.loads(captured_edition._inspection_packet(selected).json_bytes)
    public = ET.fromstring(render_teaching_overview(summary))
    narrow = ET.fromstring(render_teaching_overview(summary, profile=INSPECTOR_FIGURE))

    def bases(root):
        return {
            (e.get("data-strand-id"), e.get("data-base-index"), e.get("data-base"))
            for e in root.iter()
            if e.get("data-base-index") is not None
        }

    assert bases(narrow) == bases(public)
    from hop_design.export.construction.molecular.primitives.style import base_ink

    for glyph in narrow.iter():
        if glyph.get("data-base-index") is not None:
            letter = next(e for e in glyph if e.tag.endswith("}text"))
            assert letter.get("fill") == base_ink(glyph.get("data-neighborhood"))
    assert len([e for e in narrow.iter() if e.get("data-teaching-frame")]) == 1
    assert not any(e.get("data-teaching-continuation") for e in narrow.iter())
    width, height = map(float, narrow.get("viewBox").split()[2:])
    boxes = [json.loads(e.get("data-label-box")) for e in narrow.iter() if e.get("data-label-box")]
    assert len(boxes) >= 6
    for a, b, w, h in boxes:
        assert 0 <= a < a + w <= width
        assert 0 <= b < b + h <= height
    for i, (a, b, w, h) in enumerate(boxes):
        for x, y, sw, sh in boxes[i + 1 :]:
            assert a + w <= x or x + sw <= a or b + h <= y or y + sh <= b
    for e in narrow.iter():
        if e.get("data-label-box"):
            assert float(e.get("font-size")) * 412 / width >= 12
        if e.get("data-drawing-box") and (
            e.get("data-staged-material") or e.get("data-primer-binding")
        ):
            a, b, w, h = map(float, e.get("data-drawing-box").split())
            assert 0 <= a < a + w <= width
            assert 0 <= b < b + h <= height


def test_publication_overview_measures_complete_glyphs_and_labels(captured_edition):  # noqa: F811
    from hop_design.export.construction.molecular.teaching_overview import render_teaching_overview

    selected = captured_edition.sample(seed=0)
    summary = json.loads(captured_edition._inspection_packet(selected).json_bytes)
    drawing = ET.fromstring(render_teaching_overview(summary))
    assert drawing.get("data-content-frame") is not None
    x, y, width, height = map(float, drawing.get("data-content-frame").split())
    assert width < float(drawing.get("viewBox").split()[2])
    for node in drawing.iter():
        box = None
        if node.get("data-label-box"):
            box = json.loads(node.get("data-label-box"))
        elif node.get("data-drawing-box"):
            box = list(map(float, node.get("data-drawing-box").split()))
        if box:
            a, b, w, h = box
            assert x <= a < a + w <= x + width
            assert y <= b < b + h <= y + height
    loop = next(node for node in drawing.iter() if node.get("data-teaching-note") == "loop")
    value = next(p["value"] for p in summary["teaching"]["parameters"] if p["key"] == "loop_nt")
    assert loop.text == f"{value} nt"
    assert set(json.loads(loop.get("data-teaching-keys"))) == {"loop_nt", "loop_word"}


def test_teaching_neighborhood_names_clear_complete_primer_contours(captured_edition):  # noqa: F811
    from hop_design.export.construction.molecular.teaching_overview import render_teaching_overview

    summary = json.loads(
        captured_edition._inspection_packet(captured_edition.sample(seed=0)).json_bytes
    )
    root = ET.fromstring(render_teaching_overview(summary))
    primers = [
        tuple(map(float, node.get("data-drawing-box").split()))
        for node in root.iter()
        if node.get("data-staged-material") or node.get("data-primer-binding")
    ]
    headings = [node for node in root.iter() if node.get("font-weight") == "600"]
    assert {node.text for node in headings} == {"Basal", "Supplied stem", "Foldback"}
    for node in headings:
        x, y, width, height = json.loads(node.get("data-label-box"))
        for a, b, w, h in primers:
            assert x + width <= a or a + w <= x or y + height <= b or b + h <= y, node.text


def test_structural_scenes_keep_stage_qualified_parameters_and_exact_bases(loop_pool, tmp_path):
    choices = construction.query_scaffold_variants(
        loop_pool, {"result_digest": loop_pool.result_digest, "stage": "hairpin", "focus": "loop"}
    )
    summary = json.loads(choices.json_bytes)
    packet = construction.inspect_scaffold_atlas(
        loop_pool,
        choices,
        {
            "result_digest": loop_pool.result_digest,
            "query_digest": summary["query_digest"],
            "option_label": summary["compatible_options"][0],
        },
    )
    facts = json.loads(packet.json_bytes)
    teaching = facts["teaching"]
    assert [f["key"] for f in teaching["frames"]] == ["source_association", "hairpin", "insert"]
    assert [s["frame"] for s in teaching["scenes"]] == ["hairpin", "insert"]
    parameters = {p["key"]: p for p in teaching["parameters"]}
    assert set(parameters) == {axis["key"] for axis in summary["choice_space"]["axes"]}
    assert teaching["materialized_realization_id"] == facts["atlas"]["materialized_realization_id"]
    locations = {p["key"]: p for p in facts["parameter_locations"]}
    for key in ("foldback_strand", "basal_strand"):
        assert locations[key]["reference_addresses"]
        assert locations[key]["boundary_anchors"]
        assert parameters[key]["coverage"] == "located"
    for key in ("methods", "background"):
        assert parameters[key]["coverage"] == "context"
        assert parameters[key]["location_key"] is None
    assert "state" not in teaching["hairpin"]
    assert all(set(s) == {"strand_id", "sequence"} for s in teaching["source"]["strands"])
    minimum = parameters["adapter_annealing_min_nt"]
    assert minimum["value"] == 18
    assert minimum["domain"]["values"] == [17]
    assert minimum["effective_requirement_differs"] is True
    assert parameters["noncanonical_pairs"]["coverage"] == "empty_contact_set"
    assert parameters["basal_nick_offset_nt"]["coverage"] == "boundary"
    assert parameters["loop_word"]["value"] in ("GAAA", "TTTC")
    assert parameters["self_paired_arm_bp"]["definition"]["dependencies"] == [
        "foldback_arm_bp",
        "join_offset_nt",
    ]
    assert all(p["coverage"] != "unlocated" for p in parameters.values())
    contacts = teaching["contacts"]
    assert contacts
    assert [p["position_from_ligation"] for p in contacts] == list(range(len(contacts)))
    assert all(len(p["parameter_keys"]) == 3 for p in contacts)
    assert all(len(p["source_base"]) == len(p["adapter_base"]) == 1 for p in contacts)
    assert teaching["context"]["coverage"] == facts["envelope"]["coverage"]
    assert "material_policies" in teaching["context"]
    packet.write(tmp_path / "teaching")
    root = ET.fromstring((tmp_path / "teaching/teaching.svg").read_bytes())
    overview = ET.fromstring((tmp_path / "teaching/overview.svg").read_bytes())
    assert overview.get("data-preparation-id") == teaching["materialized_realization_id"]
    width, height = map(float, overview.get("viewBox").split()[2:])
    # A taller single strip now includes both complete primers and local
    # measurements. It remains a landscape panel, without an appended key.
    assert width / height >= 2
    assert not any(e.get("data-site-key") for e in overview.iter())
    assert any(e.get("data-label-kind") == "recognition" for e in overview.iter())
    assert len([e for e in overview.iter() if e.get("data-teaching-frame")]) == 1
    assert not any(e.get("data-teaching-continuation") for e in overview.iter())
    # The compact teaching molecule uses the route's continuous, categorical
    # strands and addressed recognition contours, rather than a second grammar.
    route = ET.fromstring(packet.svg_bytes)
    teaching_bands = [e for e in overview.iter() if e.get("data-region-fill")]
    assert teaching_bands
    assert {(e.get("data-region-fill"), e.get("stroke")) for e in teaching_bands} <= {
        (e.get("data-region-fill"), e.get("stroke"))
        for e in route.iter()
        if e.get("data-region-fill")
    }
    assert any(e.get("data-recognition-footprint") for e in overview.iter())
    hairpin_scene = next(s for s in teaching["scenes"] if s["frame"] == "hairpin")
    hairpin_bases = {
        (m["strand_id"], i, base)
        for s in facts["atlas"]["states"]
        if s["state"]["state_id"] == hairpin_scene["state_id"]
        for m in s["state"]["molecules"]
        for i, base in enumerate(m["sequence"])
    }
    assert {
        (e.get("data-strand-id"), int(e.get("data-base-index")), e.get("data-base"))
        for e in overview.iter()
        if e.get("data-base-index") is not None
    } == hairpin_bases
    anchors = {
        e.get("data-parameter-anchor") for e in overview.iter() if e.get("data-parameter-anchor")
    }
    assert {"loop_nt", "loop_word", "foldback_arm_bp", "left_end_word", "right_end_word"} <= anchors
    rendered = {key for e in root.iter() for key in json.loads(e.get("data-teaching-keys", "[]"))}
    assert rendered <= set(parameters)
    assert {"loop_nt", "foldback_arm_bp", "foldback_method"} <= rendered
    metadata = next(e for e in root.iter() if e.get("data-teaching-parameters"))
    assert json.loads(metadata.text) == teaching["parameters"]
    assert all(
        any(child.tag.endswith(("}path", "}rect", "}polygon")) for child in element.iter())
        for element in root.iter()
        if element.get("data-teaching-keys")
    )
    assert [e.get("data-teaching-frame") for e in root.iter() if e.get("data-teaching-frame")] == [
        "hairpin",
        "insert",
    ]
    assert not any(e.get("data-primer-binding") for e in root.iter())
    hairpin_state = next(s["state_id"] for s in teaching["scenes"] if s["frame"] == "hairpin")
    hairpin = next(s for s in facts["atlas"]["states"] if s["state"]["state_id"] == hairpin_state)
    assert {e.get("data-site-id") for e in root.iter() if e.get("data-site-id")} >= {
        s["site_id"] for s in hairpin["recognition_sites"] if s["recognition"]
    }
    assert parameters["loop_word"]["value"] in "".join(root.itertext())
    inspected = construction.inspect_scaffold_variant(
        loop_pool,
        choices,
        {
            "result_digest": loop_pool.result_digest,
            "query_digest": summary["query_digest"],
            "option_label": summary["compatible_options"][0],
            "state": "endpoint",
        },
    )
    assert json.loads(inspected.json_bytes)["teaching"] == teaching
    inspected.write(tmp_path / "endpoint")
    assert (tmp_path / "endpoint/teaching.svg").read_bytes() == (
        tmp_path / "teaching/teaching.svg"
    ).read_bytes()
    assert b"data-parameter-keys" in inspected.svg_bytes
    states = {s["state"]["state_id"]: s["state"] for s in facts["atlas"]["states"]}
    expected = Counter(
        (scene["state_id"], m["strand_id"], i, base)
        for scene in teaching["scenes"]
        for m in states[scene["state_id"]]["molecules"]
        for i, base in enumerate(m["sequence"])
    )
    actual = Counter(
        (
            e.get("data-state-id"),
            e.get("data-strand-id"),
            int(e.get("data-base-index")),
            next(t.text for t in e if t.tag.endswith("}text")),
        )
        for e in root.iter()
        if e.get("data-base-index") is not None
    )
    assert actual == expected
    width = float(root.get("viewBox").split()[2])
    for base in (e for e in root.iter() if e.get("data-base-index") is not None):
        text = next(t for t in base if t.tag.endswith("}text"))
        assert float(text.get("font-size")) * 504 / width >= 8
    assert root.get("data-preparation-id") == teaching["materialized_realization_id"]
    layout = json.loads((tmp_path / "teaching/teaching-layout.json").read_bytes())
    assert (tmp_path / "teaching/teaching.pdf").is_file()
    assert layout["minimum_sequence_font_pt"] >= 8
    assert all(p["width_pt"] == 504 and p["height_pt"] <= 720 for p in layout["pages"])
    printed = Counter()
    for path in sorted((tmp_path / "teaching/teaching-pages").glob("*.svg")):
        page = ET.fromstring(path.read_bytes())
        printed.update(
            (
                e.get("data-state-id"),
                e.get("data-strand-id"),
                int(e.get("data-base-index")),
                next(t.text for t in e if t.tag.endswith("}text")),
            )
            for e in page.iter()
            if e.get("data-base-index") is not None
        )
    assert printed == expected


def test_current_teaching_uses_catalog_names_without_rewriting_captured_measurements(
    captured_edition,  # noqa: F811
):
    import copy

    from hop_design.export.construction.molecular.teaching_overview import render_teaching_overview

    summary = json.loads(
        captured_edition._inspection_packet(captured_edition.sample(seed=0)).json_bytes
    )
    for item in summary["teaching"]["parameters"]:
        if item["key"] == "foldback_arm_bp":
            item["definition"]["label"] = "Foldback arm"
    for item in summary["parameter_locations"]:
        if item["key"] == "foldback_arm_bp":
            item["definition"]["label"] = "Foldback arm"
    before = copy.deepcopy(summary)
    tree = ET.fromstring(render_teaching_overview(summary))
    anchor = tree.find(".//*[@data-parameter-anchor='foldback_arm_bp']")
    assert anchor.get("data-parameter-label") == "Loop-side extension"
    assert anchor.find("{http://www.w3.org/2000/svg}title").text.startswith("Loop-side extension:")
    assert summary == before
