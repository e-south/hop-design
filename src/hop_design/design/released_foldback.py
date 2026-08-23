"""Bounded discovery of released-foldback physical geometry."""

from __future__ import annotations

from itertools import islice
from typing import Literal

from hop_design.models.catalog import ProcessingCatalog
from hop_design.models.discovery.released_foldback import (
    ReleasedFoldbackGeometryHit,
    ReleasedFoldbackGeometryRequest,
    ReleasedFoldbackGeometrySearchLimits,
    ReleasedFoldbackGeometrySearchResult,
    ReleasedFoldbackGeometryTruncation,
    released_foldback_geometry_id,
    released_foldback_hit_order_key,
)
from hop_design.models.discovery.released_foldback_candidate_evaluation import (
    enumerate_released_foldback_precursors,
    released_foldback_precursor_candidate_count,
    released_foldback_precursor_domains,
)
from hop_design.models.discovery.released_foldback_candidates import (
    ReleasedFoldbackPrecursorBlocker,
    ReleasedFoldbackPrecursorCandidate,
    ReleasedFoldbackPrecursorSearchLimits,
    ReleasedFoldbackPrecursorSearchRequest,
    ReleasedFoldbackPrecursorSearchResult,
    ReleasedFoldbackPrecursorSearchTruncation,
    released_foldback_precursor_candidate_id,
)
from hop_design.models.discovery.released_foldback_evaluation import (
    evaluate_released_foldback_geometry,
    iter_released_foldback_geometry_nodes,
    released_foldback_candidate_space_size,
)
from hop_design.serialization import sha256_digest


def search_released_foldback_geometries(
    *,
    catalog: ProcessingCatalog,
    request: ReleasedFoldbackGeometryRequest,
    limits: ReleasedFoldbackGeometrySearchLimits,
) -> ReleasedFoldbackGeometrySearchResult:
    """Find compatible nick/release/foldback domains without choosing sequences."""
    candidate_space_size = released_foldback_candidate_space_size(
        catalog=catalog,
        request=request,
    )
    nodes = islice(
        iter_released_foldback_geometry_nodes(catalog=catalog, request=request),
        limits.max_search_nodes,
    )
    feasibility = tuple(
        evaluate_released_foldback_geometry(
            nicking_agent=nick,
            release_agent=release,
            release_orientation=orientation,
            evaluated_nick_boundary=boundary,
            request=request,
        )
        for boundary, nick, release, orientation in nodes
    )
    compatible = tuple(row for row in feasibility if row.compatible)
    returned = tuple(sorted(compatible, key=released_foldback_hit_order_key))[: limits.max_hits]
    hits = tuple(
        ReleasedFoldbackGeometryHit(
            **row.model_dump(mode="python"),
            candidate_id=released_foldback_geometry_id(row),
            canonical_ordinal=canonical_ordinal,
        )
        for canonical_ordinal, row in enumerate(returned, start=1)
    )
    truncated_by: list[ReleasedFoldbackGeometryTruncation] = []
    if len(feasibility) < candidate_space_size:
        truncated_by.append("max_search_nodes")
    if len(compatible) > limits.max_hits:
        truncated_by.append("max_hits")
    if truncated_by:
        status: Literal["complete", "infeasible", "truncated"] = "truncated"
    elif hits:
        status = "complete"
    else:
        status = "infeasible"
    return ReleasedFoldbackGeometrySearchResult(
        status=status,
        catalog=catalog,
        request=request,
        limits=limits,
        hits=hits,
        feasibility=feasibility,
        candidate_space_size=candidate_space_size,
        search_nodes_examined=len(feasibility),
        observed_hit_count=len(compatible),
        truncated_by=tuple(truncated_by),
    )


def search_released_foldback_precursors(
    request: ReleasedFoldbackPrecursorSearchRequest,
    *,
    limits: ReleasedFoldbackPrecursorSearchLimits,
) -> ReleasedFoldbackPrecursorSearchResult:
    """Materialize exact precursors only inside caller-authorized domains."""
    domains = released_foldback_precursor_domains(request)
    if domains is None:
        return ReleasedFoldbackPrecursorSearchResult(
            status="infeasible",
            request=request,
            limits=limits,
            hits=(),
            candidate_space_size=0,
            search_nodes_examined=0,
            observed_hit_count=0,
            blockers=(ReleasedFoldbackPrecursorBlocker.CALLER_DOMAIN_CONFLICT,),
            truncated_by=(),
        )

    candidate_space_size = released_foldback_precursor_candidate_count(
        request,
        domains=domains,
    )
    sequences = tuple(
        islice(
            enumerate_released_foldback_precursors(request, domains=domains),
            limits.max_search_nodes,
        )
    )
    returned = sequences[: limits.max_hits]
    hits = tuple(
        ReleasedFoldbackPrecursorCandidate(
            candidate_id=released_foldback_precursor_candidate_id(
                geometry_id=request.geometry.candidate_id,
                sequence=sequence,
            ),
            canonical_ordinal=canonical_ordinal,
            geometry_id=request.geometry.candidate_id,
            precursor_sequence=sequence,
            precursor_digest=sha256_digest(sequence.encode("utf-8")),
        )
        for canonical_ordinal, sequence in enumerate(returned, start=1)
    )
    truncated_by: list[ReleasedFoldbackPrecursorSearchTruncation] = []
    if len(sequences) < candidate_space_size:
        truncated_by.append("max_search_nodes")
    if len(returned) < len(sequences):
        truncated_by.append("max_hits")
    status: Literal["complete", "truncated"] = "truncated" if truncated_by else "complete"
    return ReleasedFoldbackPrecursorSearchResult(
        status=status,
        request=request,
        limits=limits,
        hits=hits,
        candidate_space_size=candidate_space_size,
        search_nodes_examined=len(sequences),
        observed_hit_count=len(sequences),
        blockers=(),
        truncated_by=tuple(truncated_by),
    )


__all__ = [
    "search_released_foldback_geometries",
    "search_released_foldback_precursors",
]
