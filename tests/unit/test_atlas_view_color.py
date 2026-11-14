"""A saved color view is explicit and cannot revise molecular requirements."""

import pytest

from hop_design.design.construction.navigation.views import inspection_settings
from hop_design.export.construction.survey.color import molecular_colors
from hop_design.models.construction.variants.view import parse_view_receipt


@pytest.mark.parametrize("raw", [None, False, True, 0, 1.5, "", "saved", [], [{}]])
def test_saved_view_rejects_non_object_roots(raw):
    with pytest.raises(ValueError, match="Saved view must be a JSON object"):
        parse_view_receipt(raw)


@pytest.mark.parametrize("field", ["presentation", "exploration"])
@pytest.mark.parametrize("raw", [False, True, 0, 1.5, "", "saved", [], [{}]])
def test_view_options_reject_non_object_values_instead_of_defaulting(field, raw):
    with pytest.raises(ValueError, match=f"{field.capitalize()} must be a JSON object"):
        inspection_settings(**{field: raw})


def test_omitted_view_options_keep_the_same_defaults_as_empty_objects():
    assert inspection_settings(presentation=None, exploration=None) == inspection_settings(
        presentation={}, exploration={}
    )


def test_browser_and_print_keep_the_shared_numeric_palette():
    import json
    import re
    from importlib.resources import files

    from hop_design.export.construction.presentation.palette import NUMERIC_BLUE

    rows = [{"materialized_realization_id": str(i), "values": {"left_gap": i}} for i in range(5)]
    answer = {"paths": rows, "axes": [{"key": "left_gap", "label": "Left gap", "unit": "bp"}]}
    colors = molecular_colors(answer, {"key": "left_gap"}).colors
    assert list(colors.values()) == [value.lower() for value in NUMERIC_BLUE]
    source = files("hop_design").joinpath("assets/design_explorer/molecular_colors.js").read_text()
    stops = json.loads(re.search(r"const ramp=(\[[^;]+\]);", source).group(1))
    expected = [[int(color[i : i + 2], 16) for i in (1, 3, 5)] for color in NUMERIC_BLUE]
    assert stops == expected


def test_population_accent_is_independent_of_molecular_role_fills():
    import re
    from importlib.resources import files

    from hop_design.export.construction.presentation.palette import BASAL, POPULATION_ACCENT

    answer = {"paths": [{"materialized_realization_id": "one", "values": {}}], "axes": []}
    assert molecular_colors(answer, {"key": "none"}).colors == {"one": POPULATION_ACCENT}
    assert POPULATION_ACCENT != BASAL
    source = files("hop_design").joinpath("assets/design_explorer/molecular_colors.js").read_text()
    assert re.search(r"const accent='([^']+)'", source).group(1) == POPULATION_ACCENT


def test_larger_end_gap_color_requires_both_measurements_without_mutating_rows():
    from copy import deepcopy

    answer = {
        "axes": [{"key": key, "applicable": True} for key in ("left_gap", "right_gap")],
        "paths": [
            {"materialized_realization_id": "a", "values": {"left_gap": 0, "right_gap": 0}},
            {"materialized_realization_id": "b", "values": {"left_gap": 4, "right_gap": 1}},
            {"materialized_realization_id": "c", "values": {"left_gap": 1, "right_gap": 4}},
            {"materialized_realization_id": "missing", "values": {"left_gap": 0}},
        ],
    }
    before = deepcopy(answer)
    result = molecular_colors(answer, {"key": "max_end_gap"})
    assert "Larger end gap" in result.label and "bp" in result.label
    assert result.colors == {"a": "#66a8ed", "b": "#0c2043", "c": "#0c2043", "missing": None}
    assert answer == before
    answer["axes"][1]["applicable"] = False
    with pytest.raises(ValueError, match="applicable"):
        molecular_colors(answer, {"key": "max_end_gap"})


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
    assert numeric.colors == {"a": "#66a8ed", "b": "#0073e6", "c": "#0c2043", "d": None}
    word = molecular_colors(answer, {"key": "left_end_word", "word": "AGTC"})
    assert word.colors == {"a": "#0073E6", "b": "#8D99A5", "c": "#0073E6", "d": None}
    assert "AGTC" in word.label


def test_larger_gap_saved_view_validates_against_recorded_side_measurements():
    from types import SimpleNamespace

    from hop_design.design.construction.navigation.views import validate_color
    from hop_design.models.construction.variants.view_color import AtlasColorLens

    lens = AtlasColorLens(key="max_end_gap")

    def choices(rows):
        return SimpleNamespace(query=lambda: {"paths": [{"values": row} for row in rows]})

    validate_color(choices([{"left_gap": 0, "right_gap": 0}]), lens)
    with pytest.raises(ValueError, match="not applicable"):
        validate_color(choices([{"left_gap": 0}]), lens)
    with pytest.raises(ValueError, match="finite numeric"):
        validate_color(choices([{"left_gap": True, "right_gap": 2}]), lens)
