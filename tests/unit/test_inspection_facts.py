"""Concise comparisons describe recorded coordinates without asserting a control."""

import pytest

from hop_design.design.construction.navigation.local_contrast import explain_choice


def answer():
    return {
        "paths": [
            {
                "materialized_realization_id": "a",
                "values": {
                    "loop_word": "AAAA",
                    "loop_nt": 4,
                    "foldback_arm_bp": 5,
                    "loop_side_paired_bp": 5,
                    "left_gap": 0,
                },
            },
            {
                "materialized_realization_id": "b",
                "values": {
                    "loop_word": "AAAA",
                    "loop_nt": 4,
                    "foldback_arm_bp": 6,
                    "loop_side_paired_bp": 6,
                    "left_gap": 2,
                },
            },
            {
                "materialized_realization_id": "c",
                "values": {
                    "loop_word": "AAAA",
                    "loop_nt": 4,
                    "foldback_arm_bp": 5,
                    "loop_side_paired_bp": 5,
                    "left_gap": 0,
                },
            },
        ]
    }


def test_inspection_explanation_deduplicates_aliases_and_keeps_reference_explicit():
    result = explain_choice(answer(), "b", reference="a")
    assert result["materialized_realization_id"] == "b"
    assert result["reference_identity"] == "a"
    assert result["basis"] == "recorded_parameters"
    assert [c["key"] for c in result["coordinate_changes"]] == ["foldback_arm_bp", "left_gap"]
    assert "Loop-side extension: 5 → 6 bp" in result["description"]
    assert "Left gap: 0 → 2 bp" in result["description"]
    assert "preserved" not in result["description"]


def test_matching_dimensions_do_not_assert_the_same_substrate_or_preserved_surroundings():
    result = explain_choice(answer(), "c", reference="a")
    assert result["coordinate_changes"] == []
    assert result["description"] == "Displayed parameters agree; exact sequences can differ."
    neutral = explain_choice(answer(), "a")
    assert neutral["reference_identity"] is None
    assert neutral["description"] == "Loop AAAA · 5 bp loop-side extension"
    assert explain_choice(answer(), "a", reference="a") == neutral
    with pytest.raises(ValueError, match="recorded"):
        explain_choice(answer(), "b", reference="missing")


def test_background_signature_alone_does_not_identify_the_kind_of_molecular_change():
    data = answer()
    data["paths"][0]["values"].update(background="old", join_offset_nt=2)
    data["paths"][2]["values"].update(background="new", join_offset_nt=3)
    result = explain_choice(data, "c", reference="a")
    assert result["description"] == "Outside-loop scaffold differs."


@pytest.mark.parametrize("display_axes", [None, ["left_gap"]])
def test_hover_uses_the_retained_inspected_reference_after_filter_exclusion(
    monkeypatch, display_axes
):
    from types import SimpleNamespace

    from hop_design.api import _InspectionProjection
    from hop_design.commands.design.inspection_response import preview_response

    data = answer()
    data["query"] = {}
    state = {
        "choices": data,
        "selection": None,
        "view_receipt": {"selection": {"materialized_realization_id": "a"}},
        "token": "current",
        "render_policy": "captured",
        "presentation": {} if display_axes is None else {"display_axes": display_axes},
    }
    monkeypatch.setattr(_InspectionProjection, "layout", lambda *args: {})
    projection = SimpleNamespace(trace=lambda identity: {"identity": identity}, figure_geometry={})
    calls = []

    def project(answer, axes):
        calls.append((answer, axes))
        return projection

    plots = SimpleNamespace(projection=project)
    hover = SimpleNamespace(get=lambda *args, **kwargs: {"teaching_geometry": {}})
    result = preview_response(state, None, plots, hover, "b")
    assert result["inspection_explanation"]["reference_identity"] == "a"
    assert result["inspection_explanation"]["materialized_realization_id"] == "b"
    assert state["selection"] is None
    assert calls == [(data, None if display_axes is None else tuple(display_axes))]


@pytest.mark.parametrize(
    "endpoint,label",
    [
        ("ssdna_hairpin", "ssDNA hairpin"),
        ("adapter_ligated_hairpin", "adapter-ligated hairpin"),
        ("hairpin_pcr_duplex", "copied hairpin duplex"),
        ("clone_ready_duplex", "released duplex insert"),
    ],
)
def test_inspection_product_label_names_each_supported_endpoint_without_rewriting_cost(
    endpoint, label
):
    from copy import deepcopy

    from hop_design.api import _InspectionProjection

    cost = {"endpoint": endpoint, "added_nt_by_strand": {"top": 20}, "distinct_orders": 4}
    before = deepcopy(cost)
    assert _InspectionProjection.product_label(cost) == label
    assert cost == before
    assert _InspectionProjection.product_label(None) is None
    with pytest.raises(ValueError):
        _InspectionProjection.product_label({"endpoint": "unknown_product"})


def test_inspection_state_options_keep_exact_ids_and_shared_molecular_names():
    from hop_design.api import _InspectionProjection

    states = [
        {"state": {"state_id": "first", "phase": "source_ssdna"}},
        {"state": {"state_id": "last", "phase": "clone_ready_duplex"}},
    ]
    assert _InspectionProjection.stage_options(states) == [
        {"value": "first", "label": "Source ssDNA"},
        {"value": "last", "label": "Released insert"},
    ]
    assert states[0]["state"]["phase"] == "source_ssdna"
