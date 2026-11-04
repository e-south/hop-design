"""Mark literal equal-length hairpin differences without inferring an alignment."""

from xml.etree import ElementTree as ET

from hop_design.models.construction.projections.hairpin import HairpinPortraitProjection


def mark_sequence_changes(
    content: bytes, portrait: HairpinPortraitProjection, reference: HairpinPortraitProjection
) -> bytes:
    before = reference.state.molecules[0].sequence
    after = portrait.state.molecules[0].sequence
    if len(before) != len(after):
        return content
    changed = {i for i, (a, b) in enumerate(zip(before, after, strict=True)) if a != b}
    root = ET.fromstring(content)
    for item in root.iter():
        index = item.get("data-backbone-index")
        if index is not None and int(index) in changed:
            item.set("stroke", "#8B4A89")
            item.set("stroke-width", "5")
            item.set("data-sequence-change", "substitution")
    return ET.tostring(root)
