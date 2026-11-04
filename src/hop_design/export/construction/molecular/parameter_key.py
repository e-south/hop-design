"""A compact product-first teaching strip; complete definitions remain in metadata."""

import json
from math import ceil
from typing import Any, cast
from xml.etree import ElementTree as ET

from ..presentation.print_contract import PUBLICATION
from ..presentation.regions import REGIONS
from .teaching_canvas import TeachingCanvas

WIDTH = 1200
FONT = ceil(PUBLICATION.units(PUBLICATION.annotation_pt, canvas_width=WIDTH))


class DefinitionCanvas(TeachingCanvas):
    def __init__(self, key: dict[str, Any]) -> None:
        super().__init__({"parameters": []})
        self.parameters = {p["definition"]["key"]: p for p in key["parameters"]}
        self.root.attrib.update(
            {
                "viewBox": f"0 0 {WIDTH} 360",
                "width": "7in",
                "height": "2.1in",
                "font-size": str(FONT),
                "data-schema": key["schema"],
                "aria-label": "Molecular design features; schematic, not to scale",
            }
        )
        self.element(self.root, "rect", width=WIDTH, height=360, fill="white")
        self.element(self.root, "metadata").text = json.dumps(key, sort_keys=True)

    def group(self, parent: ET.Element, *keys: str) -> ET.Element:
        if not keys or any(k not in self.parameters for k in keys):
            raise ValueError("Every symbolic feature needs registered parameter definitions.")
        group = self.element(parent, "g", data_teaching_keys=json.dumps(keys), tabindex=0)
        meanings = "; ".join(
            f"{self.parameters[k]['definition']['label']}: "
            f"{self.parameters[k]['definition']['measurement']}"
            for k in keys
        )
        group.set("aria-label", meanings)
        self.element(group, "title").text = meanings
        return group

    def feature_label(self, x: float, y: float, lines: tuple[str, ...], *keys: str) -> ET.Element:
        group = self.group(self.root, *keys)
        for i, line in enumerate(lines):
            self.text(group, x, y + i * (FONT + 2), line, text_anchor="middle")
        return group

    def span(self, a: float, b: float, y: float, lines: tuple[str, ...], *keys: str) -> None:
        group = self.feature_label(
            (a + b) / 2, y - 12 - (len(lines) - 1) * (FONT + 2), lines, *keys
        )
        self.path(group, f"M {a} {y + 5} v -10 H {b} v 10")


def render_parameter_definition_key(key: dict[str, Any]) -> bytes:
    """Teach locatable features first; avoid presenting derived quantities as knobs."""
    if key.get("schema") != "hop.parameter-definition-key/v1":
        raise ValueError("Unknown molecular parameter definition key.")
    c = DefinitionCanvas(key)
    root = c.root
    for x, width, region in (
        (20, 290, "assembly"),
        (320, 390, "closing"),
        (750, 430, "interfaces"),
    ):
        label, color = REGIONS[region]
        group = c.element(root, "g", data_region=region)
        c.region(group, x, 8, width, 33, color)
        c.text(group, x + width / 2, 32, label, text_anchor="middle", font_weight=600)
    # One folded hairpin: basal association, supplied stem, closing extension.
    for x, width, color in ((120, 155, "#BDD9EC"), (275, 155, "#F0C9CE"), (430, 165, "#CDE1D2")):
        c.region(root, x, 162, width, 36, color)
    c.path(root, "M 35 125 H 85 L 120 170 H 595 C 680 110 680 250 595 190 H 120 L 85 235 H 35")
    for x in range(127, 595, 12):
        c.path(root, f"M {x} 170 v 20")
    c.text(root, 17, 130, "5\u2032")
    c.text(root, 17, 240, "3\u2032")
    c.feature_label(60, 67, ("5\u2032 tail",), "five_prime_unpaired_nt")
    c.feature_label(72, 275, ("3\u2032 tail",), "three_prime_unpaired_nt")
    c.span(120, 275, 112, ("Basal paired", "extent (positions)"), "open_side_paired_positions")
    c.span(430, 595, 112, ("Loop-side", "extension (bp)"), "foldback_arm_bp")
    c.feature_label(640, 276, ("Loop size (nt)", "and sequence"), "loop_nt", "loop_word")
    c.path(root, "M 640 243 V 211", stroke_dasharray="3 3")
    c.text(root, 352, 226, "Supplied stem", text_anchor="middle", fill="#70454E")
    c.feature_label(214, 301, ("Contact classes",), "noncanonical_pairs")
    c.path(root, "M 214 275 V 198", stroke_dasharray="3 3")
    # A separate molecular frame prevents projecting sticky ends onto the hairpin.
    for x, width, color in (
        (808, 67, "#BDD9EC"),
        (875, 85, "#F0C9CE"),
        (960, 80, "#CDE1D2"),
        (1040, 65, "#F0C9CE"),
        (1105, 45, "#BDD9EC"),
    ):
        c.region(root, x, 162, width, 36, color)
    c.path(root, "M 770 170 H 1150 M 808 190 H 1186")
    for x in range(816, 1150, 12):
        c.path(root, f"M {x} 170 v 20")
    c.text(root, 751, 175, "5\u2032")
    c.text(root, 1168, 164, "3\u2032")
    c.text(root, 782, 211, "3\u2032")
    c.text(root, 1169, 218, "5\u2032")
    c.feature_label(811, 93, ("Left end", "word + polarity"), "left_end_word", "left_end_polarity")
    c.feature_label(
        1100, 93, ("Right end", "word + polarity"), "right_end_word", "right_end_polarity"
    )
    c.path(root, "M 800 125 L 788 165 M 1135 125 L 1168 185", stroke_dasharray="3 3")
    c.span(808, 875, 268, ("Left gap", "(bp)"), "left_gap")
    c.span(1105, 1150, 268, ("Right gap", "(bp)"), "right_gap")
    c.text(root, 980, 303, "Sticky ends shown as 5\u2032 examples", text_anchor="middle")
    c.text(
        root,
        600,
        346,
        "Schematic; not to scale. Coupled features, not independent parts.",
        text_anchor="middle",
    )
    return cast(bytes, ET.tostring(root, encoding="utf-8"))
