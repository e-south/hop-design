"""Incoming primers retain their silhouette when the nearest lane is occupied."""

from itertools import pairwise
from math import hypot

import pytest

from hop_design.export.construction.molecular.primitives.primer_geometry import (
    position_primer,
)
from hop_design.export.construction.molecular.primitives.primer_shape import primer_outline


@pytest.mark.parametrize("outward", [-1, 1])
def test_primer_stays_near_handle_where_template_straightens(outward):
    template = [(16.0 * i, outward * 64.0) for i in range(11)]
    template += [(160.0 + 12 * i, outward * (64.0 - 12 * i)) for i in range(1, 5)]
    molecule = template + [(208.0 + 16 * i, outward * 16.0) for i in range(1, 10)]

    placed = position_primer(template, molecule, outward=outward)

    assert len(placed) == len(template)
    # The flat inner edge adds 12 units of inward tip width. The nearest safe
    # lane can move ten units outward; keep that explicit geometric allowance.
    assert outward * (placed[0][1] - template[0][1]) <= 58
    outline, _ = primer_outline(placed, outward=outward)
    distances = []
    for a, b in pairwise([*outline, outline[0]]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        length_squared = dx * dx + dy * dy
        for x, y in molecule:
            fraction = (
                min(1, max(0, ((x - a[0]) * dx + (y - a[1]) * dy) / length_squared))
                if length_squared
                else 0
            )
            distances.append(hypot(a[0] + fraction * dx - x, a[1] + fraction * dy - y))
    # Analytic segment distance is stricter than sampling the changed contour.
    assert min(distances) >= 18


@pytest.mark.parametrize("outward", [-1, 1])
def test_blocked_primer_uses_a_clear_lane_without_changing_its_shape(outward):
    template = [(16.0 * i, 0.0) for i in range(11)]
    molecule = template + [(16.0 * i, outward * 70.0) for i in range(16)]
    nearest = position_primer(template, template, outward=outward, leading=2)
    placed = position_primer(template, molecule, outward=outward, leading=2)
    assert len(placed) == len(template) + 2
    # A drawing displacement does not change order, spacing or extension direction.
    assert [x for x, _ in placed] == [x for x, _ in nearest]
    shifts = [y - before[1] for (_, y), before in zip(placed, nearest, strict=True)]
    assert shifts == pytest.approx([shifts[0]] * len(placed))
    outline, _ = primer_outline(placed, outward=outward)
    assert min(outward * y for _, y in outline) >= max(outward * y for _, y in molecule) + 19
