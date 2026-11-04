"""Inspect captured drawings or render a compact authority on selection."""

import json
from typing import TYPE_CHECKING

from ..intents.base import Source
from ..packets.atlas import MolecularAtlasPacket
from ..packets.inspection import MolecularInspectionPacket

if TYPE_CHECKING:
    from .reader import AtlasEdition


def inspect_edition_atlas(
    edition: "AtlasEdition",
    selection: Source,
    *,
    reference_selection: Source | None = None,
    render_policy: str | None = None,
    presentation: str | None = None,
    stage: str | None = None,
    draw_route: bool = True,
) -> MolecularAtlasPacket:
    from ..navigation.render_policy import render_context
    from .reader import CapturedAtlas

    context = render_context(
        edition, selection, reference_selection, render_policy, presentation, stage
    )
    selection, reference_selection, policy = (
        context.selection,
        context.reference,
        context.policy,
    )
    selected = edition._selected(selection)
    if edition._store.compact:
        from .compact_projection import compact_atlas

        packet: MolecularAtlasPacket = compact_atlas(
            edition, selected, reference_selection=reference_selection, draw_route=draw_route
        )
        return context.finish(
            packet,
            "current",
            notice="Compact edition retains molecular authority; artwork is drawn on demand.",
            draw_route=draw_route,
        )
    prefix = edition._prefix(selected.materialized_realization_id) + "/atlas/"
    files = (
        dict(edition._store.files(prefix))
        if draw_route
        else {
            name: edition._store.read(prefix + name)
            for name in ("summary.json", "overview.svg", "report.md")
        }
    )
    summary = json.loads(files["summary.json"])
    if summary["atlas"]["materialized_realization_id"] != selected.materialized_realization_id:
        raise ValueError("Captured molecular atlas disagrees with selection.")
    packet = object.__new__(CapturedAtlas if draw_route else MolecularInspectionPacket)
    object.__setattr__(packet, "_files", tuple(sorted(files.items())))
    object.__setattr__(packet, "_summary", files["summary.json"])
    object.__setattr__(packet, "_report", files["report.md"].decode())
    object.__setattr__(packet, "_roots", (edition._store.root,))
    notice = None
    if reference_selection is not None:
        from .comparison import compare_captured

        packet = compare_captured(edition, packet, selection, reference_selection)
        notice = "Captured artwork is unchanged; exact differences are in the comparison record."
    if policy == "current":
        from .redraw import redraw_captured

        packet = redraw_captured(packet, draw_route=draw_route)
        rendering = json.loads(packet.json_bytes)["rendering"]
        return context.finish(
            packet, rendering["effective"], notice=rendering["notice"], draw_route=draw_route
        )
    return context.finish(packet, "captured", notice=notice, draw_route=draw_route)


def inspection_state_ids(edition: "AtlasEdition", selection: Source) -> tuple[str, ...]:
    """Verify captured bytes without constructing or measuring a drawing packet."""
    selected = edition._selected(selection)
    if edition._store.compact:
        from ..projections.inspection import inspection_states
        from .authority import admitted_route

        route = admitted_route(edition, selected.materialized_realization_id)
        return tuple(state.state_id for state in inspection_states(route))
    prefix = edition._prefix(selected.materialized_realization_id) + "/atlas/"
    atlas = json.loads(edition._store.read(prefix + "summary.json"))["atlas"]
    for name in edition._store.files(prefix):
        if name != "summary.json":
            edition._store.read(prefix + name)
    if atlas["materialized_realization_id"] != selected.materialized_realization_id:
        raise ValueError("Captured molecular atlas disagrees with selection.")
    return tuple(state["state"]["state_id"] for state in atlas["states"])
