"""Bounded discovery of release-compatible terminal basal processing geometry."""

from __future__ import annotations

from typing import Literal

from hop_design.kernel.basal_processing import (
    evaluate_basal_processing_geometry,
    resolve_basal_release_geometry,
)
from hop_design.models.catalog import ProcessingCatalog, ReleaseAgent
from hop_design.models.discovery.basal_processing import (
    BasalProcessingGeometryHit,
    BasalProcessingGeometryRequest,
    BasalProcessingGeometrySearchLimits,
    BasalProcessingGeometrySearchResult,
    BasalProcessingGeometryTruncation,
    basal_processing_geometry_id,
)


def search_basal_processing_geometries(
    *,
    catalog: ProcessingCatalog,
    request: BasalProcessingGeometryRequest,
    limits: BasalProcessingGeometrySearchLimits,
) -> BasalProcessingGeometrySearchResult:
    """Find exact terminal nick geometries without application preference."""
    try:
        resolved_agent = catalog.by_id(request.release_agent_id)
    except KeyError as exc:
        raise ValueError(
            f"Processing catalog does not contain release agent {request.release_agent_id!r}."
        ) from exc
    if not isinstance(resolved_agent, ReleaseAgent):
        raise ValueError(f"Catalog entry {request.release_agent_id!r} is not a release agent.")
    release = resolve_basal_release_geometry(
        resolved_agent,
        orientation=request.release_orientation,
    )
    if request.require_release_site_excised and not release.recognition_site_excised:
        raise ValueError("Selected release agent does not excise its recognition site.")

    agents = tuple(sorted(catalog.nicking_agents, key=lambda agent: agent.agent_id))
    examined = agents[: limits.max_search_nodes]
    feasibility = tuple(
        evaluate_basal_processing_geometry(
            agent,
            release=release,
            request=request,
        )
        for agent in examined
    )
    compatible = tuple(row for row in feasibility if row.compatible)
    returned = compatible[: limits.max_hits]
    hits = tuple(
        BasalProcessingGeometryHit(
            **row.model_dump(mode="python"),
            candidate_id=basal_processing_geometry_id(row),
            canonical_ordinal=canonical_ordinal,
        )
        for canonical_ordinal, row in enumerate(returned, start=1)
    )
    truncated_by: list[BasalProcessingGeometryTruncation] = []
    if len(examined) < len(agents):
        truncated_by.append("max_search_nodes")
    if len(compatible) > limits.max_hits:
        truncated_by.append("max_hits")
    if truncated_by:
        status: Literal["complete", "infeasible", "truncated"] = "truncated"
    elif hits:
        status = "complete"
    else:
        status = "infeasible"
    return BasalProcessingGeometrySearchResult(
        status=status,
        catalog_id=catalog.catalog_id,
        request=request,
        limits=limits,
        release=release,
        hits=hits,
        feasibility=feasibility,
        candidate_space_size=len(agents),
        search_nodes_examined=len(examined),
        observed_hit_count=len(compatible),
        truncated_by=tuple(truncated_by),
    )


__all__ = ["search_basal_processing_geometries"]
