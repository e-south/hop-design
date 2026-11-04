"""A zero extent at a terminus sits outside its base, at the covalent boundary."""

from xml.etree import ElementTree as ET

from hop_design.export.construction.molecular.parameter_boundaries import add_parameter_boundaries


def test_terminal_zero_extent_uses_half_step_outward_from_last_base():
    root = ET.fromstring("""<svg xmlns="http://www.w3.org/2000/svg">
      <g data-base-index="0" data-state-id="s" data-strand-id="a">
        <rect x="3" y="0" width="14" height="20"/></g>
      <g data-base-index="1" data-state-id="s" data-strand-id="a">
        <rect x="19" y="0" width="14" height="20"/></g>
    </svg>""")
    edge = {"before": {"state_id": "s", "strand_id": "a", "index": 1}, "after": None}
    add_parameter_boundaries(
        root,
        [
            {
                "key": "three_prime_unpaired_nt",
                "zero_extent": True,
                "definition": {"representation": "span", "label": "3-prime tail"},
                "boundary_anchors": [{"start": edge, "end": edge}],
            }
        ],
    )
    path = next(e for e in root.iter() if e.tag == "path")
    assert path.attrib["d"].startswith("M 34.0 ")
