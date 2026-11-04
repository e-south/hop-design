"""Reserve label bounds for both the SVG face and the bundled PDF face."""

from reportlab.pdfbase.pdfmetrics import stringWidth  # type: ignore[import-untyped]

from ....fonts import report_font_name


def text_width(text: str, size: float, *, bold: bool = False) -> float:
    svg_width = stringWidth(text, "Helvetica-Bold" if bold else "Helvetica", size)
    pdf_width = stringWidth(text, report_font_name(), size)
    return float(max(svg_width, pdf_width))
