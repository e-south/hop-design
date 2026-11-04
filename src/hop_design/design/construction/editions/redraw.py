"""Current glyphs over captured records; failed schema adaptation keeps original artwork."""

import json

from pydantic import ValidationError

from hop_design.export.construction.molecular.atlas import render_molecular_atlas
from hop_design.export.construction.molecular.teaching import render_parameter_teaching
from hop_design.models.construction.projections.atlas import AtlasComparison, MolecularAtlas
from hop_design.serialization import canonical_json_bytes

from ..navigation.render_policy import rendering_receipt
from ..packets.atlas import MolecularAtlasPacket


def redraw_captured(
    packet: MolecularAtlasPacket, *, draw_route: bool = True
) -> MolecularAtlasPacket:
    summary = json.loads(packet.json_bytes)
    try:
        atlas = MolecularAtlas.model_validate_json(canonical_json_bytes(summary["atlas"]))
    except ValidationError:
        return rendering_receipt(
            packet,
            "current",
            "captured",
            notice=(
                "This captured molecular schema is not supported by the current renderer. "
                "The original artwork is retained."
            ),
        )
    files = dict(packet._files)
    comparison = (
        AtlasComparison.model_validate_json(canonical_json_bytes(summary["comparison"]))
        if summary.get("comparison") is not None
        else None
    )
    if draw_route:
        files["projection.svg"] = render_molecular_atlas(
            atlas, parameter_locations=summary["parameter_locations"], comparison=comparison
        )
        files["teaching.svg"] = render_parameter_teaching(
            summary["teaching"], atlas, summary["parameter_locations"], comparison=comparison
        )
    files.pop("overview.svg", None)
    result = type(packet)._create(files, summary, packet.report_text)
    object.__setattr__(result, "_roots", packet._roots)
    return rendering_receipt(result, "current", "current")
