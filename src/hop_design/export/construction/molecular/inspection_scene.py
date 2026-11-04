"""Shared, addressable scene primitives for static inspection and verified motion."""

import json
from collections import defaultdict
from html import escape
from math import hypot

from hop_design.models.construction.projections.inspection import MolecularStateInspection

from .primitives.ribbon import ribbon_path
from .primitives.style import BACKBONE, CONTACT, REGION_COLORS, REGION_OPACITY

Points = dict[tuple[str, int], tuple[float, float]]


def address_key(strand: str, index: int) -> str:
    return json.dumps([strand, index], separators=(",", ":"))


def region_spans(projection: MolecularStateInspection, points: Points) -> str:
    groups = defaultdict(list)
    for base in projection.bases:
        groups[base.address.strand_id, base.neighborhood or "unmapped"].append(base.address.index)
    rows = []
    for (strand, region), indices in groups.items():
        runs: list[list[int]] = []
        for index in sorted(indices):
            x, y = points[strand, index]
            if (
                not runs
                or index != runs[-1][-1] + 1
                or hypot(x - points[strand, runs[-1][-1]][0], y - points[strand, runs[-1][-1]][1])
                > 34
            ):
                runs.append([])
            runs[-1].append(index)
        for run in runs:
            context = list(run)
            for direction in (-1, 1):
                for _ in range(2):
                    endpoint = context[0] if direction < 0 else context[-1]
                    neighbor = endpoint + direction
                    if (strand, neighbor) not in points:
                        break
                    x, y = points[strand, endpoint]
                    u, v = points[strand, neighbor]
                    if hypot(u - x, v - y) > 34:
                        break
                    if direction < 0:
                        context.insert(0, neighbor)
                    else:
                        context.append(neighbor)
            start, end = context.index(run[0]), context.index(run[-1])
            curve = ribbon_path(
                [points[strand, index] for index in context], 13, start, end, terminal_extension=6
            )
            members = escape(json.dumps([[strand, index] for index in run]), quote=True)
            path_members = escape(json.dumps([[strand, index] for index in context]), quote=True)
            rows.append(
                f'<path data-region-fill="{region}" data-members="{members}" '
                f'data-path-members="{path_members}" '
                f'data-path-start="{start}" data-path-end="{end}" '
                f'data-region-width="13" data-ribbon-contour="true" data-terminal-extension="6" '
                f'd="{curve}" fill="{REGION_COLORS.get(region, "#AAB2B8")}" '
                f'fill-opacity="{REGION_OPACITY}" stroke="{BACKBONE}" '
                'stroke-opacity=".6" stroke-width="1"/>'
            )
    return "".join(rows)


def edge(
    kind: str, left: tuple[str, int], right: tuple[str, int], points: Points, *, pair_kind: str = ""
) -> str:
    x, y = points[left]
    u, v = points[right]
    length = max(1, hypot(u - x, v - y))
    pad = min(10 if kind == "pair" else 7, length / 2)
    dx, dy = (u - x) * pad / length, (v - y) * pad / length
    attrs = f' data-pair-kind="{pair_kind}"' if pair_kind else ""
    path = f"M{x + dx},{y + dy} L{u - dx},{v - dy}"
    noncanonical = kind == "pair" and pair_kind not in {"", "watson_crick"}
    if noncanonical:
        mx, my = (x + u) / 2, (y + v) / 2
        ux, uy = (u - x) / length, (v - y) / length
        a, b = mx - ux * 6, my - uy * 6
        c, d = mx + ux * 6, my + uy * 6
        path = (
            f"M{x + dx},{y + dy} L{a},{b} "
            f"M{a},{b} L{mx - uy * 5},{my + ux * 5} L{c},{d} "
            f"L{mx + uy * 5},{my - ux * 5} Z M{c},{d} L{u - dx},{v - dy}"
        )
        attrs += ' data-contact-glyph="diamond"'
    return (
        f'<path data-edge-kind="{kind}" data-from="{escape(address_key(*left), quote=True)}" '
        f'data-to="{escape(address_key(*right), quote=True)}" '
        f'd="{path}" fill="none" '
        f'stroke="{CONTACT if kind == "pair" else BACKBONE}" '
        f'stroke-opacity="{1 if kind == "pair" else 0}" '
        f'stroke-width="{2.4 if noncanonical else 1.3 if kind == "pair" else 2}"{attrs}/>'
    )
