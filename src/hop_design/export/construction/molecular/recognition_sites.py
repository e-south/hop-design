"""Fitted site spans from mapped addresses, with no sequence or reaction inference."""

import json
from collections import defaultdict
from html import escape
from typing import Literal

from hop_design.models.construction.projections.inspection import MolecularStateInspection

from .complementary_row import complementary_row_offset
from .label_layout import LabelPlacer
from .primitives.annotation_policy import FootprintScope, footprint_color, visible_footprint
from .primitives.ribbon import footprint_envelope, rounded_path
from .primitives.style import ANNOTATION_SIZE, object_id
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
    site_leaders: bool = True,
    footprint_scope: FootprintScope = "structural",
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
        painted = visible_footprint(projection, site.role, scope=footprint_scope)
        reference_count = getattr(site, "reference_base_count", 2 * len(site.recognition))
        mapped_count = getattr(site, "mapped_reference_bases", len(site.recognition))
        addresses = escape(
            json.dumps([(a.strand_id, a.index) for a in site.recognition]), quote=True
        )
        display = "absent" if not site.recognition else "painted" if painted else "metadata"
        rows.append(
            f'<g data-footprint-display="{display}" '
            f'data-recognition-addresses="{addresses}" '
            f'id="{object_id("site", projection.state.state_id, site.site_id)}" '
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
            f"{site.presence}; {mapped_count} of {reference_count} precursor bases "
            f"mapped to this state</title>"
        )
        members = [(a.strand_id, a.index) for a in site.recognition]
        boxes = []
        remaining = set(members)
        clusters = []
        while remaining:
            cluster = [min(remaining)]
            remaining.remove(cluster[0])
            for key in cluster:
                neighbors = [
                    k
                    for k in sorted(remaining)
                    if abs(points[k][0] - points[key][0]) <= 24
                    and abs(points[k][1] - points[key][1]) <= 60
                ]
                cluster.extend(neighbors)
                remaining.difference_update(neighbors)
            clusters.append(cluster)
        for cluster in clusters if painted else []:
            positions = [points[key] for key in cluster]
            paired = [
                points[other]
                for pair in projection.state.pairings
                for key, other in [
                    (
                        (pair.left_strand_id, pair.left_index),
                        (pair.right_strand_id, pair.right_index),
                    ),
                    (
                        (pair.right_strand_id, pair.right_index),
                        (pair.left_strand_id, pair.left_index),
                    ),
                ]
                if key in cluster and other in points
            ]
            if paired:
                positions += paired
            else:
                offset = complementary_row_offset(projection, cluster, points)
                if offset is not None:
                    positions += [(x, y + offset) for x, y in positions]
            outline = footprint_envelope(positions)
            x, z = min(p[0] for p in outline), max(p[0] for p in outline)
            y, w = min(p[1] for p in outline), max(p[1] for p in outline)
            boxes.append((x, z, y, w))
            labels.occupied.append((x, y, z - x, w - y))
            contour = rounded_path(outline, radius=6)
            dash = ' stroke-dasharray="5 3"' if site.presence in {"partial", "unresolved"} else ""
            rows.append(
                f'<path data-members="{escape(json.dumps(cluster), quote=True)}" '
                f'data-path-members="{escape(json.dumps(cluster), quote=True)}" '
                f'data-path-start="0" data-path-end="{len(cluster) - 1}" '
                f'data-envelope-box="{escape(json.dumps([x, y, z - x, w - y]), quote=True)}" '
                f'data-recognition-footprint="18" d="{contour}" '
                f'fill="{color}" fill-opacity=".2" stroke="{color}" '
                f'stroke-opacity="{1 if operation else 0.85}" stroke-linejoin="round" '
                f'stroke-width="{2.8 if operation else 1.8}"{dash}/>'
            )
        if (
            boxes
            and (site_labels == "all" or operation is not None)
            and (label_site_ids is None or site.site_id in label_site_ids)
        ):
            x, right = min(box[0] for box in boxes), max(box[1] for box in boxes)
            top, bottom = min(box[2] for box in boxes), max(box[3] for box in boxes)
            # Role, lineage and eligibility remain in the titled site group.
            label = site.enzyme_name
            if site.presence in {"partial", "unresolved"}:
                label += "*"
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
            a, b, width, height = labels.place(x, y, label, size=label_size)
            site = next(s for s in projection.recognition_sites if s.site_id == anchors[0][0])
            positions = [points[address.strand_id, address.index] for address in site.recognition]
            px = (min(p[0] for p in positions) + max(p[0] for p in positions)) / 2
            py = (min(p[1] for p in positions) + max(p[1] for p in positions)) / 2
            tx = min(max(px, a + 4), a + width - 4)
            ty = b + height if py > b + height / 2 else b
            bend = py + (ty - py) * 0.65
            molecule_center = (
                min(p[0] for p in points.values()) + max(p[0] for p in points.values())
            ) / 2
            bow = min(22, max(10, abs(ty - py) / 4)) * (-1 if px < molecule_center else 1)
            if site_leaders:
                rows.append(
                    f'<path data-site-leader="true" d="M{px},{py} Q{px + bow},{bend} {tx},{ty}" '
                    f'fill="none" stroke="{color}" stroke-opacity=".9" '
                    'stroke-width="3" stroke-linecap="round"/>'
                )
            box = escape(json.dumps([a, b, width, height]), quote=True)
            rows.append(
                f'<text data-label-kind="recognition" data-label-box="{box}" '
                f'x="{a}" y="{b + label_size}" font-size="{label_size}" '
                f'fill="{color}">{escape(label)}</text>'
            )
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
