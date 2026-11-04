"""Composed molecular plates stay valid when the shared plot uses default SVG names."""

from xml.etree import ElementTree as ET

from hop_design.export.construction.molecular.plate import sequence_plates
from hop_design.export.construction.survey.plot import SVG


def test_sequence_plate_has_one_namespace_and_preserves_each_molecular_drawing():
    drawings = [
        (
            f'<svg xmlns="{SVG}" viewBox="0 0 120 {height}">'
            f'<text data-molecule="{i}">Molecule {i}</text></svg>'
        ).encode()
        for i, height in enumerate((40, 60, 80))
    ]
    pages = [ET.fromstring(page) for page in sequence_plates(drawings)]
    assert len(pages) == 2
    assert all(page.tag == f"{{{SVG}}}svg" for page in pages)
    assert pages[0].get("viewBox") == "0 0 120.0 100.0"
    assert [(child.get("y"), child.get("height")) for child in pages[0]] == [
        ("0.0", "40.0"),
        ("40.0", "60.0"),
    ]
    assert [e.text for page in pages for e in page.iter() if e.get("data-molecule")] == [
        "Molecule 0",
        "Molecule 1",
        "Molecule 2",
    ]
