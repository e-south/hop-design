"""The visible map descriptor is a projection of the fitted comparison, not new math."""

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
    displayed = [e.text for e in drawing.iter() if e.get("data-encoded")]
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
