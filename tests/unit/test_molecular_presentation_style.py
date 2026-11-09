"""Shared contrast and transport rules preserve legibility without molecular changes."""

from xml.etree import ElementTree as ET

from hop_design.export.construction.molecular.atlas_placement import BlockExtent, place_route
from hop_design.export.construction.molecular.atlas_reading_order import continuation_svg
from hop_design.export.construction.molecular.primitives.operations import draw_operation
from hop_design.export.construction.molecular.primitives.style import (
    REGION_COLORS,
    base_ink,
    contrast_ratio,
)


def test_region_nucleotides_keep_small_type_contrast():
    for region, color in REGION_COLORS.items():
        assert contrast_ratio(base_ink(region), color) >= 4.5
        assert base_ink(region) == "#FFFFFF"
    assert base_ink("unmapped") != "#FFFFFF"
    assert base_ink("stem", "#DED2EC") != "#FFFFFF"


def test_route_transport_uses_one_short_arrow_vocabulary():
    root = ET.Element("svg")
    draw_operation(root, 200, 300, 800, "copy", "Copy")
    arrow = next(e for e in root if e.get("data-operation-arrow"))
    assert float(arrow.get("data-drawing-box").split()[-1]) <= 64
    layout = place_route((BlockExtent(800, 200, 200, "duplex"),) * 2)
    continuation = ET.fromstring(continuation_svg(layout))
    assert continuation[0].get("stroke-width") == arrow.get("stroke-width")
    assert float(continuation[0].get("stroke-opacity", "1")) == 1


def test_larger_nucleotides_preserve_the_iupac_pitch_budget():
    from hop_design.export.construction.molecular.primitives.typography import (
        fitted_base_size,
        text_width,
    )

    for base in "ACGTRYSWKMBDHVN":
        size = fitted_base_size(base, 20)
        assert text_width(base, size) < 16
    assert all(fitted_base_size(base, 20) == 20 for base in "ACGT")
    assert fitted_base_size("W", 20, pitch=0.1) > 0
