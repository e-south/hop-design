"""Presentation measures blocks without resizing their molecular geometry."""

import pytest

from hop_design.export.construction.molecular.atlas_placement import BlockExtent, place_route


def block(height=200, width=800, phase="duplex"):
    return BlockExtent(width, height, 200, phase)


def test_wide_finishing_state_does_not_change_earlier_block_dimensions():
    blocks = (
        block(),
        block(250),
        block(200, 4000, "hairpin_pcr_duplex"),
        block(200, 3000, "clone_ready_duplex"),
    )
    placement = place_route(blocks)
    assert placement.width == 4064
    assert [p.column for p in placement.positions] == ["0", "1", "full", "full"]
    assert placement.positions[-2].x == 32
    assert placement.positions[-1].x == 532
    assert all(p.x >= 0 and p.y >= 0 for p in placement.positions)
    assert blocks[0] == block()


def test_hairpin_endpoint_has_no_fictitious_copy_or_release_stage():
    blocks = (block(200), block(300), block(200, phase="foldback_closed_hairpin"))
    layout = place_route(blocks)
    assert len(layout.positions) == 3
    assert {p.column for p in layout.positions} == {"0", "1"}
    for p, b in zip(layout.positions, blocks, strict=True):
        assert p.x + b.width <= layout.width
        assert p.y + b.height <= layout.height


def test_column_spacing_follows_content_instead_of_stretching_the_short_column():
    from hop_design.export.construction.molecular.atlas_placement import GAP

    blocks = (block(100), block(100), block(180), block(180), block(100))
    layout = place_route(blocks)
    for index in range(len(blocks) - 1):
        a, b = layout.positions[index : index + 2]
        if a.column == b.column:
            assert b.y - a.y - blocks[index].height == GAP


@pytest.mark.parametrize(
    "blocks",
    [(), (block(0),), (block(float("nan")),), (block(phase="clone_ready_duplex"), block())],
)
def test_invalid_geometry_is_rejected(blocks):
    with pytest.raises(ValueError):
        place_route(blocks)


def test_column_connector_has_rounded_corners_and_a_visible_arrowhead():
    from xml.etree import ElementTree as ET

    from hop_design.export.construction.molecular.atlas_reading_order import continuation_svg

    root = ET.fromstring(continuation_svg(place_route((block(), block()))))
    path = next(e for e in root if e.tag.endswith("}path"))
    assert path.get("d").count("Q") >= 2
    assert 0 < float(path.get("stroke-width")) < 4
    assert not path.get("stroke-dasharray")


def test_column_turn_has_clearance_before_full_width_finish():
    layout = place_route((block(), block(), block(phase="hairpin_pcr_duplex")))
    assert layout.continuation is not None
    assert layout.positions[-1].y - (layout.continuation[1] + 24) >= 24


def test_column_transport_is_quieter_than_local_processing_arrows():
    from xml.etree import ElementTree as ET

    from hop_design.export.construction.molecular.atlas_reading_order import continuation_svg

    root = ET.fromstring(continuation_svg(place_route((block(), block()))))
    assert float(root[0].get("stroke-width")) < 4
