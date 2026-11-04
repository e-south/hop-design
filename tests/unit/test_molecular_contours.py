"""Contour and separation rules preserve orientation while removing graphic ambiguity."""

import re
from itertools import pairwise
from xml.etree import ElementTree as ET

import pytest


def coordinates(path):
    return [tuple(map(float, p)) for p in re.findall(r"(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)", path)]


@pytest.mark.parametrize("side", [-1, 1])
def test_primer_tip_continues_the_template_facing_edge(side):
    from hop_design.export.construction.molecular.primitives.materials import primer_contour

    root = ET.fromstring(primer_contour([(0, 0), (16, 0), (32, 0)], outward=side))
    points = coordinates(root.get("d"))
    tip = max(points, key=lambda p: p[0])
    assert tip == pytest.approx((64, -side * 12))
    assert min(y * side for _, y in points) >= -12
    assert max(y * side for _, y in points) >= 24
    assert "Q" in root.get("d")


def test_primer_clearance_is_normal_to_both_straight_and_diagonal_handle():
    from hop_design.export.construction.molecular.primitives.primer_geometry import (
        parallel_positions,
    )

    path = [(0, 0), (16, 0), (32, 0), (48, 0), (64, 16), (80, 32), (96, 48)]
    for side in (-1, 1):
        result = parallel_positions(path, side * 40)
        assert len(result) == len(path)
        assert result[0][1] == pytest.approx(side * 40)
        x, y = result[-1]
        assert (y - x + 48) / 2**0.5 == pytest.approx(side * 40)
        assert all(
            ((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5 > 10 for a, b in pairwise(result)
        )


def test_rounded_ribbon_keeps_exact_extents_with_small_end_corners():
    from hop_design.export.construction.molecular.primitives.ribbon import ribbon_path

    path = ribbon_path([(0, 0), (16, 0), (32, 0)], 13, terminal_extension=6)
    points = coordinates(path)
    assert min(x for x, _ in points) == -6
    assert max(x for x, _ in points) == 38
    assert max(y for _, y in points) == 13
    assert path.count("Q") >= 4


def test_handle_departure_selects_outside_despite_distant_stem_mass():
    from hop_design.export.construction.molecular.primitives.primer_geometry import outward_side

    upper = [(0, 0), (16, 0), (32, 0), (48, 16), (64, 32)]
    lower = [(0, 100), (16, 100), (32, 100), (48, 84), (64, 68)]
    assert outward_side(upper, (400, 50)) == -1
    assert outward_side(lower, (400, 50)) == 1


def test_recognition_key_uses_the_filled_band_drawn_on_the_strand():
    from hop_design.export.construction.molecular.primitives.annotation_policy import draw_site_key

    svg, _ = draw_site_key([("Example enzyme", "#176487")], 1000, 0)
    key = ET.fromstring(svg)
    symbol = next(e for e in key if e.tag == "rect")
    assert symbol.get("fill") == "#176487"
    assert float(symbol.get("fill-opacity")) == 0.2
