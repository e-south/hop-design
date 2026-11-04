"""An inspection renders its visible drawing set, retaining bounded cache ownership."""

import copy

import pytest

from hop_design.api import _InspectionProjection
from hop_design.commands.design.inspection_plots import InspectionPlots


@pytest.fixture(autouse=True)
def axes_stub(monkeypatch):
    # These tests own cache lifetime; shared renderer geometry has separate tests.
    monkeypatch.setattr(_InspectionProjection, "axes", lambda answer: b"x" * 20)


class Choices:
    has_landscape = True

    def __init__(self):
        self.drawn = []
        self.large = set()

    def families(self, **kwargs):
        return {"products": []}

    def explain(self, query):
        return {"guidance": "Choose a preparation."}

    def plot_svg_bytes(self, query, *, view, **kwargs):
        self.drawn.append(view)
        return b"x" * (1000 if view in self.large else 20)


def state(mode="parameters"):
    return {
        "selection": None,
        "choices": {"query": {}},
        "family_stage": "endpoint",
        "presentation": {"layout": "mosaic", "landscape": mode},
    }


@pytest.mark.parametrize("mode", ["parameters", "families", "similarity"])
def test_only_visible_plot_set_is_generated_and_map_capability_remains_visible(tmp_path, mode):
    choices = Choices()
    plots = InspectionPlots(tmp_path)
    try:
        result = plots.get(choices, state(mode))
        expected = {"parameters", "distributions", mode}
        assert set(choices.drawn) == expected
        assert set(result["plots"]) == expected | {"inspection"}
        assert len(choices.drawn) == len(expected)
        assert result["has_landscape"] is True
        for url in result["plots"].values():
            assert (tmp_path / url.removeprefix("/files/")).is_file()
    finally:
        plots.close()
    assert not plots.root.exists() and plots.bytes == 0


def test_presentation_switch_changes_plots_but_camera_reuses_them(tmp_path):
    choices = Choices()
    plots = InspectionPlots(tmp_path)
    try:
        first = plots.get(choices, state())
        moved = copy.deepcopy(state())
        moved["camera"] = {"x": 10}
        assert plots.get(choices, moved) == first
        assert len(choices.drawn) == 2
        second = plots.get(choices, state("similarity"))
        assert "similarity" in second["plots"]
        assert len(choices.drawn) == 5
        assert plots.get(choices, state()) == first
        assert len(choices.drawn) == 5
    finally:
        plots.close()


def test_inactive_oversized_drawing_does_not_block_active_view(tmp_path):
    choices = Choices()
    choices.large = {"similarity"}
    plots = InspectionPlots(tmp_path, byte_limit=100)
    try:
        first = plots.get(choices, state())
        owned = set(plots.root.iterdir())
        with pytest.raises(ValueError, match="bounded inspection cache"):
            plots.get(choices, state("similarity"))
        assert set(plots.root.iterdir()) == owned
        assert plots.get(choices, state()) == first
        assert plots.bytes == 60
    finally:
        plots.close()


def test_pin_changes_do_not_regenerate_the_cohort_or_its_axes(tmp_path):
    choices = Choices()
    plots = InspectionPlots(tmp_path)
    try:
        initial = state("similarity")
        first = plots.get(choices, initial)
        for identity in ("one", "two", "one"):
            pinned = copy.deepcopy(initial)
            pinned["selection"] = {"materialized_realization_id": identity}
            assert plots.get(choices, pinned)["plots"] == first["plots"]
        assert choices.drawn == ["parameters", "similarity", "distributions"]
    finally:
        plots.close()
