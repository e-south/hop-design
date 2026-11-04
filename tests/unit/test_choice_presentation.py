"""Display fewer independent concepts without reducing the underlying choice space."""

import copy

import pytest

from hop_design.models.construction.variants.parameters import parameter_definition
from tests.unit.test_survey_plot import choices


def test_primary_axes_keep_product_features_and_variable_methods_but_not_duplicate_outcomes():
    from hop_design.export.construction.survey.presentation import present_choices

    data = choices()
    method = next(a for a in data["axes"] if a["key"] == "basal_method")
    method["domain"]["values"] = ["enzyme-a", "enzyme-b"]
    method["nodes"] = [{**method["nodes"][0], "value": "enzyme-a", "label": "Nb.BsrDI"}]
    data["paths"][0]["values"]["basal_method"] = "enzyme-a"
    before = copy.deepcopy(data)
    view = present_choices(data)
    keys = [a["key"] for a in view["axes"]]
    assert {
        "loop_nt",
        "foldback_arm_bp",
        "left_end_word",
        "left_gap",
        "right_gap",
        "basal_method",
    } <= set(keys)
    assert "self_paired_arm_bp" not in keys
    assert "source_forward_primer_required_nt" not in keys
    assert "release_method" not in keys
    assert any(a["key"] == "release_method" for a in view["fixed"])
    assert data == before


def test_an_observed_constant_is_not_a_fixed_permission_and_overlaps_retain_exact_members():
    from hop_design.export.construction.survey.presentation import present_choices

    data = choices()
    loop = next(a for a in data["axes"] if a["key"] == "loop_nt")
    loop["nodes"] = [loop["nodes"][0]]
    first = data["paths"][0]
    data["paths"] += [{**first, "materialized_realization_id": "another-product"}, dict(first)]
    alias = next(a for a in data["axes"] if a["key"] == "foldback_arm_bp")
    data["axes"].append(
        {**alias, **parameter_definition("loop_side_paired_bp").model_dump(mode="json")}
    )
    for p in data["paths"]:
        p["values"]["loop_side_paired_bp"] = p["values"]["foldback_arm_bp"]
    view = present_choices(data)
    assert "loop_nt" in {a["key"] for a in view["axes"]}
    assert "loop_side_paired_bp" not in {a["key"] for a in view["axes"]}
    assert view["preparations"] == 2
    assert len(view["traces"]) == 1
    assert {p["materialized_realization_id"] for p in view["traces"][0]} == {
        "exact-one",
        "another-product",
    }


def test_an_active_construction_constraint_is_accessible_without_changing_eligibility():
    from hop_design.export.construction.survey.presentation import present_choices

    data = choices()
    data["query"]["parameters"] = [{"key": "self_paired_arm_bp", "minimum": 0, "maximum": 1}]
    view = present_choices(data)
    assert "self_paired_arm_bp" in {a["key"] for a in view["axes"]}
    assert view["traces"][0][0]["matches"]


def test_an_observed_singleton_has_context_distinct_from_fixed_requirements():
    from hop_design.export.construction.survey.presentation import present_choices

    data = choices()
    loop = next(a for a in data["axes"] if a["key"] == "loop_word")
    loop["domain"]["basis"] = "observed_only"
    view = present_choices(data)
    assert "loop_word" not in {a["key"] for a in view["axes"]}
    assert "loop_word" in {a["key"] for a in view["observed_constants"]}
    assert "loop_word" not in {a["key"] for a in view["fixed"]}


def test_explicit_display_axes_preserve_coincident_members_and_full_query():
    from hop_design.export.construction.survey.presentation import present_choices

    data = choices()
    other = copy.deepcopy(data["paths"][0])
    other["materialized_realization_id"] = "another-product"
    other["values"]["loop_nt"] = 6
    other["matches"] = False
    data["paths"].append(other)
    before = copy.deepcopy(data)
    # A declared constant is deliberately requested, not silently omitted.
    axes = ("left_gap", "right_gap", "foldback_arm_bp", "release_method")
    view = present_choices(data, display_axes=axes)
    assert [a["key"] for a in view["axes"]] == list(axes)
    assert len(view["traces"]) == 1
    assert {p["materialized_realization_id"] for p in view["traces"][0]} == {
        "exact-one",
        "another-product",
    }
    assert [p["matches"] for p in view["traces"][0]] == [True, False]
    receipt = view["display_projection"]
    assert receipt["displayed"] == list(axes)
    assert "loop_nt" in receipt["omitted"]
    assert "release_method" in receipt["fixed"]
    assert data == before


@pytest.mark.parametrize(
    "keys", [(), ("unknown",), ("left_gap", "left_gap"), ("foldback_arm_bp", "loop_side_paired_bp")]
)
def test_display_axes_reject_empty_unknown_duplicate_and_alias_requests(keys):
    from hop_design.export.construction.survey.presentation import present_choices

    with pytest.raises(ValueError, match=r"axis|axes|canonical"):
        present_choices(choices(), display_axes=keys)


def test_inspector_recipe_keeps_interfaces_and_shape_without_changing_the_pool():
    from hop_design.export.construction.presentation.figure_profile import INSPECTOR_FIGURE
    from hop_design.export.construction.survey.display_projection import inspector_display_axes
    from hop_design.export.construction.survey.layout import band_count, plot_axes
    from hop_design.export.construction.survey.presentation import present_choices

    data = choices()
    before = copy.deepcopy(data)
    keys = inspector_display_axes(data)
    assert keys == (
        "open_side_paired_positions",
        "left_end_word",
        "left_gap",
        "right_gap",
        "right_end_word",
        "foldback_arm_bp",
        "loop_nt",
    )
    shown = present_choices(data, display_axes=keys)
    assert band_count(plot_axes(shown, profile=INSPECTOR_FIGURE)) <= 2
    assert data == before
    assert shown["preparations"] == len(data["paths"])
    # Endpoint-specific absence is not a fabricated zero-length insert.
    for axis in data["axes"]:
        if axis["key"].startswith(("left_", "right_")):
            axis["applicable"] = False
    assert not any(k.startswith(("left_", "right_")) for k in inspector_display_axes(data))


def test_initial_family_inspection_uses_the_same_product_recipe_without_a_map():
    from types import SimpleNamespace

    from hop_design.commands.design.inspection_view import initial_state
    from hop_design.design.construction.navigation.views import inspection_settings
    from hop_design.export.construction.survey.display_projection import inspector_display_axes

    data = choices()
    source = SimpleNamespace(
        resolution={},
        has_landscape=False,
        query=lambda: data,
        inspection_settings=inspection_settings,
    )
    state = initial_state(source)
    assert state["presentation"]["landscape"] == "families"
    assert state["presentation"]["display_axes"] == list(inspector_display_axes(data))
    assert state["choices"] is data
