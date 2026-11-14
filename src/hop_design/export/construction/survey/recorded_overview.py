"""Use saved preparation positions and field codes without a new fit or recoding."""

from collections import Counter
from math import sqrt
from typing import Any, cast
from xml.etree import ElementTree as ET

from hop_design.models.construction.variants.overview import PreparationOverview
from hop_design.serialization import canonical_json_bytes, sha256_digest

from ..presentation.comparison import COMPARISON_GROUPS
from ..presentation.palette import FOLDBACK, pale
from .layout import WIDTH
from .similarity import HEIGHT, render_map_geometry


def comparison_packet(overview: PreparationOverview, members: tuple[str, ...]) -> dict[str, Any]:
    if len(set(members)) != len(members) or set(members) != set(overview.members):
        raise ValueError("Overview display members disagree with the saved preparations.")
    index = {identity: i for i, identity in enumerate(overview.members)}
    return {
        "algorithm": overview.algorithm,
        "basis": overview.basis.model_dump(mode="json"),
        "presentation": {
            "groups": {
                **COMPARISON_GROUPS,
                "processing": {"label": "Enzymes", "fill": pale(FOLDBACK)},
            }
        },
        "columns": [
            {
                **column.model_dump(mode="json", exclude_none=True),
                "indices": [column.indices[index[identity]] for identity in members],
            }
            for column in overview.columns
        ],
        "contacts": [],
    }


def overview_geometry(overview: PreparationOverview) -> dict[str, Any]:
    radius = max(1.6, min(7, 80 / sqrt(len(overview.members))))
    counts = Counter(overview.coordinates)
    points: list[dict[str, Any]] = []
    for identity, (x, y) in zip(overview.members, overview.coordinates, strict=True):
        dx, dy = WIDTH / 2 + x * 185, HEIGHT / 2 - y * 185
        points.append(
            {
                "identity": identity,
                "comparison_key": identity,
                "x": dx,
                "y": dy,
                "center": [dx, dy],
                "molecular": [x, y],
                "offset": [0.0, 0.0],
                "coincident": counts[(x, y)],
                "loop": "",
            }
        )
    left, right = min(p["x"] for p in points) - radius, max(p["x"] for p in points) + radius
    top, bottom = min(p["y"] for p in points) - radius, max(p["y"] for p in points) + radius
    padding = max(12, max(right - left, bottom - top) * 0.08)
    return {
        "points": points,
        "radius": radius,
        "frame": [
            left - padding,
            top - padding,
            right - left + 2 * padding,
            bottom - top + 2 * padding,
        ],
    }


def overview_map_index(overview: PreparationOverview, members: tuple[str, ...]) -> dict[str, Any]:
    geometry = overview_geometry(overview)
    lookup = {identity: i for i, identity in enumerate(members)}
    comparison = comparison_packet(overview, members)
    return {
        "schema": "hop.inspection-map/v1",
        "digest": sha256_digest(
            canonical_json_bytes({"overview": overview.digest, "geometry": geometry})
        ),
        "frame": geometry["frame"],
        "radius": geometry["radius"],
        "points": [[lookup[p["identity"]], p["x"], p["y"]] for p in geometry["points"]],
        "comparison": comparison,
    }


def selected_overview_features(overview: PreparationOverview, identity: str) -> dict[str, Any]:
    from .comparison_features import select_projected_features

    return select_projected_features(
        comparison_packet(overview, overview.members), overview.members, identity
    )


def render_recorded_overview(overview: PreparationOverview, **kwargs: Any) -> bytes:
    geometry = overview_geometry(overview)
    root = ET.fromstring(
        render_map_geometry(geometry, set(overview.members), overview.digest, **kwargs)
    )
    root.set("viewBox", " ".join(str(value) for value in geometry["frame"]))
    display_scale = max(geometry["frame"][2] / WIDTH, geometry["frame"][3] / HEIGHT)
    for circle in root.iter("{http://www.w3.org/2000/svg}circle"):
        for attribute in ("r", "stroke-width"):
            circle.set(attribute, str(float(circle.attrib[attribute]) * display_scale))
    # The caller supplies its caption/legend; fixed-frame context labels do
    # not belong inside an externally fitted coordinate extent.
    for node in list(root):
        if node.get("data-map-context") or node.get("data-color-legend"):
            root.remove(node)
    return cast(bytes, ET.tostring(root, encoding="utf-8", xml_declaration=True))
