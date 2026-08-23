"""Strict contracts for bounded foldback-to-basal route composition."""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from itertools import islice, product
from typing import Literal

from pydantic import Field, model_validator

from hop_design.models.base import HopModel
from hop_design.models.discovery.basal_routes import (
    BasalProcessingRouteCandidate,
    BasalProcessingRouteSearchResult,
)
from hop_design.models.discovery.released_foldback import ReleasedFoldbackGeometryHit
from hop_design.models.discovery.released_foldback_candidate_evaluation import (
    released_foldback_precursor_domains,
)
from hop_design.models.discovery.released_foldback_candidates import (
    ReleasedFoldbackPrecursorCandidate,
    ReleasedFoldbackPrecursorSearchRequest,
    ReleasedFoldbackPrecursorSearchResult,
)
from hop_design.models.junction import Strand
from hop_design.models.references import ReferenceId
from hop_design.models.strand_state import ReleasedStrandState

HairpinJunctionRouteStatus = Literal["complete", "infeasible", "truncated"]
HairpinJunctionRouteTruncation = Literal[
    "released_precursors",
    "basal_routes",
    "max_search_nodes",
    "max_hits",
]


class HairpinJunctionRouteBlocker(StrEnum):
    """Physical reasons why foldback and basal processing cannot share one strand."""

    CONTINUOUS_STRAND_MISMATCH = "continuous_strand_mismatch"


class HairpinJunctionRouteFeasibility(HopModel):
    """One evaluated released-foldback precursor by basal-route join."""

    released_foldback_precursor_id: ReferenceId
    basal_route_id: ReferenceId
    released_active_strand: Strand
    basal_surviving_strand: Strand
    blockers: tuple[HairpinJunctionRouteBlocker, ...]
    compatible: bool

    @model_validator(mode="after")
    def validate_outcome(self) -> HairpinJunctionRouteFeasibility:
        expected_blockers = (
            ()
            if self.released_active_strand is self.basal_surviving_strand
            else (HairpinJunctionRouteBlocker.CONTINUOUS_STRAND_MISMATCH,)
        )
        if self.blockers != expected_blockers:
            raise ValueError("Route blockers must derive from strand continuity.")
        if self.compatible != (not self.blockers):
            raise ValueError("compatible must be true exactly when blockers are empty.")
        return self


def _released_active_strand(geometry: ReleasedFoldbackGeometryHit) -> Strand:
    return Strand.BOTTOM if geometry.nick.strand is Strand.TOP else Strand.TOP


def hairpin_junction_route_feasibility(
    *,
    geometry: ReleasedFoldbackGeometryHit,
    released_foldback_precursor: ReleasedFoldbackPrecursorCandidate,
    basal_route: BasalProcessingRouteCandidate,
) -> HairpinJunctionRouteFeasibility:
    """Derive one foldback-to-basal strand-continuity outcome."""
    active_strand = _released_active_strand(geometry)
    blockers = (
        ()
        if active_strand is basal_route.surviving_strand
        else (HairpinJunctionRouteBlocker.CONTINUOUS_STRAND_MISMATCH,)
    )
    return HairpinJunctionRouteFeasibility(
        released_foldback_precursor_id=released_foldback_precursor.candidate_id,
        basal_route_id=basal_route.route_id,
        released_active_strand=active_strand,
        basal_surviving_strand=basal_route.surviving_strand,
        blockers=blockers,
        compatible=not blockers,
    )


def hairpin_junction_route_id(
    *,
    geometry: ReleasedFoldbackGeometryHit,
    released_foldback_precursor: ReleasedFoldbackPrecursorCandidate,
    basal_route: BasalProcessingRouteCandidate,
) -> str:
    """Return content identity for one foldback-to-basal route."""
    payload = {
        "released_foldback_geometry": geometry.model_dump(mode="json"),
        "released_foldback_precursor": released_foldback_precursor.model_dump(mode="json"),
        "basal_route": basal_route.model_dump(mode="json"),
    }
    content = (
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"
    ).encode("utf-8")
    return f"hop:hairpin-junction-route/{hashlib.sha256(content).hexdigest()}@1"


class HairpinJunctionRouteCandidate(HopModel):
    """One released foldback and basal route joined by continuous strand identity."""

    route_id: str = Field(pattern=r"^hop:hairpin-junction-route/[0-9a-f]{64}@1$")
    rank: int = Field(ge=1)
    released_foldback_geometry: ReleasedFoldbackGeometryHit
    released_foldback_precursor: ReleasedFoldbackPrecursorCandidate
    released_state: ReleasedStrandState
    basal_route: BasalProcessingRouteCandidate
    feasibility: HairpinJunctionRouteFeasibility

    @model_validator(mode="after")
    def validate_route(self) -> HairpinJunctionRouteCandidate:
        geometry = self.released_foldback_geometry
        precursor = self.released_foldback_precursor
        state = self.released_state
        basal_route = self.basal_route
        if precursor.geometry_id != geometry.candidate_id:
            raise ValueError("The exact precursor must reference the embedded foldback geometry.")
        precursor_request = ReleasedFoldbackPrecursorSearchRequest(
            geometry=geometry,
            precursor_template=precursor.precursor_sequence,
        )
        if released_foldback_precursor_domains(precursor_request) is None:
            raise ValueError("The exact precursor must satisfy the embedded foldback geometry.")
        if not self.feasibility.compatible:
            raise ValueError("A hairpin-junction route candidate must be compatible.")
        expected_feasibility = hairpin_junction_route_feasibility(
            geometry=geometry,
            released_foldback_precursor=precursor,
            basal_route=basal_route,
        )
        if self.feasibility != expected_feasibility:
            raise ValueError("Route feasibility must derive from the embedded physical inputs.")
        if state.precursor_top_strand != precursor.precursor_sequence:
            raise ValueError("Released state must project the selected exact precursor.")
        if state.nick != geometry.nick or state.release_cut != geometry.release_cut:
            raise ValueError("Released state events must equal the selected foldback geometry.")
        if state.active_product_precursor_span != geometry.active_product_span:
            raise ValueError("Released state span must equal the selected foldback geometry.")
        if state.active_nick_boundary != geometry.active_nick_boundary:
            raise ValueError("Released state nick boundary must equal the selected geometry.")
        expected_id = hairpin_junction_route_id(
            geometry=geometry,
            released_foldback_precursor=precursor,
            basal_route=basal_route,
        )
        if self.route_id != expected_id:
            raise ValueError("route_id must match the complete hairpin-junction route content.")
        return self


def hairpin_junction_route_order_key(
    route: HairpinJunctionRouteCandidate,
) -> tuple[object, ...]:
    """Return deterministic upstream order without caller desirability."""
    return (
        route.released_foldback_precursor.rank,
        route.basal_route.rank,
        route.route_id,
    )


class HairpinJunctionRouteSearchLimits(HopModel):
    """Hard budgets for evaluated joins and returned routes."""

    max_search_nodes: int = Field(ge=1)
    max_hits: int = Field(ge=1)


class HairpinJunctionRouteSearchResult(HopModel):
    """Bounded join of exact released foldbacks and basal processing routes."""

    schema_id: Literal["hop.hairpin-junction-route-search-result/v1"] = Field(
        default="hop.hairpin-junction-route-search-result/v1",
        alias="schema",
    )
    status: HairpinJunctionRouteStatus
    released_precursors: ReleasedFoldbackPrecursorSearchResult
    basal_routes: BasalProcessingRouteSearchResult
    limits: HairpinJunctionRouteSearchLimits
    hits: tuple[HairpinJunctionRouteCandidate, ...]
    feasibility: tuple[HairpinJunctionRouteFeasibility, ...]
    available_pair_count: int = Field(ge=0)
    search_nodes_examined: int = Field(ge=0)
    observed_hit_count: int = Field(ge=0)
    truncated_by: tuple[HairpinJunctionRouteTruncation, ...] = ()

    @model_validator(mode="after")
    def validate_search(self) -> HairpinJunctionRouteSearchResult:
        geometry = self.released_precursors.request.geometry
        expected_pair_count = len(self.released_precursors.hits) * len(self.basal_routes.hits)
        if self.available_pair_count != expected_pair_count:
            raise ValueError("available_pair_count must equal the returned upstream cross-product.")
        expected_examined = min(expected_pair_count, self.limits.max_search_nodes)
        if self.search_nodes_examined != expected_examined:
            raise ValueError("search_nodes_examined must exhaust the available route-node budget.")
        expected_pairs = tuple(
            islice(
                product(self.released_precursors.hits, self.basal_routes.hits),
                expected_examined,
            )
        )
        if len(self.feasibility) != expected_examined:
            raise ValueError("Route feasibility rows must equal examined route nodes.")
        for row, (precursor, basal_route) in zip(
            self.feasibility,
            expected_pairs,
            strict=True,
        ):
            expected_row = hairpin_junction_route_feasibility(
                geometry=geometry,
                released_foldback_precursor=precursor,
                basal_route=basal_route,
            )
            if row != expected_row:
                raise ValueError("Route feasibility rows must replay canonical upstream pairs.")
        compatible = tuple(row for row in self.feasibility if row.compatible)
        if self.observed_hit_count != len(compatible):
            raise ValueError("observed_hit_count must equal compatible route rows.")
        expected_returned = min(self.observed_hit_count, self.limits.max_hits)
        if len(self.hits) != expected_returned:
            raise ValueError("Returned routes must exhaust the available hit budget.")
        if tuple(route.rank for route in self.hits) != tuple(range(1, len(self.hits) + 1)):
            raise ValueError("Returned route ranks must be contiguous and one-based.")
        if self.hits != tuple(sorted(self.hits, key=hairpin_junction_route_order_key)):
            raise ValueError("Returned routes must use canonical upstream order.")
        pairs_by_ids = {
            (precursor.candidate_id, basal_route.route_id): (precursor, basal_route)
            for precursor, basal_route in expected_pairs
        }
        expected_ids = []
        for row in compatible[: self.limits.max_hits]:
            precursor, basal_route = pairs_by_ids[
                (row.released_foldback_precursor_id, row.basal_route_id)
            ]
            expected_ids.append(
                hairpin_junction_route_id(
                    geometry=geometry,
                    released_foldback_precursor=precursor,
                    basal_route=basal_route,
                )
            )
        if tuple(route.route_id for route in self.hits) != tuple(expected_ids):
            raise ValueError("Returned routes must project compatible feasibility rows.")

        expected_truncation: list[HairpinJunctionRouteTruncation] = []
        if self.released_precursors.status == "truncated":
            expected_truncation.append("released_precursors")
        if self.basal_routes.status == "truncated":
            expected_truncation.append("basal_routes")
        if self.search_nodes_examined < self.available_pair_count:
            expected_truncation.append("max_search_nodes")
        if self.observed_hit_count > self.limits.max_hits:
            expected_truncation.append("max_hits")
        if self.truncated_by != tuple(expected_truncation):
            raise ValueError("truncated_by must describe upstream and local bounds exactly.")
        if (self.status == "truncated") != bool(self.truncated_by):
            raise ValueError("Truncated status and route truncation evidence must agree.")
        if self.status == "complete" and not self.hits:
            raise ValueError("A complete hairpin-junction route search must return routes.")
        if self.status == "infeasible":
            if self.search_nodes_examined != self.available_pair_count:
                raise ValueError("An infeasible route search must examine every available pair.")
            if self.observed_hit_count or self.hits:
                raise ValueError("An infeasible route search cannot contain compatible routes.")
        return self


__all__ = [
    "HairpinJunctionRouteBlocker",
    "HairpinJunctionRouteCandidate",
    "HairpinJunctionRouteFeasibility",
    "HairpinJunctionRouteSearchLimits",
    "HairpinJunctionRouteSearchResult",
    "HairpinJunctionRouteTruncation",
]
