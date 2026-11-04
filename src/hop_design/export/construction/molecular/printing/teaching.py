"""Print selected teaching panels without shrinking or repeating nucleotide glyphs."""

import json
from copy import deepcopy
from typing import Any
from xml.etree import ElementTree as ET

from hop_design.serialization import canonical_json_bytes

from ...presentation.print_contract import PUBLICATION
from ...scaffold.report_pdf import render_report_pdf
from .blocks import paginate_panels
from .panels import ScenePanel


def paginate_teaching(svg: bytes) -> tuple[tuple[bytes, ...], dict[str, Any]]:
    root = ET.fromstring(svg)
    if root.get("data-teaching-resolution") != "every-base":
        raise ValueError("Readable teaching pages require an exact selected drawing.")
    width = float(root.attrib["viewBox"].split()[2])
    scale = PUBLICATION.width_pt / width
    panels = []
    for element in root.iter():
        if not element.get("data-teaching-continuation"):
            continue
        panel = deepcopy(element)
        panel.attrib.pop("transform", None)
        panels.append(
            ScenePanel(
                panel,
                float(element.attrib["data-panel-height"]),
                json.loads(element.attrib["data-teaching-continuation"]),
            )
        )
    pages, layout = paginate_panels(
        panels,
        width,
        scale,
        title="Selected molecular measurements",
        schema="hop.parameter-teaching-print/v1",
        shared_definitions=root.find("{http://www.w3.org/2000/svg}defs"),
    )
    return pages, {**layout, "materialized_realization_id": root.attrib["data-preparation-id"]}


def teaching_print_files(svg: bytes) -> dict[str, bytes]:
    pages, layout = paginate_teaching(svg)
    return {
        "teaching.pdf": render_report_pdf(pages, title="HOP selected molecular measurements"),
        "teaching-layout.json": canonical_json_bytes(layout),
        **{f"teaching-pages/{i:02}.svg": page for i, page in enumerate(pages, 1)},
    }
