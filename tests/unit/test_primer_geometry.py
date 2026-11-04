"""Incoming primers retain their silhouette when the nearest lane is occupied."""

import pytest

from hop_design.export.construction.molecular.primitives.primer_geometry import (
    position_primer,
)
from hop_design.export.construction.molecular.primitives.primer_shape import primer_outline


@pytest.mark.parametrize("outward", [-1, 1])
def test_blocked_primer_uses_a_clear_lane_without_changing_its_shape(outward):
    template = [(16.0 * i, 0.0) for i in range(11)]
    molecule = template + [(16.0 * i, outward * 80.0) for i in range(16)]
    nearest = position_primer(template, template, outward=outward, leading=2)
    placed = position_primer(template, molecule, outward=outward, leading=2)
    assert len(placed) == len(template) + 2
    # A drawing displacement does not change order, spacing or extension direction.
    assert [x for x, _ in placed] == [x for x, _ in nearest]
    shifts = [y - before[1] for (_, y), before in zip(placed, nearest, strict=True)]
    assert shifts == pytest.approx([shifts[0]] * len(placed))
    outline, _ = primer_outline(placed, outward=outward)
    assert min(outward * y for _, y in outline) >= max(outward * y for _, y in molecule) + 23
