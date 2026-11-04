"""Adapt exact molecular admission to a bounded, resumable navigation operation."""

import json
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any

from hop_design.models.construction.product_request import ProductRequest
from hop_design.models.construction.surveys.execution import SurveyEvaluationLimits
from hop_design.models.construction.surveys.navigation import SurveySeekCursor

from ..branches import SurveyBranches
from ..coordinates import coordinate_at, coordinate_rank
from .pages import Geometry, PageNavigator, Plane

if TYPE_CHECKING:
    from ..partitions import PartitionPlans


def cursor_after(
    plans: "PartitionPlans",
    branches: SurveyBranches,
    limits: SurveyEvaluationLimits,
    target: int,
    *,
    branch: int,
    page: int,
) -> SurveySeekCursor:
    context, geometry_rank = divmod(branch, branches.geometry_count)
    geometry = coordinate_at(branches.geometry_sizes, geometry_rank)
    product = branches.product(target, branch=geometry_rank, limits=limits)
    policy = branches.request.materialization.source_preparation.source_ssdna
    position = plans.context_priority(product, page, policy).position(context)
    return SurveySeekCursor.model_validate(
        {
            "wave": position
            + branches.search_order(limits).cost(geometry)
            + plans.get(product).depth(page),
            "context": position,
            "geometry": geometry,
            "page_after": page,
            "wave_has_page": True,
        }
    )


def advance(
    plans: "PartitionPlans",
    branches: SurveyBranches,
    limits: SurveyEvaluationLimits,
    target: int,
    cursor: SurveySeekCursor,
    *,
    planes: frozenset[Plane],
    exhaustion_proven: bool,
) -> tuple[dict[str, Any] | None, int]:
    def product(geometry: Geometry) -> ProductRequest:
        return branches.product(
            target, branch=coordinate_rank(branches.geometry_sizes, geometry), limits=limits
        )

    def pages(geometry: Geometry, depth: int, after: int) -> Iterator[int]:
        return plans.get(product(geometry)).pages_at_depth(depth, after=after)

    def context_rank(geometry: Geometry, page: int, context: int) -> int:
        policy = branches.request.materialization.source_preparation.source_ssdna
        return plans.context_priority(product(geometry), page, policy).rank_at(context)

    result = PageNavigator(
        branches.search_order(limits), branches.context_count, pages, context_rank
    ).scan(cursor, empty_planes=planes, maximum_nodes=limits.navigation_nodes)
    if result.address is not None:
        branch, page = result.address
        return {
            "branch": branch,
            "page": page,
            "pair": 0,
            "exhaustion_proven": exhaustion_proven,
        }, result.examined_nodes
    if result.cursor is None:
        return None, result.examined_nodes
    return {
        "seek": result.cursor.model_dump(mode="json", by_alias=True),
        "exhaustion_proven": exhaustion_proven,
    }, result.examined_nodes


def navigation_record(
    plans: "PartitionPlans",
    branches: SurveyBranches,
    limits: SurveyEvaluationLimits,
    target: int,
    address: dict[str, Any],
    *,
    planes: frozenset[Plane],
) -> dict[str, Any]:
    cursor = SurveySeekCursor.model_validate_json(json.dumps(address["seek"]))
    following, nodes = advance(
        plans,
        branches,
        limits,
        target,
        cursor,
        planes=planes,
        exhaustion_proven=address["exhaustion_proven"],
    )
    return {
        "schema": "hop.interface-survey-navigation/v1",
        "target": target,
        "seek": address["seek"],
        "next": following,
        "navigation_nodes": nodes,
        "navigation_nodes_complete": True,
        "continuations_examined": 0,
        "exhaustion_proven": address["exhaustion_proven"],
        "witnesses": [],
        "bundle": None,
        "projections": [],
        "product_request": None,
        "empty_basal_planes": [],
        "limits": limits.model_dump(mode="json"),
    }
