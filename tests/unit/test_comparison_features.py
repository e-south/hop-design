"""
--------------------------------------------------------------------------------
HOP Design
hop-design/tests/unit/test_comparison_features.py

Keep visible comparison fields faithful to the saved basis and exact codebooks.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from hop_design.design.construction.navigation.similarity import comparison_basis
from hop_design.export.construction.survey.comparison_features import comparison_features
from tests.unit.test_molecular_similarity import molecule


def test_selected_static_descriptor_retains_the_browser_vector_and_policy():
    import json
    from xml.etree import ElementTree as ET

    from hop_design.export.construction.survey.comparison_features import (
        selected_comparison_features,
    )
    from hop_design.export.construction.survey.comparison_vector import render_comparison_vector

    rows = (molecule(), molecule(identity="other", basal="GT", loop="AAAC", tail=6, end="GGAA"))
    basis = comparison_basis(rows, weights=(2, 1, 3))
    packet = selected_comparison_features(rows, basis, "other")
    assert packet["identity"] == "other"
    assert packet["basis"] == basis.model_dump(mode="json", exclude={"comparison_keys"})
    expected_keys = [
        *[f"shape.{key}" for key in basis.shape_scales],
        *[f"sequences.{key}" for key in basis.sequence_keys],
        *[f"interfaces.{key}" for key in basis.interface_keys],
    ]
    assert [f["key"] for f in packet["vector"]] == expected_keys
    contact = next(f for f in packet["vector"] if f["key"] == "sequences.basal_pairs")
    assert contact["value"] == [("G", "T", "watson_crick")]
    assert all(type(code) is int for code in contact["encoded"])
    drawing = ET.fromstring(render_comparison_vector(packet))
    assert drawing.get("data-preparation-id") == "other"
    assert [e.get("data-feature") for e in drawing.iter() if e.get("data-feature")] == expected_keys
    displayed = [e.get("data-encoded") for e in drawing.iter() if e.get("data-encoded")]
    assert [json.loads(text) for text in displayed] == json.loads(
        json.dumps([f["encoded"] for f in packet["vector"]])
    )
    assert all("\n" not in text for text in displayed)


def test_features_preserve_exact_tokens_fixed_values_and_cohort_order():
    first = molecule()
    second = molecule(identity="other", basal="GT", loop="AAAC", tail=6, end="GGAA")
    rows = (first, second)
    basis = comparison_basis(rows, weights=(2, 1, 3))
    projection = comparison_features(rows, basis, (second.identity, first.identity))
    assert projection["basis"] == basis.model_dump(mode="json", exclude={"comparison_keys"})
    columns = {c["key"]: c for c in projection["columns"]}

    def read(key, i):
        column = columns[key]
        value = column["dictionary"][column["indices"][i]]
        return (
            tuple(projection["contacts"][t] for t in value)
            if column.get("encoding") == "contacts"
            else value
        )

    assert read("shape.five_prime_unpaired_nt", 0) == 6
    assert read("shape.five_prime_unpaired_nt", 1) == 4
    assert read("sequences.basal_pairs", 0) == (("G", "T", "watson_crick"),)
    assert read("interfaces.left_word", 0) == "GGAA"
    assert columns["shape.loop_nt"]["active"] is False
    assert columns["shape.five_prime_unpaired_nt"]["active"] is True
    assert columns["shape.loop_side_paired_bp"]["parameters"] == ["foldback_arm_bp"]
    assert "stem" not in columns
    assert len(columns["shape.loop_nt"]["dictionary"]) == 1
    assert columns["sequences.basal_pairs"]["encoding"] == "contacts"


def test_non_released_endpoint_does_not_invent_receiving_interfaces():
    row = molecule().model_copy(
        update={
            "endpoint": "ssdna_hairpin",
            "interfaces": None,
            "shape": {k: v for k, v in molecule().shape.items() if not k.endswith("gap")},
        }
    )
    projection = comparison_features((row,), comparison_basis((row,)), (row.identity,))
    assert not any(c["key"].startswith("interfaces.") for c in projection["columns"])
    assert all(not c["active"] for c in projection["columns"])


def test_contact_codes_are_identical_for_browser_and_export_member_orders():
    from hop_design.export.construction.survey.comparison_features import (
        selected_comparison_features,
    )

    rows = (molecule(), molecule(identity="other", basal="GT", loop="AAAC"))
    basis = comparison_basis(rows)
    static = selected_comparison_features(rows, basis, "other")
    browser = comparison_features(rows, basis, tuple(r.identity for r in reversed(rows)))
    assert static["contacts"] == browser["contacts"]
    for feature in static["vector"]:
        column = next(c for c in browser["columns"] if c["key"] == feature["key"])
        assert feature["encoded"] == column["dictionary"][column["indices"][0]]


def test_compact_codes_are_stable_under_member_reordering_and_round_trip():
    from hop_design.export.construction.survey.comparison_features import (
        selected_comparison_features,
    )

    rows = (molecule(), molecule(identity="other", basal="GT", loop="AAAC", tail=6, end="GGAA"))
    basis = comparison_basis(rows)
    static = selected_comparison_features(rows, basis, "other")
    reversed_pool = selected_comparison_features(tuple(reversed(rows)), basis, "other")
    assert static["presentation"] == reversed_pool["presentation"]
    for first, second in zip(static["vector"], reversed_pool["vector"], strict=True):
        assert first["display_value"] == second["display_value"]
        assert type(first["display_value"]) is int
        if first["key"].startswith("shape."):
            assert first["display_value"] == first["value"]
        else:
            projection = comparison_features(rows, basis, tuple(r.identity for r in rows))
            column = next(c for c in projection["columns"] if c["key"] == first["key"])
            assert column["dictionary"][first["display_value"]] == first["encoded"]


def test_compact_export_has_grouped_schematic_glyphs_with_angled_labels():
    from xml.etree import ElementTree as ET

    from hop_design.export.construction.survey.comparison_features import (
        selected_comparison_features,
    )
    from hop_design.export.construction.survey.comparison_vector import render_comparison_vector

    rows = (molecule(), molecule(identity="other", basal="GT", loop="AAAC", tail=6, end="GGAA"))
    packet = selected_comparison_features(rows, comparison_basis(rows), "other")
    root = ET.fromstring(render_comparison_vector(packet, width_pt=237))
    assert float(root.get("width").removesuffix("pt")) == 237
    glyphs = [e for e in root.iter() if e.get("data-input-glyph")]
    assert len(glyphs) == len(packet["vector"])
    assert all(e.get("transform").endswith(" 31)") for e in glyphs)
    assert not any(e.get("data-display-value") for e in root.iter())
    groups = [e.get("data-feature-group") for e in root.iter() if e.get("data-feature-group")]
    assert groups == ["shape", "sequence"]
    labels = [e for e in root.iter() if e.get("data-feature-label")]
    assert all(e.get("transform").startswith("rotate(-45 ") for e in labels)
    assert all(e.get("font-weight") == "normal" for e in labels)
    spans = [e for e in root.iter() if e.get("data-feature-span")]
    assert [e.get("data-feature-span") for e in spans] == groups
    for span in spans:
        assert float(span.get("x2")) > float(span.get("x1"))
        assert float(span.get("y1")) < 31 - 5
        assert span.get("stroke") == "#8a9699"


def test_comparison_labels_use_stage_specific_parameter_vocabulary():
    from hop_design.export.construction.survey.layout import compact_heading
    from hop_design.models.construction.variants.parameters import parameter_definition

    expected = {
        "open_side_paired_positions": ("Basal contacts", "positions"),
        "foldback_arm_bp": ("Loop-side pairing", "bp"),
        "loop_side_paired_bp": ("Loop-side pairing", "bp"),
        "loop_nt": ("Loop length", "nt"),
        "left_gap": ("Left insert spacer", "bp"),
        "right_gap": ("Right insert spacer", "bp"),
        "loop_word": ("Loop sequence", ""),
        "left_end_word": ("Left sticky end", ""),
        "right_end_word": ("Right sticky end", ""),
        "basal_method": ("Basal nickase", ""),
        "foldback_method": ("Foldback nickase", ""),
        "release_method": ("Release enzyme", ""),
    }
    for key, (label, unit) in expected.items():
        definition = parameter_definition(key)
        assert (definition.label, definition.unit) == (label, unit)
        axis = definition.model_dump(mode="json")
        short_unit = "pos" if unit == "positions" else unit
        assert compact_heading(axis) == label + (f" ({short_unit})" if unit else "")
    rows = (molecule(), molecule(identity="other", basal="GT", loop="AAAC"))
    packet = comparison_features(rows, comparison_basis(rows), tuple(r.identity for r in rows))
    fields = {c["key"]: c for c in packet["columns"]}
    for key, label in {
        "sequences.basal_pairs": "Basal pattern",
        "sequences.foldback_pairs": "Loop-side pattern",
        "sequences.loop": "Loop sequence",
        "interfaces.left_word": "Left sticky end",
        "interfaces.right_word": "Right sticky end",
    }.items():
        assert fields[key]["label"] == label
        assert fields[key]["definition"]
