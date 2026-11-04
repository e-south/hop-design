"""Deterministic vector PDF encoding of HOP-generated SVG pages."""

from hashlib import sha256
from importlib.metadata import version
from io import BytesIO
from xml.etree import ElementTree as ET

from pydantic import JsonValue
from reportlab.graphics import renderPDF  # type: ignore[import-untyped]
from reportlab.pdfbase import pdfmetrics  # type: ignore[import-untyped]
from reportlab.pdfgen.canvas import Canvas  # type: ignore[import-untyped]
from svglib.svglib import svg2rlg

from ...fonts import REPORT_FONT_PATH, report_font_name


def render_report_pdf(pages: tuple[bytes, ...], *, title: str = "HOP scaffold comparison") -> bytes:
    """Only generated SVG reaches this encoder; no user SVG or external resources."""
    font_name = report_font_name()
    glyphs = pdfmetrics.getFont(font_name).face.charToGlyph
    output = BytesIO()
    canvas = Canvas(output, invariant=1, pageCompression=1)
    canvas.setTitle(title)
    canvas.setAuthor("HOP Design")
    for page in pages:
        root = ET.fromstring(page)
        # SVG descriptions are accessible metadata, not visible text. svglib
        # otherwise renders a title nested inside a text node a second time.
        for parent in root.iter():
            for child in list(parent):
                if child.tag.rsplit("}", 1)[-1] in {"title", "desc"}:
                    if child.tail:
                        index = list(parent).index(child)
                        if index:
                            previous = parent[index - 1]
                            previous.tail = (previous.tail or "") + child.tail
                        else:
                            parent.text = (parent.text or "") + child.tail
                    parent.remove(child)
        texts = ("".join(e.itertext()) for e in root.iter() if e.tag.rsplit("}", 1)[-1] == "text")
        missing = sorted(
            {ord(c) for value in texts for c in value if not c.isspace() and ord(c) not in glyphs}
        )
        if missing:
            raise ValueError(f"PDF font lacks required glyphs: {missing}.")
        page = ET.tostring(root, encoding="utf-8")
        drawing = svg2rlg(
            BytesIO(page.replace(b"Arial, Helvetica, sans-serif", font_name.encode()))
        )
        if drawing is None:
            raise ValueError("Could not encode the generated molecular report page.")
        canvas.setPageSize((drawing.width, drawing.height))
        renderPDF.draw(drawing, canvas, 0, 0)
        canvas.showPage()
    canvas.save()
    return output.getvalue()


def rendering_identity() -> dict[str, JsonValue]:
    return {
        **{name: version(name) for name in ("reportlab", "svglib", "lxml")},
        "font_sha256": sha256(REPORT_FONT_PATH.read_bytes()).hexdigest(),
        "font": "DejaVu Sans 2.37 (bundled with HOP)",
        "pdf_mode": "invariant-vector",
    }
