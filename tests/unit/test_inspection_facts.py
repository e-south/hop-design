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
