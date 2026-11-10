"""Shared inspector refinements preserve the recorded molecular authority."""

import json
from xml.etree import ElementTree as ET

from tests.integration.test_atlas_assembly import atlas  # noqa: F401


def test_partial_upper_handle_site_uses_recorded_complementary_row(atlas):  # noqa: F811
    from hop_design.export.construction.molecular.assembly.placement import assembly_points
    from hop_design.export.construction.molecular.recognition_sites import recognition_site_overlays

    state = next(s for s in atlas.states if s.state.phase.value == "annealed_complex")
    points = assembly_points(atlas)[state.state.state_id]
    site = next(
        s
        for s in state.recognition_sites
        if s.role == "end_generation" and s.presence == "partial" and s.recognition
    )
    root = ET.fromstring("<svg>" + recognition_site_overlays(state, points) + "</svg>")
    group = next(e for e in root.iter() if e.get("data-site-id") == site.site_id)
    band = next(e for e in group if e.get("data-envelope-box"))
    y = min(points[a.strand_id, a.index][1] for a in site.recognition)
    _, top, _, height = json.loads(band.get("data-envelope-box"))
    assert top == y - 18
    assert top + height == y + 44 + 18


def test_reference_colliding_terminal_is_metadata_only():
    from hop_design.export.construction.molecular.assembly.annotations import (
        avoid_reference_label_collisions,
    )

    root = ET.fromstring(
        '<svg xmlns="http://www.w3.org/2000/svg">'
        '<g data-discarded-fragment-ghosts="true"><g data-ghost-base-index="0">'
        '<text x="40" y="45">A</text></g></g>'
        '<text data-label-kind="terminus" data-label-box="[36,30,25,20]" '
        'data-terminal-chemistry="5\u2032P" data-terminal-strand="retained" '
        'data-terminal-index="0">5\u2032P</text>'
        '<text data-label-kind="terminus" data-label-box="[200,30,25,20]" '
        'data-terminal-chemistry="5\u2032P" data-terminal-strand="other" '
        'data-terminal-index="0">5\u2032P</text></svg>'
    )
    avoid_reference_label_collisions(root)
    labels = [e for e in root.iter() if e.get("data-terminal-chemistry")]
    assert labels[0].get("data-terminal-display") == "metadata"
    assert not labels[0].tag.endswith("text")
    assert labels[0].get("data-terminal-strand") == "retained"
    assert labels[1].tag.endswith("text")


def test_auxiliary_enzyme_label_comes_from_recorded_catalog():
    from hop_design.design.construction.editions.materials import enzyme_labels_from_materials

    labels = {"example:enzyme/helper@1": "HelperNI"}
    files = {"preparation/enzyme-labels.json": json.dumps(labels).encode()}
    assert enzyme_labels_from_materials(files) == labels
    assert enzyme_labels_from_materials({}) == {}
