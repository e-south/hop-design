"""Pack exact input orders near their operation, without changing binding meaning."""

from xml.etree import ElementTree as ET

from hop_design.models.construction.projections.atlas import AtlasComparison, AtlasMaterialInput

from ...labels import drawing_material_label, material_role_label, terminal_label
from .style import ANNOTATION_SIZE, INK, object_id
from .typography import text_width

SVG = "http://www.w3.org/2000/svg"


def draw_inputs(
    root: ET.Element,
    inputs: tuple[AtlasMaterialInput, ...],
    width: float,
    top: float,
    comparison: AtlasComparison | None,
) -> tuple[float, float]:
    """One row when possible; wrap whole oligos rather than reduce sequence type."""
    x, y, bottom = 28.0, top, top
    for item in inputs:
        role = material_role_label(item.material_use.role)
        name = drawing_material_label(item.material_use.role)
        if comparison and item.material_use.role.value in comparison.material_roles:
            role += " · changed versus reference"
            name += " · changed"
        label = f"{name} · {len(item.material.sequence_5prime)} nt"
        sequence = (
            terminal_label("5\u2032", item.material.five_prime_end)
            + " "
            + item.material.sequence_5prime
            + " "
            + terminal_label("3\u2032", item.material.three_prime_end)
        )
        extent = max(len(sequence) * 16 * 0.64, text_width(label, ANNOTATION_SIZE))
        if x > 28 and x + extent + 28 > width:
            x, y = 28.0, bottom + 24
        group = ET.SubElement(
            root,
            f"{{{SVG}}}g",
            {
                "id": object_id("input", item.pre_state_id, item.material_use.use_id),
                "{http://www.inkscape.org/namespaces/inkscape}label": role,
                "data-atlas-input": item.material_use.use_id,
            },
        )
        ET.SubElement(group, f"{{{SVG}}}title").text = f"Binding context: {item.binding_context}"
        ET.SubElement(
            group,
            f"{{{SVG}}}text",
            {
                "x": str(x),
                "y": str(y),
                "font-size": str(ANNOTATION_SIZE),
                "fill": INK,
            },
        ).text = label
        ET.SubElement(
            group,
            f"{{{SVG}}}text",
            {
                "x": str(x),
                "y": str(y + 26),
                "font-size": "16",
                "font-family": "monospace",
                "fill": INK,
            },
        ).text = sequence
        width = max(width, x + extent + 28)
        bottom = max(bottom, y + 32)
        x += extent + 40
    return width, bottom
