"""Whole-scaffold comparisons must retain both terminal labels at a common scale."""

from types import SimpleNamespace as NS


def portrait(open_positions):
    # A schematic fixture with a 14-nt terminal handle, 32-bp stem and 9-bp extension.
    start = open_positions
    return NS(
        stem_primary_span=NS(start=NS(offset=start)),
        loop_span=NS(start=NS(offset=start + 41), end=NS(offset=start + 44)),
        loop_nt=3,
        state=NS(molecules=(NS(sequence="A" * (2 * start + 85 + 14)),)),
    )


def test_common_frame_keeps_extended_terminal_labels_inside_panel():
    from hop_design.export.construction.scaffold.discovery_plate import comparison_frame
    from hop_design.export.construction.scaffold.hairpin_layout import HairpinLayout

    portraits = [portrait(17), portrait(24), portrait(80)]
    scale, anchor = comparison_frame(portraits)
    assert 0 < scale <= 0.8
    for p in portraits:
        layout = HairpinLayout(p)
        translation = anchor - scale * layout.anchor
        for index in (0, len(p.state.molecules[0].sequence) - 1):
            # 40 native units include the end-anchored terminal glyph's width and gap.
            label_left = translation + scale * (layout.point(index)[0] - 40)
            assert label_left >= 24.99
        right_edge = translation + scale * (layout.loop_x + layout.radius)
        assert right_edge <= 455
        assert translation + scale * layout.anchor == anchor
