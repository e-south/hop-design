"""Adapt a fixed-reference variant query to the shared verified-route comparator."""

from typing import Any

from hop_design.models.construction.projections.atlas import AtlasComparison

from ..projections.atlas_comparison import compare_route_atlases
from .public import ScaffoldExploration


def compare_atlas(
    pool: ScaffoldExploration,
    summary: dict[str, Any],
    option: str,
) -> AtlasComparison | None:
    reference = summary["query"]["reference"]
    if reference is None:
        return None
    routes = dict(pool._routes)
    return compare_route_atlases(
        routes[reference], routes[option], reference=reference, option=option
    )
