"""Contour and separation rules preserve orientation while removing graphic ambiguity."""

import re
from itertools import pairwise
from xml.etree import ElementTree as ET

import pytest


def coordinates(path):
    return [tuple(map(float, p)) for p in re.findall(r"(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)", path)]


@pytest.mark.parametrize("side", [-1, 1])
def test_primer_tip_continues_the_template_facing_shaft_with_the_flare_outward(side):
    from hop_design.export.construction.molecular.primitives.materials import primer_contour

    root = ET.fromstring(primer_contour([(0, 0), (16, 0), (32, 0)], outward=side))
    points = coordinates(root.get("d"))
    tip = max(points, key=lambda p: p[0])
    assert tip == pytest.approx((52, -12 * side))
    assert min(y * side for _, y in points) >= -12
    assert max(y * side for _, y in points) >= 24
    assert "Q" in root.get("d")


@pytest.mark.parametrize("side", [-1, 1])
@pytest.mark.parametrize(
    "direction", [(1, 0), (-1, 0), (2**-0.5, 2**-0.5), (-(2**-0.5), -(2**-0.5))]
)
def test_primer_inner_arrow_edge_remains_parallel_to_its_terminal_segment(side, direction):
    from hop_design.export.construction.molecular.primitives.primer_shape import primer_outline

    ux, uy = direction
    points = [(0.0, 0.0), (ux * 16, uy * 16), (ux * 32, uy * 32)]
    before = list(points)
    outline, tip_index = primer_outline(points, outward=side)
    nx, ny = -uy * side, ux * side
    tip = outline[tip_index]
    # The asymmetric head retains its outward flare, with a straight inner edge.
    inner_join = outline[tip_index + 1 if side > 0 else tip_index - 1]
    assert (tip[0] - inner_join[0]) * nx + (tip[1] - inner_join[1]) * ny == pytest.approx(0)
    assert (tip[0] - points[-1][0]) * nx + (tip[1] - points[-1][1]) * ny == pytest.approx(-12)
    assert (tip[0] - points[-1][0]) * ux + (tip[1] - points[-1][1]) * uy == pytest.approx(20)
    assert points == before


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


@pytest.mark.parametrize(
    "offsets, expected", [((8,), "nick"), ((8, 8), "blunt"), ((8, 12), "staggered")]
)
def test_cleavage_grammar_distinguishes_recorded_cut_boundaries(offsets, expected):
    from hop_design.export.construction.molecular.inspection_overlays import cleavage_geometry

    assert cleavage_geometry(offsets) == expected
