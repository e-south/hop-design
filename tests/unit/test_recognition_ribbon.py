"""Recognition ink follows bent strands without covering the empty inside corner."""

import pytest


def test_horizontal_and_reversed_footprints_have_equal_thickness():
    from hop_design.export.construction.molecular.primitives.ribbon import ribbon_points

    forward = ribbon_points([(0, 0), (32, 0)], 15)
    reverse = ribbon_points([(32, 44), (0, 44)], 15)
    assert min(x for x, _ in forward) == pytest.approx(-8)
    assert max(x for x, _ in forward) == pytest.approx(40)
    assert max(y for _, y in forward) - min(y for _, y in forward) == pytest.approx(30)
    assert max(y for _, y in reverse) - min(y for _, y in reverse) == 30


def test_bent_footprint_preserves_its_band_width_at_each_end():
    from hop_design.export.construction.molecular.primitives.ribbon import ribbon_points

    shape = ribbon_points([(0, 0), (32, 0), (64, 32)], 15)
    # Two sides of the diagonal endpoint remain 30 units apart, rather than
    # filling a 62-unit-tall axis-aligned rectangle over the bend.
    assert len(shape) > 6
    n = len(shape) // 2
    assert (
        (shape[n - 1][0] - shape[n][0]) ** 2 + (shape[n - 1][1] - shape[n][1]) ** 2
    ) ** 0.5 == pytest.approx(30)
    assert max(x for x, y in shape if y < -10) < 60


def test_single_base_footprint_is_a_finite_tile():
    from hop_design.export.construction.molecular.primitives.ribbon import ribbon_points

    assert {(12, 15), (28, 15), (28, 45), (12, 45)} <= set(ribbon_points([(20, 30)], 15))


def test_adjacent_region_bands_share_the_same_curve_boundary():
    from hop_design.export.construction.molecular.primitives.strand_curve import band_segments

    points = [(0.0, 0.0), (16.0, 0.0), (27.0, 11.0), (32.0, 22.0), (27.0, 33.0), (16.0, 44.0)]
    left = band_segments(points, 0, 2)
    right = band_segments(points, 3, 5)
    assert left[-1][-1] == right[0][0]
    # Shared boundary tangents keep the band smooth without overlapping tiles.
    a, b = left[-1][-2:]
    c, d = right[0][:2]
    assert (b[0] - a[0], b[1] - a[1]) == pytest.approx((d[0] - c[0], d[1] - c[1]))
    assert all(
        point
        in [segment[0] for segment in left + right] + [segment[-1] for segment in left + right]
        for point in points
    )


def test_single_base_band_retains_the_same_readable_extent():
    from hop_design.export.construction.molecular.primitives.strand_curve import band_segments

    segments = band_segments([(20.0, 30.0)], 0, 0)
    # Unjoined strands on adjacent base positions must retain a visible break.
    assert segments[0][0] == (14.0, 30.0)
    assert segments[-1][-1] == (26.0, 30.0)


def test_region_ink_carries_backbone_without_incidental_dots_between_letters():
    from xml.etree import ElementTree as ET

    from hop_design.export.construction.molecular.inspection_scene import edge

    points = {("s", 0): (0, 0), ("s", 1): (16, 0)}
    backbone = ET.fromstring(edge("backbone", ("s", 0), ("s", 1), points))
    assert backbone.get("data-edge-kind") == "backbone"
    assert backbone.get("stroke-opacity") == "0"


def test_noncanonical_contact_has_a_distinct_shape_without_losing_addresses():
    from xml.etree import ElementTree as ET

    from hop_design.export.construction.molecular.inspection_scene import edge

    points = {("s", 0): (20, 0), ("s", 9): (20, 44)}
    contact = ET.fromstring(edge("pair", ("s", 0), ("s", 9), points, pair_kind="gt_wobble"))
    assert contact.get("data-pair-kind") == "gt_wobble"
    assert contact.get("data-from") == '["s",0]'
    assert contact.get("data-contact-glyph") == "diamond"
    assert "Z" in contact.get("d")
    assert contact.get("stroke-dasharray") is None
    assert float(contact.get("stroke-width")) >= 2.4


def test_footprint_follows_the_strand_curve_with_constant_normal_width():
    from hop_design.export.construction.molecular.primitives.ribbon import ribbon_points

    shape = ribbon_points([(0, 0), (16, 0), (27, 11)], 15)
    n = len(shape) // 2
    sections = list(zip(shape[:n], reversed(shape[n:]), strict=True))
    centers = [((a[0] + b[0]) / 2, (a[1] + b[1]) / 2) for a, b in sections]
    assert any(abs(x - 8.3125) < 1e-8 and abs(y + 0.6875) < 1e-8 for x, y in centers)
    assert all(
        ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5 == pytest.approx(30) for a, b in sections
    )
