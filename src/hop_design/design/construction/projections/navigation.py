"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/projections/navigation.py

Builds and verifies navigation facts around complete construction summaries.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from typing import Literal, cast

from hop_design.design.construction.complete.discovery import VerifiedConstructionSpaceResult
from hop_design.models.construction import RealizationGroup, RealizationGrouping
from hop_design.models.construction.complete.authority import CompositionDispositionStatus
from hop_design.models.construction.complete.realization import (
    MaterializedConstructionRealization,
)
from hop_design.models.construction.projections import (
    ConstructionNavigationAcceptedRoute,
    ConstructionNavigationGeometryGroup,
    ConstructionNavigationProjection,
)
from hop_design.models.construction.targets import BasalTarget, FoldbackTarget
from hop_design.serialization import canonical_json_bytes

from .complete import project_complete_construction_summary


def project_complete_construction_navigation(
    source: VerifiedConstructionSpaceResult,
) -> ConstructionNavigationProjection:
    """Project additive route-navigation facts without changing summary authority."""
    summary = project_complete_construction_summary(source)
    result = source.result
    realizations = {item.materialized_realization_id: item for item in result.realizations}
    accepted_routes = tuple(
        _project_accepted_route(realizations[cast(str, row.materialized_realization_id)])
        for row in summary.rows
        if row.status is CompositionDispositionStatus.ACCEPTED
    )
    return ConstructionNavigationProjection.create(
        source_result_id=result.result_id,
        summary=summary,
        accepted_routes=accepted_routes,
        geometry_groups=tuple(
            _project_geometry_group(group, realizations)
            for group in result.geometry_groups
            if group.grouping is RealizationGrouping.ACHIEVED_GEOMETRY
        ),
    )


def _project_accepted_route(
    realization: MaterializedConstructionRealization,
) -> ConstructionNavigationAcceptedRoute:
    basal_authority = realization.basal_authority
    return ConstructionNavigationAcceptedRoute(
        materialized_realization_id=realization.materialized_realization_id,
        foldback_geometry=cast(
            FoldbackTarget,
            realization.foldback_authority.local_realization.achieved_geometry,
        ),
        basal_geometry=(
            None
            if basal_authority is None
            else cast(BasalTarget, basal_authority.local_realization.achieved_geometry)
        ),
        foldback_retained_overhead_nt=(
            realization.foldback_authority.retained_overhead.retained_overhead_nt
        ),
        basal_retained_overhead_nt=(
            None
            if basal_authority is None
            else basal_authority.retained_overhead.retained_overhead_nt
        ),
        cleavage_enzyme_ids=_route_cleavage_enzyme_ids(realization),
        retained_non_payload_nt=(
            len(realization.design.encoding_sequence) - 2 * len(realization.design.payload_sequence)
        ),
        final_product_topology=cast(
            Literal["single_stranded_hairpin", "linear_duplex"],
            realization.final_product.reference.topology,
        ),
    )


def _route_cleavage_enzyme_ids(
    realization: MaterializedConstructionRealization,
) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                operation.enzyme_id
                for program in realization.construction_program.reaction_programs
                for stage in program.stages
                for operation in stage.operations
            }
        )
    )


def _project_geometry_group(
    group: RealizationGroup,
    realizations: dict[str, MaterializedConstructionRealization],
) -> ConstructionNavigationGeometryGroup:
    members = tuple(realizations[item] for item in group.realization_ids)
    foldback_geometry = cast(
        FoldbackTarget,
        members[0].foldback_authority.local_realization.achieved_geometry,
    )
    basal_geometry = (
        None
        if members[0].basal_authority is None
        else cast(
            BasalTarget,
            members[0].basal_authority.local_realization.achieved_geometry,
        )
    )
    return ConstructionNavigationGeometryGroup.create(
        foldback_geometry=foldback_geometry,
        basal_geometry=basal_geometry,
        realization_ids=group.realization_ids,
    )


def verify_complete_construction_navigation(
    projection: ConstructionNavigationProjection,
    source: VerifiedConstructionSpaceResult,
) -> ConstructionNavigationProjection:
    """Require canonical equality with navigation rebuilt from its verified source."""
    parsed = ConstructionNavigationProjection.model_validate(
        projection.model_dump(mode="python", by_alias=True)
    )
    expected = project_complete_construction_navigation(source)
    if canonical_json_bytes(parsed) != canonical_json_bytes(expected):
        raise ValueError("Construction navigation does not replay its verified source result.")
    return parsed


__all__ = [
    "project_complete_construction_navigation",
    "verify_complete_construction_navigation",
]
