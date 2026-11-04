"""Annotation classes share one collision domain around exact molecular geometry."""


def test_collinear_obstacles_merge_without_closing_gaps_or_inflating_bounds():
    from hop_design.export.construction.molecular.label_layout import coalesce_horizontal

    assert coalesce_horizontal(
        [(0, 20, 20, 28), (16, 20, 20, 28), (40, 20, 20, 28), (0, 52, 20, 28)]
    ) == [(0, 20, 36, 28), (40, 20, 20, 28), (0, 52, 20, 28)]


def test_annotation_placement_avoids_bases_and_other_annotation_kinds():
    from hop_design.export.construction.molecular.label_layout import LabelPlacer

    placer = LabelPlacer([(20, 50, 300, 30)])
    boxes = [
        placer.place(25, 70, text, size=13)
        for text in ("BsaI recognition", "planned nick", "source reverse primer", "left gap: 6 bp")
    ]
    assert len(set(boxes)) == len(boxes)
    for i, (x, y, w, h) in enumerate(boxes):
        for a, b, c, d in [(20, 50, 300, 30), *boxes[:i]]:
            assert x + w <= a or a + c <= x or y + h <= b or b + d <= y
        assert y >= 40


def test_placement_uses_available_clearance_instead_of_skipping_to_a_distant_row():
    from hop_design.export.construction.molecular.label_layout import LabelPlacer

    placer = LabelPlacer([(20, 76, 300, 48)])
    _, top, _, height = placer.place(25, 76, "BsaI", size=24)
    assert top >= 40 and top + height + 4 <= 76


def test_labels_measure_glyph_width_instead_of_character_count():
    from hop_design.export.construction.molecular.label_layout import LabelPlacer

    narrow = LabelPlacer().place(40, 80, "iiii", size=40)
    wide = LabelPlacer().place(40, 80, "WWWW", size=40)
    assert wide[2] > 3 * narrow[2]


def test_local_side_clearance_is_used_before_a_distant_vertical_row():
    from hop_design.export.construction.molecular.label_layout import LabelPlacer

    x, y, _, _ = LabelPlacer([(80, 40, 30, 300)]).place(85, 200, "Nickase", size=24)
    assert x >= 116
    assert 150 <= y <= 210


def test_continuation_labels_stay_within_the_print_window():
    from hop_design.export.construction.molecular.label_layout import LabelPlacer

    placer = LabelPlacer([(200, 40, 300, 100)], horizontal_bounds=(200, 500))
    x, y, width, _ = placer.place(210, 100, "Nickase", size=24)
    assert x >= 200 and x + width <= 500
    assert y >= 146


def test_related_annotation_lines_are_placed_as_one_collision_group():
    import json
    from xml.etree import ElementTree as ET

    from hop_design.export.construction.molecular.label_layout import LabelPlacer

    placer = LabelPlacer([(90, 80, 200, 200)])
    root = ET.fromstring(
        placer.block(
            95,
            100,
            [
                ("primer-binding", "Reverse", "#123", 48),
                ("primer-chemistry", "5\u2032P → 3\u2032OH", "#123", 32),
            ],
        )
    )
    labels = list(root)
    a, b = [json.loads(e.get("data-label-box")) for e in labels]
    assert a[0] == b[0]
    assert 6 <= b[1] - a[1] - a[3] <= 12
    x, y, w, h = placer.occupied[-1]
    assert x + w <= 90 or x >= 290 or y + h <= 80 or y >= 280
    assert y <= a[1] and y + h >= b[1] + b[3]


def test_neighboring_enzyme_labels_reserve_the_embedded_pdf_font_width():
    from reportlab.pdfbase import pdfmetrics

    from hop_design.export.construction.molecular.label_layout import LabelPlacer
    from hop_design.export.construction.scaffold.report_pdf import render_report_pdf

    # The actual PDF encoder chooses this bundled font, which is wider than
    # Helvetica for these names. A nonoverlapping Helvetica box is insufficient.
    render_report_pdf(
        (
            b'<svg xmlns="http://www.w3.org/2000/svg" width="100" height="40">'
            b'<text x="0" y="20">Font contract</text></svg>',
        )
    )
    placer = LabelPlacer()
    names = ("Nb.BsrDI *", "BsaI-HFv2 *")
    boxes = [placer.place(x, 125, name, size=48) for x, name in zip((492, 364), names, strict=True)]
    for (_, _, reserved_width, _), name in zip(boxes, names, strict=True):
        assert reserved_width >= pdfmetrics.stringWidth(name, "HOPReport", 48)
