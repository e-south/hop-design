"""A saved color view is explicit and cannot revise molecular requirements."""

import pytest

from hop_design.design.construction.navigation.views import inspection_settings
from hop_design.export.construction.survey.color import molecular_colors
from hop_design.models.construction.variants.view import parse_view_receipt


def receipt(color):
    return {
        "schema": "hop.atlas-view/v5",
        "pool_digest": "sha256:" + "a" * 64,
        "selection": {"materialized_realization_id": "one"},
        "presentation": {"color": color},
    }


@pytest.mark.parametrize(
    "color",
    [{"key": "left_gap"}, {"key": "loop_word", "word": "AACA"}, {"key": "none"}],
)
def test_color_receipt_has_explicit_round_trip_without_requiring_axis_recipe(color):
    saved = parse_view_receipt(receipt(color)).model_dump(mode="json", by_alias=True)
    assert saved["schema"] == "hop.atlas-view/v5"
    assert saved["presentation"]["color"] == {"word": None, **color}
    assert "display_axes" not in saved["presentation"]
    assert parse_view_receipt(saved).model_dump(mode="json", by_alias=True) == saved
    assert (
        inspection_settings(presentation={"color": color})["presentation"] == saved["presentation"]
    )


@pytest.mark.parametrize(
    "color",
    [
        {"key": "invented"},
        {"key": "loop_word"},
        {"key": "left_end_word", "word": "NNNN"},
        {"key": "left_gap", "word": "AGTC"},
        {"key": "none", "word": "AGTC"},
        {"key": "loop_word", "word": ""},
        {"key": "loop_word", "word": "AAAA", "color": "red"},
    ],
)
def test_color_receipts_reject_ambiguous_or_unknown_meanings(color):
    with pytest.raises(ValueError):
        parse_view_receipt(receipt(color))


def test_older_schema_cannot_silently_accept_a_color_lens():
    for version in ("v2", "v3", "v4"):
        old = {**receipt({"key": "none"}), "schema": f"hop.atlas-view/{version}"}
        with pytest.raises(ValueError):
            parse_view_receipt(old)


def test_color_and_projected_axes_share_coordinate_binding():
    raw = receipt({"key": "right_end_word", "word": "AACC"})
    raw["presentation"].update(landscape="similarity", display_axes=["left_gap", "right_gap"])
    with pytest.raises(ValueError):
        parse_view_receipt(raw)
    raw["landscape_digest"] = "sha256:" + "b" * 64
    assert parse_view_receipt(raw).presentation.display_axes == ("left_gap", "right_gap")


def test_print_color_keeps_full_pool_scale_and_exact_words_under_filtering():
    rows = [
        {
            "materialized_realization_id": "a",
            "matches": True,
            "values": {"left_gap": 0, "left_end_word": "AGTC"},
        },
        {
            "materialized_realization_id": "b",
            "matches": False,
            "values": {"left_gap": 6, "left_end_word": "AACC"},
        },
        {
            "materialized_realization_id": "c",
            "matches": False,
            "values": {"left_gap": 12, "left_end_word": "AGTC"},
        },
        {"materialized_realization_id": "d", "matches": True, "values": {}},
    ]
    answer = {
        "paths": rows,
        "axes": [
            {"key": "left_gap", "label": "Left gap", "unit": "bp"},
            {"key": "left_end_word", "label": "Left sticky end", "unit": ""},
        ],
    }
    numeric = molecular_colors(answer, {"key": "left_gap"})
    assert numeric.colors == {"a": "#dfebe6", "b": "#539997", "c": "#1a3e4b", "d": None}
    word = molecular_colors(answer, {"key": "left_end_word", "word": "AGTC"})
    assert word.colors == {"a": "#216e72", "b": "#c5cecf", "c": "#216e72", "d": None}
    assert "AGTC" in word.label
