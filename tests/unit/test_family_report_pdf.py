"""Portable PDFs must carry the scientific symbols instead of missing-glyph boxes."""

import pytest

from hop_design.export.construction.scaffold.report_pdf import render_report_pdf


def test_unavailable_pdf_glyph_rejects_before_export():
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="50">'
        "<text>\U0010ffff</text></svg>"
    ).encode()
    with pytest.raises(ValueError, match="glyph"):
        render_report_pdf((svg,))


@pytest.mark.parametrize("leading", [False, True])
def test_accessible_tooltip_is_not_printed_as_a_second_terminal_label(leading):
    plain = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="50">'
        '<text x="10" y="25" font-size="16">5\u2032</text></svg>'
    ).encode()
    text = (
        "<title>5\u2032OH</title>5\u2032<desc>Hydroxyl terminus</desc>"
        if leading
        else "5\u2032<title>5\u2032OH</title><desc>Hydroxyl terminus</desc>"
    )
    described = plain.replace("5\u2032</text>".encode(), (text + "</text>").encode())
    assert render_report_pdf((described,)) == render_report_pdf((plain,))


def test_dna_polarity_and_direction_are_portable_glyphs():
    from pathlib import Path

    from reportlab.pdfbase.ttfonts import TTFont

    import hop_design

    font = TTFont(
        "coverage-test", str(Path(hop_design.__file__).parent / "assets/fonts/DejaVuSans.ttf")
    )
    assert all(ord(c) in font.face.charToGlyph for c in "ACGT5\u20323\u2032→○│\u2013")
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="50">'
        "<text>5\u2032→3\u2032</text></svg>"
    ).encode()
    assert render_report_pdf((svg,)).startswith(b"%PDF-")
