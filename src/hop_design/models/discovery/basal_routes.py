"""Strict contracts for bounded basal processing-route composition."""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from itertools import islice, product
from typing import Literal

from pydantic import Field, field_validator, model_validator

from hop_design.models.base import HopModel
from hop_design.models.coordinates import Boundary
from hop_design.models.discovery.basal_candidates import (
    BasalCandidate,
    BasalCandidateSearchResult,
)
from hop_design.models.discovery.basal_processing import (
    BasalProcessingGeometryHit,
    BasalProcessingGeometrySearchResult,
    BasalReleaseGeometry,
)
from hop_design.models.junction import Strand
from hop_design.models.physical import opposite_strand
from hop_design.models.references import ReferenceId
from hop_design.models.sequence import (
    SequenceValidationError,
    iupac_bases,
    normalize_dna_sequence,
    reverse_complement_iupac,
)
from hop_design.models.strand_state import NickEvent

BasalProcessingRouteStatus = Literal["complete", "infeasible", "truncated"]
BasalProcessingRouteTruncation = Literal[
    "basal_candidates",
    "processing_geometries",
    "max_search_nodes",
    "max_hits",
]


class BasalProcessingRouteBlocker(StrEnum):
    """Physical reasons why one basal pair and process geometry cannot compose."""

    RETAINED_SCAR_DOMAIN_CONFLICT = "retained_scar_domain_conflict"
    RETAINED_RELEASE_SITE_PRESENT = "retained_release_site_present"


_BLOCKER_ORDER = {blocker: index for index, blocker in enumerate(BasalProcessingRouteBlocker)}


class BasalProcessingRouteFeasibility(HopModel):
    """One evaluated basal-candidate by processing-geometry join."""

    basal_candidate_id: ReferenceId
    processing_geometry_id: ReferenceId
    retained_scar: str
    blockers: tuple[BasalProcessingRouteBlocker, ...]
    compatible: bool

    @field_validator("retained_scar", mode="before")
    @classmethod
    def normalize_retained_scar(cls, value: object) -> str:
        if not isinstance(value, str):
            raise SequenceValidationError("DNA sequence must be a string.")
        normalized = normalize_dna_sequence(value, allow_degenerate=False)
        if len(normalized) != 4:
            raise ValueError("A basal processing route requires a four-nucleotide scar.")
        return normalized

    @model_validator(mode="after")
    def validate_outcome(self) -> BasalProcessingRouteFeasibility:
        if len(set(self.blockers)) != len(self.blockers):
            raise ValueError("Basal route blockers must not contain duplicates.")
        if self.blockers != tuple(sorted(self.blockers, key=_BLOCKER_ORDER.__getitem__)):
            raise ValueError("Basal route blockers must use canonical order.")
        if self.compatible != (not self.blockers):
            raise ValueError("compatible must be true exactly when blockers are empty.")
        return self


def _contains_iupac_site(sequence: str, motif: str) -> bool:
    for oriented in (motif, reverse_complement_iupac(motif)):
        if len(oriented) > len(sequence):
            continue
        for start in range(len(sequence) - len(oriented) + 1):
            if all(
                base in iupac_bases(symbol)
                for base, symbol in zip(
                    sequence[start : start + len(oriented)],
                    oriented,
                    strict=True,
                )
            ):
                return True
    return False


def basal_processing_route_feasibility(
    *,
    release: BasalReleaseGeometry,
    basal_candidate: BasalCandidate,
    processing_geometry: BasalProcessingGeometryHit,
) -> BasalProcessingRouteFeasibility:
    """Derive one exact basal-candidate by processing-geometry outcome."""
    scar = basal_candidate.pairing.left_arm
    blockers: list[BasalProcessingRouteBlocker] = []
    if any(
        base not in domain.allowed_bases
        for base, domain in zip(
            scar,
            processing_geometry.retained_scar_domains,
            strict=True,
        )
    ):
        blockers.append(BasalProcessingRouteBlocker.RETAINED_SCAR_DOMAIN_CONFLICT)
    if _contains_iupac_site(scar, release.oriented_motif_top_5to3):
        blockers.append(BasalProcessingRouteBlocker.RETAINED_RELEASE_SITE_PRESENT)
    return BasalProcessingRouteFeasibility(
        basal_candidate_id=basal_candidate.candidate_id,
        processing_geometry_id=processing_geometry.candidate_id,
        retained_scar=scar,
        blockers=tuple(blockers),
        compatible=not blockers,
    )


def basal_processing_route_id(
    *,
    release: BasalReleaseGeometry,
    basal_candidate: BasalCandidate,
    processing_geometry: BasalProcessingGeometryHit,
) -> str:
    """Return content identity for one complete basal processing route."""
    payload = {
        "release": release.model_dump(mode="json"),
        "basal_candidate_id": basal_candidate.candidate_id,
        "processing_geometry_id": processing_geometry.candidate_id,
    }
    content = (
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"
    ).encode("utf-8")
    return f"hop:basal-processing-route/{hashlib.sha256(content).hexdigest()}@1"


class BasalProcessingRouteCandidate(HopModel):
    """One exact basal pair joined to one compatible terminal process geometry."""

    route_id: str = Field(pattern=r"^hop:basal-processing-route/[0-9a-f]{64}@1$")
    canonical_ordinal: int = Field(ge=1)
    release: BasalReleaseGeometry
    basal_candidate: BasalCandidate
    processing_geometry: BasalProcessingGeometryHit
    feasibility: BasalProcessingRouteFeasibility
    terminal_nick: NickEvent
    surviving_strand: Strand

    @model_validator(mode="after")
    def validate_route(self) -> BasalProcessingRouteCandidate:
        basal = self.basal_candidate
        geometry = self.processing_geometry
        if not self.feasibility.compatible:
            raise ValueError("A basal processing route candidate must be compatible.")
        if self.feasibility.basal_candidate_id != basal.candidate_id:
            raise ValueError("Route feasibility must reference the embedded basal candidate.")
        if self.feasibility.processing_geometry_id != geometry.candidate_id:
            raise ValueError("Route feasibility must reference the embedded process geometry.")
        if self.feasibility.retained_scar != basal.pairing.left_arm:
            raise ValueError("The retained scar must equal the basal left arm.")
        if self.release.release_agent_id != geometry.release_agent_id:
            raise ValueError("The release and terminal processing geometry must use one agent.")
        expected_feasibility = basal_processing_route_feasibility(
            release=self.release,
            basal_candidate=basal,
            processing_geometry=geometry,
        )
        if self.feasibility != expected_feasibility:
            raise ValueError("Route feasibility must derive from the embedded physical inputs.")
        expected_nick = NickEvent(
            boundary=Boundary(offset=geometry.nick_boundary),
            strand=geometry.nicked_strand,
        )
        if self.terminal_nick != expected_nick:
            raise ValueError("The route terminal nick must derive from its process geometry.")
        expected_survivor = opposite_strand(geometry.nicked_strand)
        if self.surviving_strand is not expected_survivor:
            raise ValueError("The surviving strand must be opposite the terminal-nicked strand.")
        expected_id = basal_processing_route_id(
            release=self.release,
            basal_candidate=basal,
            processing_geometry=geometry,
        )
        if self.route_id != expected_id:
            raise ValueError("route_id must match the complete basal processing route content.")
        return self


def basal_processing_route_order_key(
    route: BasalProcessingRouteCandidate,
) -> tuple[object, ...]:
    """Return deterministic physical order without caller desirability."""
    return (
        route.basal_candidate.canonical_ordinal,
        route.processing_geometry.canonical_ordinal,
        route.route_id,
    )


class BasalProcessingRouteSearchLimits(HopModel):
    """Hard budgets for evaluated joins and returned basal routes."""

    max_search_nodes: int = Field(ge=1)
    max_hits: int = Field(ge=1)


class BasalProcessingRouteSearchResult(HopModel):
    """Bounded join of basal candidates and terminal processing geometries."""

    schema_id: Literal["hop.basal-processing-route-search-result/v2"] = Field(
        default="hop.basal-processing-route-search-result/v2",
        alias="schema",
    )
    status: BasalProcessingRouteStatus
    basal_candidates: BasalCandidateSearchResult
    processing_geometries: BasalProcessingGeometrySearchResult
    limits: BasalProcessingRouteSearchLimits
    hits: tuple[BasalProcessingRouteCandidate, ...]
    feasibility: tuple[BasalProcessingRouteFeasibility, ...]
    available_pair_count: int = Field(ge=0)
    search_nodes_examined: int = Field(ge=0)
    observed_hit_count: int = Field(ge=0)
    truncated_by: tuple[BasalProcessingRouteTruncation, ...] = ()

    @model_validator(mode="after")
    def validate_search(self) -> BasalProcessingRouteSearchResult:
        expected_pair_count = len(self.basal_candidates.hits) * len(self.processing_geometries.hits)
        if self.available_pair_count != expected_pair_count:
            raise ValueError("available_pair_count must equal the returned upstream cross-product.")
        expected_examined = min(self.available_pair_count, self.limits.max_search_nodes)
        if self.search_nodes_examined != expected_examined:
            raise ValueError("search_nodes_examined must exhaust the available route-node budget.")
        expected_pairs = tuple(
            islice(
                product(self.basal_candidates.hits, self.processing_geometries.hits),
                expected_examined,
            )
        )
        if len(self.feasibility) != self.search_nodes_examined:
            raise ValueError("Route feasibility rows must equal examined route nodes.")
        for row, (basal, geometry) in zip(
            self.feasibility,
            expected_pairs[: self.search_nodes_examined],
            strict=True,
        ):
            if (
                row.basal_candidate_id != basal.candidate_id
                or row.processing_geometry_id != geometry.candidate_id
                or row.retained_scar != basal.pairing.left_arm
            ):
                raise ValueError("Route feasibility rows must follow canonical upstream pairs.")
            expected_row = basal_processing_route_feasibility(
                release=self.processing_geometries.release,
                basal_candidate=basal,
                processing_geometry=geometry,
            )
            if row != expected_row:
                raise ValueError("Route feasibility rows must replay their physical inputs.")
        compatible = tuple(row for row in self.feasibility if row.compatible)
        if self.observed_hit_count != len(compatible):
            raise ValueError("observed_hit_count must equal compatible route rows.")
        expected_returned = min(self.observed_hit_count, self.limits.max_hits)
        if len(self.hits) != expected_returned:
            raise ValueError("Returned routes must exhaust the available hit budget.")
        observed_ordinals = tuple(route.canonical_ordinal for route in self.hits)
        if observed_ordinals != tuple(range(1, len(self.hits) + 1)):
            raise ValueError("Returned route ordinals must be contiguous and one-based.")
        if self.hits != tuple(sorted(self.hits, key=basal_processing_route_order_key)):
            raise ValueError("Returned routes must use canonical physical order.")
        expected_ids = []
        pair_by_ids = {
            (basal.candidate_id, geometry.candidate_id): (basal, geometry)
            for basal, geometry in expected_pairs
        }
        for row in compatible[: self.limits.max_hits]:
            basal, geometry = pair_by_ids[(row.basal_candidate_id, row.processing_geometry_id)]
            expected_ids.append(
                basal_processing_route_id(
                    release=self.processing_geometries.release,
                    basal_candidate=basal,
                    processing_geometry=geometry,
                )
            )
        if tuple(route.route_id for route in self.hits) != tuple(expected_ids):
            raise ValueError("Returned routes must project compatible feasibility rows.")

        expected_truncation: list[BasalProcessingRouteTruncation] = []
        if self.basal_candidates.status == "truncated":
            expected_truncation.append("basal_candidates")
        if self.processing_geometries.status == "truncated":
            expected_truncation.append("processing_geometries")
        if self.search_nodes_examined < self.available_pair_count:
            expected_truncation.append("max_search_nodes")
        if self.observed_hit_count > self.limits.max_hits:
            expected_truncation.append("max_hits")
        if self.truncated_by != tuple(expected_truncation):
            raise ValueError(
                "truncated_by must describe upstream, node, and hit truncation exactly."
            )
        if (self.status == "truncated") != bool(self.truncated_by):
            raise ValueError("Truncated status and route truncation evidence must agree.")
        if self.status == "complete" and not self.hits:
            raise ValueError("A complete basal route search must return compatible routes.")
        if self.status == "infeasible" and (self.observed_hit_count or self.hits):
            raise ValueError("An infeasible basal route search cannot contain routes.")
        return self


__all__ = [
    "BasalProcessingRouteBlocker",
    "BasalProcessingRouteCandidate",
    "BasalProcessingRouteFeasibility",
    "BasalProcessingRouteSearchLimits",
    "BasalProcessingRouteSearchResult",
    "BasalProcessingRouteTruncation",
]
