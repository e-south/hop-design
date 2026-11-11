"""Publication refinements retain molecular inventories and usable annotation anchors."""

import json
from xml.etree import ElementTree as ET

from hop_design.export.construction.molecular.atlas import render_molecular_atlas
from tests.integration.test_atlas_assembly import atlas  # noqa: F401


def test_source_recognition_bands_use_the_future_complementary_row(atlas):  # noqa: F811
    from hop_design.export.construction.molecular.inspection import molecular_inspection_element

    source = atlas.states[0]
    root = molecular_inspection_element(source)
    glyph = next(e for e in root.iter() if e.get("data-base-index") is not None)
    rect = next(e for e in glyph if e.tag.endswith("}rect"))
    y = float(rect.get("y")) + float(rect.get("height")) / 2
    for site in (e for e in root.iter() if e.get("data-site-id")):
        bands = [e for e in site if e.get("data-recognition-footprint")]
        if not bands:
            continue
        assert len(bands) == 1
        _left, top, _width, height = json.loads(bands[0].get("data-envelope-box"))
        assert top == y - 18 and top + height == y + 44 + 18


def test_route_labels_anchor_to_horizontal_material_ink_and_adapter_ends(atlas):  # noqa: F811
    root = ET.fromstring(render_molecular_atlas(atlas, presentation="assembly"))
    for item in (
        e for e in root.iter() if e.get("data-primer-binding") or e.get("data-staged-material")
    ):
        anchor = json.loads(
            next(e for e in item.iter() if e.get("data-material-label-anchor")).get(
                "data-material-label-anchor"
            )
        )
        label = next(e for e in item.iter() if e.get("data-label-kind") == "material-name")
        a, _b, w, _h = json.loads(label.get("data-label-box"))
        assert abs(a + w / 2 - anchor[0]) < 1e-6
        letters = [e for e in item.iter() if e.get("data-input-base-index") is not None]
        assert all(e.get("dy") is not None and e.get("text-anchor") == "middle" for e in letters)
        if item.get("data-material-role") == "ligation_adapter":
            assert label.text == "Y adapter"
            ends = [e for e in item.iter() if e.get("data-input-terminus")]
            assert {e.get("data-input-terminus") for e in ends} == {"five_prime", "three_prime"}
    for glyph in (e for e in root.iter() if e.get("data-base-index") is not None):
        assert next(e for e in glyph if e.tag.endswith("}text")).get("dy") is not None


def test_simple_contours_remove_self_crossing_offset_loops():
    from hop_design.export.construction.molecular.primitives.ribbon import simple_outline

    # A narrow bend can introduce a small false loop in an offset outline.
    points = [
        (0.0, 0.0),
        (40.0, 0.0),
        (40.0, 40.0),
        (20.0, 40.0),
        (20.0, 20.0),
        (30.0, 30.0),
        (10.0, 30.0),
        (20.0, 20.0),
        (0.0, 40.0),
    ]
    result = simple_outline(points)
    assert len(result) < len(points)
    assert min(x for x, y in result) == 0 and max(x for x, y in result) == 40


def test_concise_overview_keeps_connected_sites_without_floating_dimensions(atlas):  # noqa: F811
    from hop_design.export.construction.molecular.inspection_layout import inspection_points
    from hop_design.export.construction.molecular.teaching_annotations.layout import (
        OverviewLabels,
        compact_recognition_overlays,
    )

    state = next(s for s in atlas.states if s.state.phase.value == "adapter_ligated")
    points = inspection_points(state)
    root = ET.fromstring(
        "<svg>"
        + compact_recognition_overlays(state, points, OverviewLabels(points, width=1400, size=32))
        + "</svg>"
    )
    assert any(e.get("data-site-leader") for e in root.iter())


def test_duplex_sites_combine_rows_without_merging_distinct_site_identities(atlas):  # noqa: F811
    from hop_design.export.construction.molecular.inspection import molecular_inspection_element

    state = next(s for s in atlas.states if s.state.phase.value == "duplex")
    root = molecular_inspection_element(state)
    groups = {e.get("data-site-id"): e for e in root.iter() if e.get("data-site-id")}
    assert set(groups) == {s.site_id for s in state.recognition_sites}
    for site in state.recognition_sites:
        bands = [e for e in groups[site.site_id] if e.get("data-recognition-footprint")]
        assert len(bands) == (1 if site.recognition else 0)
        assert {tuple(a)[-2:] for e in bands for a in json.loads(e.get("data-members"))} == {
            (a.strand_id, a.index) for a in site.recognition
        }


def test_long_descriptor_fits_article_width_without_losing_encoded_tokens():
    import json
    from xml.etree import ElementTree as ET

    from hop_design.export.construction.survey.comparison_vector import render_comparison_vector

    fields = [
        {
            "key": f"shape.dimension{i}",
            "label": f"Parameter {i}",
            "unit": "nt",
            "encoded": i,
            "value": i,
        }
        for i in range(5)
    ]
    fields += [
        {
            "key": "sequences.basal_pairs",
            "label": "Basal contacts",
            "unit": "",
            "encoding": "contacts",
            "encoded": [1, 12] * 9,
            "value": [("A", "T", "watson_crick")] * 18,
        },
        {
            "key": "sequences.foldback_pairs",
            "label": "Foldback contacts",
            "unit": "",
            "encoding": "contacts",
            "encoded": [2] * 5,
            "value": [("C", "G", "watson_crick")] * 5,
        },
    ]
    fields += [
        {
            "key": f"interfaces.end{i}",
            "label": f"End {i}",
            "unit": "",
            "encoded": "ACGT",
            "value": "ACGT",
        }
        for i in range(3)
    ]
    from hop_design.export.construction.presentation.comparison import COMPARISON_GROUPS

    for field in fields:
        field["display_value"] = field["value"] if field["key"].startswith("shape.") else 0
    packet = {
        "identity": "example",
        "vector": fields,
        "presentation": {"groups": COMPARISON_GROUPS},
    }
    root = ET.fromstring(render_comparison_vector(packet))
    assert float(root.get("viewBox").split()[2]) <= 504
    assert root.get("data-comparison-display") == "numeric-row"
    assert [json.loads(e.get("data-encoded")) for e in root.iter() if e.get("data-encoded")] == [
        f["encoded"] for f in fields
    ]
    for e in root.iter():
        if e.get("data-encoded"):
            assert e.get("data-vector-index") is not None
        if e.tag.endswith("text"):
            assert float(e.get("font-size")) >= 7.2


def test_constant_only_descriptor_states_all_features_are_constant():
    from hop_design.export.construction.survey.comparison_vector import render_comparison_vector

    packet = {
        "identity": "constant-example",
        "vector": [],
        "features": [{"key": "shape.loop_nt", "value": 4, "active": False}],
    }
    root = ET.fromstring(render_comparison_vector(packet))
    assert "X =" in "".join(root.itertext())
    assert json.loads(root.find("{http://www.w3.org/2000/svg}metadata").text) == packet
