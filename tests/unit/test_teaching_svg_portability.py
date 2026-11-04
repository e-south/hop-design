"""Invisible hit regions must remain invisible in SVG 1.1 publication renderers."""

from xml.etree import ElementTree as ET

from hop_design.export.construction.molecular.teaching_canvas import TeachingCanvas


def test_bracket_hit_area_has_explicit_zero_opacity_instead_of_a_css_color_keyword():
    canvas = TeachingCanvas(
        {
            "parameters": [
                {
                    "key": "left_gap",
                    "value": 0,
                    "value_label": "0",
                    "effective_requirement_differs": False,
                    "domain": {},
                    "definition": {
                        "label": "Left gap",
                        "symbol": "eL",
                        "unit": "bp",
                        "representation": "span",
                    },
                }
            ]
        }
    )
    canvas.bracket(canvas.root, "left_gap", 10, 10, 20)
    root = ET.fromstring(ET.tostring(canvas.root))
    hit = next(e for e in root.iter() if e.tag.endswith("}rect"))
    assert hit.get("fill-opacity") == "0"
    assert hit.get("fill") != "transparent"
    assert float(hit.get("width")) > 0  # A zero gap remains pointer-accessible.
