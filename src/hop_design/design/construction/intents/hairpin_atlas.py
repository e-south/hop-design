"""Recorded hairpin inspection and comparison, independent of query authoring."""

import json
from typing import TYPE_CHECKING

from ..packets.atlas import MolecularAtlasPacket
from ..variants.atlas import _inspect_scaffold_atlas
from .base import Source

if TYPE_CHECKING:
    from .hairpin_choices import HairpinDesignChoices


def inspect_hairpin(
    choices: "HairpinDesignChoices",
    selection: Source,
    reference_selection: Source | None,
    *,
    draw_route: bool = True,
) -> MolecularAtlasPacket:
    selected = choices._selected(selection)
    native = choices._native(selected["query"])
    summary = json.loads(native.json_bytes)
    packet: MolecularAtlasPacket = _inspect_scaffold_atlas(
        choices._pool,
        native,
        {
            "result_digest": choices._pool.result_digest,
            "query_digest": summary["query_digest"],
            "option_label": selected["option_label"],
        },
        draw_route=draw_route,
    )
    if reference_selection is not None:
        from ..navigation.route_comparison import compared_packet

        reference_owner = choices._for_selection(reference_selection)
        reference = reference_owner._selected(reference_selection)
        packet = compared_packet(
            packet,
            dict(reference_owner._pool._routes)[reference["option_label"]],
            dict(choices._pool._routes)[selected["option_label"]],
            reference_selection=reference,
            selection=selected,
            draw_route=draw_route,
        )
    return choices._protect(packet)
