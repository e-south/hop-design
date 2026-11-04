"""SVG primitives for the shared, coordinate-defined teaching key."""

import json
from typing import Any
from xml.etree import ElementTree as ET


class TeachingCanvas:
    def __init__(self, teaching: dict[str, Any]) -> None:
        self.parameters = {p["key"]: p for p in teaching["parameters"]}
        self.covered: set[str] = set()
        self.root = ET.Element(
            "svg",
            {
                "xmlns": "http://www.w3.org/2000/svg",
                "viewBox": "0 0 1200 340",
                "role": "group",
                "aria-label": "Molecular parameter key for one complete preparation",
                "font-family": "Arial, Helvetica, sans-serif",
                "font-size": "12",
                "fill": "#243740",
            },
        )

    def element(self, parent: ET.Element, tag: str, **attrs: Any) -> ET.Element:
        return ET.SubElement(parent, tag, {k.replace("_", "-"): str(v) for k, v in attrs.items()})

    def text(self, parent: ET.Element, x: float, y: float, text: str, **attrs: Any) -> None:
        self.element(parent, "text", x=x, y=y, **attrs).text = text

    def path(self, parent: ET.Element, d: str, **attrs: Any) -> None:
        self.element(parent, "path", d=d, fill="none", stroke="#40535B", stroke_width=1.6, **attrs)

    def region(
        self, parent: ET.Element, x: float, y: float, w: float, h: float, color: str
    ) -> None:
        self.element(
            parent, "rect", x=x, y=y, width=w, height=h, rx=3, fill=color, fill_opacity=0.5
        )

    def group(self, parent: ET.Element, *keys: str) -> ET.Element:
        keys = tuple(k for k in keys if k in self.parameters)
        self.covered.update(keys)
        group = self.element(
            parent,
            "g",
            data_teaching_keys=json.dumps(keys),
            tabindex=0,
            role="button",
            cursor="pointer",
        )
        meanings = [f"{self.parameters[k]['definition']['label']}: {self.label(k)}" for k in keys]
        group.set("aria-label", "; ".join(meanings))
        self.element(group, "title").text = "; ".join(meanings)
        return group

    def value(self, key: str, default: Any = 0) -> Any:
        p = self.parameters.get(key)
        return p["value"] if p and p["value"] is not None else default

    def label(self, key: str) -> str:
        p = self.parameters[key]
        label = str(p["value_label"]) + (
            f" {p['definition']['unit']}" if p["definition"]["unit"] else ""
        )
        if p["effective_requirement_differs"]:
            requested = ", ".join(map(str, p["domain"]["values"]))
            label += f" · requested {requested}"
        return label

    def bracket(
        self,
        parent: ET.Element,
        key: str,
        a: float,
        z: float,
        y: float,
        label: str | None = None,
        *also: str,
    ) -> None:
        g = self.group(parent, key, *also)
        threshold = self.parameters[key]["definition"]["representation"] == "threshold"
        self.element(
            g,
            "rect",
            x=min(a, z) - 3,
            y=y - 19,
            width=max(10, abs(z - a) + 6),
            height=28,
            fill="#FFFFFF",
            fill_opacity=0,
        )
        self.path(
            g, f"M {a} {y + 4} v -7 H {z} v 7", stroke_dasharray="3 2" if threshold else "none"
        )
        text = label or (
            self.parameters[key]["definition"]["symbol"]
            or self.parameters[key]["definition"]["label"]
        )
        self.text(
            g, (a + z) / 2, y - 8, f"{text}: {self.label(key)}", text_anchor="middle", font_size=11
        )
        g.set("data-threshold", str(threshold).lower())
