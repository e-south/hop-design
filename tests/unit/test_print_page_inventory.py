"""A page inventory includes continued states, not only their first panels."""

from xml.etree import ElementTree as ET

from hop_design.export.construction.molecular.printing.blocks import paginate_panels
from hop_design.export.construction.molecular.printing.panels import ScenePanel


def test_page_inventory_names_continued_molecules():
    panels = [
        ScenePanel(ET.Element("g"), 1300, {"state_id": "state-a", "part": i, "parts": 2})
        for i in (1, 2)
    ]
    pages, layout = paginate_panels(panels, 1008, 0.5)
    assert len(pages) == 2
    assert [p["state_ids"] for p in layout["pages"]] == [["state-a"], ["state-a"]]
