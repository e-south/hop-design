"""Route-level annotation decisions; molecular footprints remain authoritative."""

import json
from html import escape
from typing import Literal

from hop_design.models.construction.projections.atlas import MolecularScenes
from hop_design.models.construction.projections.inspection import MolecularStateInspection
from hop_design.models.construction.variants.inspection import MolecularAddress

from .style import TERMINAL_SIZE, site_color
from .typography import text_width

RouteSiteLabels = Literal["all", "operations", "narrative"]


def footprint_color(
    projection: MolecularStateInspection, role: str, addresses: tuple[MolecularAddress, ...]
) -> str:
    """Use the recorded neighborhood to distinguish the two exposure regions."""
    if role == "strand_exposure" and addresses:
        neighborhoods = {b.neighborhood for b in projection.bases if b.address in addresses}
        if neighborhoods and neighborhoods <= {"closing", "loop"}:
            return site_color("foldback_nick")
    return site_color(role)


def named_sites(
    state: MolecularStateInspection, policy: RouteSiteLabels, introduced: set[str]
) -> frozenset[str]:
    if policy not in {"all", "operations", "narrative"}:
        raise ValueError("Unknown site-label policy.")
    acting = {o.operation_id for o in state.operations}
    return frozenset(
        site.site_id
        for site in state.recognition_sites
        if policy == "all"
        or site.site_id in acting
        or (policy == "narrative" and site.enzyme_name not in introduced)
    )


def site_key(
    atlas: MolecularScenes,
    width: float,
    top: float,
    *,
    size: float = TERMINAL_SIZE,
    include_events: bool = True,
) -> tuple[str, float]:
    """A compact printed key also works without hover or repeated names."""
    entries = sorted(
        {
            (site.enzyme_name, footprint_color(state, site.role, site.recognition))
            for state in atlas.states
            for site in state.recognition_sites
            if site.recognition
        }
    )
    return draw_site_key(entries, width, top, size=size, include_events=include_events)


def draw_site_key(
    entries: list[tuple[str, str]],
    width: float,
    top: float,
    *,
    size: float = TERMINAL_SIZE,
    include_events: bool = True,
) -> tuple[str, float]:
    """Reflow the same name/color bindings for the full plate and printed pages."""
    data = escape(json.dumps(entries), quote=True)
    rows = [f'<g data-site-key="true" data-site-key-entries="{data}">']
    x, y = 28.0, top + size
    for name, color in entries:
        extent = text_width(name, size) + 96
        if x > 28 and x + extent > width - 28:
            x, y = 28, y + size * 1.4
        rows.append(
            f'<rect x="{x}" y="{y - size * 0.7}" width="40" height="{size * 0.6}" rx="3" '
            f'fill="{color}" fill-opacity=".2" stroke="{color}" stroke-width="2"/>'
        )
        rows.append(
            f'<text x="{x + 52}" y="{y}" font-size="{size}" fill="{color}">{escape(name)}</text>'
        )
        x += extent
    captions: tuple[str, ...] = (
        "Dashed site: partial / unresolved · Hollow / filled cut: planned / applied.",
        "Unmarked termini: OH · P: phosphate.",
        "Diamond: noncanonical · Bridge: joined · End words: 5\u2032→3\u2032; gap in bp.",
    )
    if not include_events:
        captions = (
            "Dashed site: partial / unresolved · Diamond: noncanonical · "
            "P: phosphate; unmarked termini: OH.",
        )
    for caption in captions:
        line = ""
        for word in caption.split():
            candidate = (line + " " + word).strip()
            if line and text_width(candidate, size) > width - 56:
                y += size * 1.4
                rows.append(f'<text x="28" y="{y}" font-size="{size}">{escape(line)}</text>')
                line = word
            else:
                line = candidate
        y += size * 1.4
        rows.append(f'<text x="28" y="{y}" font-size="{size}">{escape(line)}</text>')
    rows.append("</g>")
    return "".join(rows), y + 12
