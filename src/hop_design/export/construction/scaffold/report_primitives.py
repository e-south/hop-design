"""Common static page assembly; no molecular or selection semantics."""

from html import escape
from xml.etree import ElementTree as ET


def text(x: float, y: float, value: str, size: int = 16) -> str:
    return f'<text x="{x}" y="{y}" font-size="{size}">{escape(value)}</text>'


def page(title: str, rows: list[str], *, height: int = 900) -> bytes:
    return (
        "\n".join(
            [
                f'<svg xmlns="http://www.w3.org/2000/svg" width="180mm" '
                f'height="{height / 5}mm" viewBox="0 0 900 {height}">',
                '<rect width="900" height="100%" fill="white"/>',
                '<g font-family="Arial, Helvetica, sans-serif" fill="#23313B">',
                text(25, 35, title, 24),
                *rows,
                "</g></svg>",
            ]
        )
    ).encode()


def embed(content: bytes, x: float, y: float, width: float, *, shape_only: bool = False) -> str:
    root = ET.fromstring(content)
    native_width = float(root.attrib["viewBox"].split()[2])
    root.set("width", str(native_width))
    root.set("height", root.attrib["viewBox"].split()[3])
    shape = next(e for e in root.iter() if e.get("id") == "hairpin-shape") if shape_only else root
    return (
        f'<g transform="translate({x},{y}) scale({width / native_width})">'
        + ET.tostring(shape, encoding="unicode")
        + "</g>"
    )


def drawing_fragment(
    content: bytes, *, hairpin: bool = False, annotate: bool = False, height: int = 170
) -> bytes:
    """Remove repeated annotations only; preserve all molecular marks and identities."""
    root = ET.fromstring(content)
    if hairpin:
        shape = next(e for e in root.iter() if e.get("id") == "hairpin-shape")
        for e in list(shape):
            tag = e.tag.rsplit("}", 1)[-1]
            if tag == "text":
                if e.text in ("5\u2032", "3\u2032"):
                    e.set("font-size", "23")
                elif annotate:
                    e.set("font-size", "17")
                else:
                    shape.remove(e)
            elif not annotate and tag == "path" and e.get("data-backbone-index") is None:
                shape.remove(e)
    else:
        for parent in root.iter():
            for e in list(parent):
                if e.tag.endswith("}text") and float(e.get("y", "0")) >= height:
                    parent.remove(e)
        box = root.attrib["viewBox"].split()
        root.set("viewBox", " ".join([*box[:3], str(height)]))
    return ET.tostring(root)
