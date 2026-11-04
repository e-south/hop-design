"""Place two exact sequence drawings on one static comparison plate."""

from itertools import batched
from xml.etree import ElementTree as ET


def sequence_plates(drawings: list[bytes]) -> tuple[bytes, ...]:
    pages = []
    for pair in batched(drawings, 2):
        elements = [ET.fromstring(svg) for svg in pair]
        width = max(float(e.attrib["viewBox"].split()[2]) for e in elements)
        heights = [float(e.attrib["viewBox"].split()[3]) for e in elements]
        height = sum(heights)
        page = ET.Element(
            "{http://www.w3.org/2000/svg}svg",
            {
                "width": "240mm",
                "height": f"{240 * height / width:.2f}mm",
                "viewBox": f"0 0 {width} {height}",
            },
        )
        y = 0.0
        for element, h in zip(elements, heights, strict=True):
            element.attrib.update(x="0", y=str(y), width=str(width), height=str(h))
            page.append(element)
            y += h
        pages.append(ET.tostring(page))
    return tuple(pages)
