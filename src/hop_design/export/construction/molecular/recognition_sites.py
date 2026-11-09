"""Fitted site spans from mapped addresses, with no sequence or reaction inference."""

import json
from collections import defaultdict
from html import escape
from typing import Literal

from hop_design.models.construction.projections.inspection import MolecularStateInspection

from .label_layout import LabelPlacer
from .primitives.annotation_policy import footprint_color
from .primitives.ribbon import ribbon_path, ribbon_points
from .primitives.style import ANNOTATION_SIZE, SITE_HALF_WIDTH, object_id
from .primitives.typography import text_width


def recognition_site_overlays(
    projection: MolecularStateInspection,
    points: dict[tuple[str, int], tuple[float, float]],
    labels: LabelPlacer | None = None,
    *,
    site_labels: Literal["all", "operations"] = "all",
    label_site_ids: frozenset[str] | None = None,
    label_size: int = ANNOTATION_SIZE,
    strand_labels: bool = False,
) -> str:
    if site_labels not in ("all", "operations"):
        raise ValueError("Unknown site-label policy.")
    operations = {o.operation_id: o for o in projection.operations}
    rows = []
    named: dict[tuple[str, str, str], list[tuple[str, float, float]]] = defaultdict(list)
    labels = labels or LabelPlacer()
    for site in projection.recognition_sites:
        operation = operations.get(site.site_id)
        color = footprint_color(projection, site.role, site.recognition)
        direction = "unresolved"
        path = [points[a.strand_id, a.index] for a in site.orientation_path]
        if (
            len(path) >= 2
            and len({a.strand_id for a in site.orientation_path}) == 1
            and max(p[1] for p in path) - min(p[1] for p in path) < 1
        ):
            points_right = (path[-1][0] > path[0][0]) == (site.orientation == "forward")
            direction = "right" if points_right else "left"
        rows.append(
            f'<g id="{object_id("site", projection.state.state_id, site.site_id)}" '
            f'data-site-id="{escape(site.site_id)}" data-presence="{site.presence}" '
            f'data-eligibility="{site.substrate_eligibility}" data-display-direction="{direction}" '
            f'data-site-role="{site.role}" data-orientation="{site.orientation}" '
            f'data-operation-timing="{operation.timing if operation else ""}">'
        )
        role = {
            "complete-end-generation-left": "left release",
            "complete-end-generation-right": "right release",
        }.get(site.site_id, site.role.replace("_", " "))
        rows.append(
            f"<title>{escape(site.enzyme_name)}; {role}; {site.orientation}; "
            f"{site.presence}; substrate eligibility: {site.substrate_eligibility}</title>"
        )
        runs: list[list[tuple[float, float]]] = []
        run_addresses: list[list[tuple[str, int]]] = []
        previous = None
        for address in site.recognition:
            position = points[address.strand_id, address.index]
            if (
                previous is None
                or address.strand_id != previous.strand_id
                or address.index != previous.index + 1
                or abs(position[0] - runs[-1][-1][0]) > 32
                or abs(position[1] - runs[-1][-1][1]) > 24
            ):
                runs.append([])
                run_addresses.append([])
            runs[-1].append(position)
            run_addresses[-1].append((address.strand_id, address.index))
            previous = address
        boxes = []
        for members in run_addresses:
            context = list(members)
            for step in (-1, 1):
                for _ in range(2):
                    strand, index = context[0] if step < 0 else context[-1]
                    neighbor = (strand, index + step)
                    if neighbor not in points:
                        break
                    current_point, neighbor_point = points[strand, index], points[neighbor]
                    if (
                        abs(current_point[0] - neighbor_point[0]) > 32
                        or abs(current_point[1] - neighbor_point[1]) > 24
                    ):
                        break
                    if step < 0:
                        context.insert(0, neighbor)
                    else:
                        context.append(neighbor)
            start, end = context.index(members[0]), context.index(members[-1])
            outline = ribbon_points([points[k] for k in context], SITE_HALF_WIDTH, start, end)
            x, z = min(p[0] for p in outline), max(p[0] for p in outline)
            y, w = min(p[1] for p in outline), max(p[1] for p in outline)
            boxes.append((x, z, y, w))
            contour = ribbon_path([points[k] for k in context], SITE_HALF_WIDTH, start, end)
            dash = ' stroke-dasharray="5 3"' if site.presence in {"partial", "unresolved"} else ""
            rows.append(
                f'<path data-members="{escape(json.dumps(members), quote=True)}" '
                f'data-path-members="{escape(json.dumps(context), quote=True)}" '
                f'data-path-start="{start}" data-path-end="{end}" '
                f'data-recognition-footprint="{SITE_HALF_WIDTH}" d="{contour}" '
                f'fill="{color}" fill-opacity=".2" stroke="{color}" '
                f'stroke-opacity="{1 if operation else 0.85}" '
                f'stroke-linejoin="round" stroke-width="{2.8 if operation else 1.8}"{dash}/>'
            )
        if (
            boxes
            and (site_labels == "all" or operation is not None)
            and (label_site_ids is None or site.site_id in label_site_ids)
        ):
            x, right, top, bottom = min(boxes, key=lambda box: (box[2], box[0]))
            # Role, lineage and eligibility remain in the titled site group.
            label = site.enzyme_name
            if site.presence in {"partial", "unresolved"}:
                label += " *"
            if strand_labels:
                middle = (
                    min(y for _, y in points.values()) + max(y for _, y in points.values())
                ) / 2
                below = (top + bottom) / 2 > middle
                y = bottom + label_size + 10 if below else top - 10
                named[label, color, site.site_id].append((site.site_id, (x + right) / 2, y))
            else:
                named[label, color, site.site_id].append((site.site_id, (x + right) / 2, top - 9))
        rows.append("</g>")
    for (label, color, _), anchors in named.items():
        center = sum(x for _, x, _ in anchors) / len(anchors)
        x = center - text_width(label, label_size) / 2
        y = min(y for _, _, y in anchors)
        ids = escape(json.dumps([site for site, _, _ in anchors]), quote=True)
        rows.append(
            f'<g data-site-labels="{ids}" '
            f'data-label-for-site="{escape(anchors[0][0], quote=True)}">'
        )
        if len(anchors) == 1:
            rows.append(labels.text("recognition", x, y, label, color, label_size))
        else:
            a, b, width, height = labels.place(x, y, label, size=label_size)
            box = escape(json.dumps([a, b, width, height]), quote=True)
            for _, px, py in anchors:
                rows.append(
                    f'<path d="M{a + width / 2},{b + height} L{px},{py}" '
                    f'fill="none" stroke="{color}" stroke-opacity=".25"/>'
                )
            rows.append(
                f'<text data-label-kind="recognition" data-label-box="{box}" '
                f'x="{a}" y="{b + label_size}" font-size="{label_size}" '
                f'fill="{color}">{escape(label)}</text>'
            )
        rows.append("</g>")
    return "".join(rows)
