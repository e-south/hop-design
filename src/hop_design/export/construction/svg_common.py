"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/export/construction/svg_common.py

Provides shared SVG document and text helpers for construction projections.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import html

INK = "#17211d"
MUTED = "#5b6661"
RULE = "#cbd3cf"
ACCENT = "#176b54"
WASH = "#eef4f1"


def escape(value: object) -> str:
    """Escape one value for XML text or attribute content."""
    return html.escape(str(value), quote=True)


def short_id(value: str | None) -> str:
    """Return the compact digest suffix used only in rendered labels."""
    if value is None:
        return ""
    stem = value.removesuffix("@1")
    return stem.rsplit("/", 1)[-1][:10]


def render_document(
    *,
    title: str,
    body: str,
    height: int,
    description: str = "Neutral scientific projection of typed local construction discovery.",
) -> bytes:
    """Wrap one typed construction projection in an accessible SVG document."""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="{height}"
viewBox="0 0 1200 {height}" role="img" aria-labelledby="figure-title figure-description">
<title id="figure-title">{escape(title)}</title>
<desc id="figure-description">{escape(description)}</desc>
<style>
text {{ fill:{INK}; font-family:Arial, Helvetica, sans-serif; }}
.title {{ font-size:28px; font-weight:700; }}
.subtitle {{ font-size:17px; fill:{MUTED}; }}
.label {{ font-size:14px; font-weight:700; letter-spacing:.04em; text-transform:uppercase; }}
.body {{ font-size:16px; }}
.small {{ font-size:13px; fill:{MUTED}; }}
.rule {{ stroke:{RULE}; stroke-width:1.5; }}
</style>
<rect width="100%" height="100%" fill="#ffffff"/>
{body}
</svg>
""".encode()


__all__ = ["ACCENT", "WASH", "escape", "render_document", "short_id"]
