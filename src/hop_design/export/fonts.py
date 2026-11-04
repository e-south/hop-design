"""Shared bundled PDF font registration for encoding and layout measurements."""

from functools import lru_cache
from pathlib import Path

from reportlab.pdfbase import pdfmetrics  # type: ignore[import-untyped]
from reportlab.pdfbase.ttfonts import TTFont  # type: ignore[import-untyped]

REPORT_FONT_PATH = Path(__file__).parents[1] / "assets/fonts/DejaVuSans.ttf"


@lru_cache(maxsize=1)
def report_font_name() -> str:
    """Register the packaged face once; never depend on installed system fonts."""
    name = "HOPReport"
    if name not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(name, str(REPORT_FONT_PATH)))
    return name
