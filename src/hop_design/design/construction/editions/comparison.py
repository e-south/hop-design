"""Compare captured complete route records without loading a live discovery."""

import json
from typing import TYPE_CHECKING, Any

from ..intents.base import Source
from ..packets.atlas import MolecularAtlasPacket

if TYPE_CHECKING:
    from .reader import AtlasEdition

from hop_design.models.construction.complete.realization import MaterializedConstructionRealization

from ..navigation.render_policy import renderer_identity
from ..navigation.route_comparison import compared_packet


def captured_route(edition: "AtlasEdition", identity: str) -> MaterializedConstructionRealization:
    from .materials import member_materials, route_from_materials

    return route_from_materials(member_materials(edition, identity), identity)


def comparison_provenance(edition: "AtlasEdition", *, redraw: bool) -> dict[str, Any]:
    return {
        "producer": edition.producer,
        "renderer": renderer_identity() if redraw else None,
        "edition_digest": edition.digest,
        "comparison_basis": "captured_complete_routes",
    }


def compare_captured(
    edition: "AtlasEdition",
    packet: MolecularAtlasPacket,
    selected: Source,
    reference: Source,
    *,
    redraw: bool = False,
    draw_route: bool = True,
) -> MolecularAtlasPacket:
    old = edition._selected(reference)
    new = edition._selected(selected)
    result = compared_packet(
        packet,
        captured_route(edition, old.materialized_realization_id),
        captured_route(edition, new.materialized_realization_id),
        reference_selection=old.model_dump(mode="json", by_alias=True),
        selection=new.model_dump(mode="json", by_alias=True),
        redraw=redraw,
        draw_route=draw_route,
    )
    summary = json.loads(result.json_bytes)
    summary.update(comparison_provenance(edition, redraw=redraw))
    updated = type(result)._create(dict(result._files), summary, result.report_text)
    object.__setattr__(updated, "_roots", result._roots)
    return updated
