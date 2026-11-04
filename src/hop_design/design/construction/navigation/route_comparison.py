"""Attach the existing exact route comparison to a selected presentation packet."""

import json

from hop_design.export.construction.molecular.atlas import render_molecular_atlas
from hop_design.export.construction.molecular.teaching import render_parameter_teaching
from hop_design.models.construction.complete.realization import MaterializedConstructionRealization
from hop_design.models.construction.projections.atlas import MolecularAtlas
from hop_design.serialization import canonical_json_bytes

from ..packets.atlas import MolecularAtlasPacket
from ..projections.atlas_comparison import compare_route_atlases
from .types import Record


def compared_packet(
    packet: MolecularAtlasPacket,
    old: MaterializedConstructionRealization,
    new: MaterializedConstructionRealization,
    *,
    reference_selection: Record,
    selection: Record,
    redraw: bool = True,
    draw_route: bool = True,
) -> MolecularAtlasPacket:
    comparison = compare_route_atlases(
        old, new, reference=old.materialized_realization_id, option=new.materialized_realization_id
    )
    summary = json.loads(packet.json_bytes)
    summary.update(
        comparison=comparison.model_dump(mode="json"),
        selection=selection,
        reference_selection=reference_selection,
    )
    files = dict(packet._files)
    if redraw and draw_route:
        atlas = MolecularAtlas.model_validate_json(canonical_json_bytes(summary["atlas"]))
        files["projection.svg"] = render_molecular_atlas(
            atlas, comparison=comparison, parameter_locations=summary["parameter_locations"]
        )
        files["teaching.svg"] = render_parameter_teaching(
            summary["teaching"], atlas, summary["parameter_locations"], comparison=comparison
        )
    if redraw:
        files.pop("overview.svg", None)
    result = type(packet)._create(files, summary, packet.report_text)
    object.__setattr__(result, "_roots", packet._roots)
    return result
