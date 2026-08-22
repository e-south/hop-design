"""Strict contracts for bounded released-foldback geometry discovery."""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from itertools import islice
from math import prod
from typing import Literal

from pydantic import Field, field_validator, model_validator

from hop_design.models.base import HopModel
from hop_design.models.catalog import ProcessingCatalog, SiteOrientation
from hop_design.models.coordinates import BasePairCount, Boundary, NucleotideCount, Span
from hop_design.models.references import ReferenceId
from hop_design.models.strand_state import DuplexCut, NickEvent, StrandExposureRoute

ReleasedFoldbackGeometryStatus = Literal["complete", "infeasible", "truncated"]
ReleasedFoldbackGeometryTruncation = Literal["max_search_nodes", "max_hits"]
ReleasedFoldbackHitKind = Literal["exact", "nearest"]
ExactBase = Literal["A", "C", "G", "T"]
WatsonCrickPair = Literal["AT", "CG", "GC", "TA"]


class ReleasedFoldbackGeometryBlocker(StrEnum):
    """Independent physical reasons why one geometry cannot be realized."""

    NICK_SITE_BEFORE_ORIGIN = "nick_site_before_origin"
    RELEASE_SITE_BEFORE_ORIGIN = "release_site_before_origin"
    RELEASE_SITE_NOT_DOWNSTREAM_OF_NICK = "release_site_not_downstream_of_nick"
    INCOMPLETE_DOWNSTREAM_SEPARATION = "incomplete_downstream_separation"
    PROCESSING_DOMAIN_CONFLICT = "processing_domain_conflict"
    FOLDBACK_PAIRING_DOMAIN_CONFLICT = "foldback_pairing_domain_conflict"


_BLOCKER_ORDER = {blocker: index for index, blocker in enumerate(ReleasedFoldbackGeometryBlocker)}
_PAIR_ORDER: tuple[WatsonCrickPair, ...] = ("AT", "CG", "GC", "TA")


class ReleasedFoldbackBaseDomain(HopModel):
    """Allowed exact bases at one precursor top-strand coordinate."""

    coordinate: int = Field(ge=0)
    allowed_bases: tuple[ExactBase, ...]

    @field_validator("allowed_bases", mode="before")
    @classmethod
    def normalize_allowed_bases(cls, value: object) -> object:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def validate_domain(self) -> ReleasedFoldbackBaseDomain:
        if tuple(sorted(set(self.allowed_bases))) != self.allowed_bases:
            raise ValueError("Allowed bases must be unique and use lexical order.")
        return self


class FoldbackPairingDomain(HopModel):
    """Allowed Watson-Crick choices for one antiparallel foldback pair."""

    left_coordinate: int = Field(ge=0)
    right_coordinate: int = Field(ge=0)
    allowed_pairs: tuple[WatsonCrickPair, ...]

    @field_validator("allowed_pairs", mode="before")
    @classmethod
    def normalize_allowed_pairs(cls, value: object) -> object:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def validate_domain(self) -> FoldbackPairingDomain:
        if self.left_coordinate >= self.right_coordinate:
            raise ValueError("Foldback pair coordinates must be ordered left to right.")
        canonical = tuple(pair for pair in _PAIR_ORDER if pair in self.allowed_pairs)
        if canonical != self.allowed_pairs or len(set(self.allowed_pairs)) != len(
            self.allowed_pairs
        ):
            raise ValueError("Allowed pairs must be unique and use canonical order.")
        return self


class ReleasedFoldbackGeometryRequest(HopModel):
    """Caller-authored released-foldback target and boundary window."""

    schema_id: Literal["hop.released-foldback-geometry-request/v1"] = Field(
        default="hop.released-foldback-geometry-request/v1",
        alias="schema",
    )
    target_nick_boundary: Boundary
    paired_tract: BasePairCount
    turn_length: NucleotideCount
    route: StrandExposureRoute
    max_boundary_displacement: NucleotideCount
    require_release_site_downstream_of_nick: bool
    require_complete_downstream_separation: bool

    @model_validator(mode="after")
    def validate_foldback_extent(self) -> ReleasedFoldbackGeometryRequest:
        if self.paired_tract.value < 1:
            raise ValueError("Released-foldback geometry requires at least one base pair.")
        return self


class ReleasedFoldbackGeometrySearchLimits(HopModel):
    """Hard budgets for examined geometries and returned hits."""

    max_search_nodes: int = Field(ge=1)
    max_hits: int = Field(ge=1)


class ReleasedFoldbackGeometryFeasibility(HopModel):
    """Complete physical audit for one agent pair, boundary, and orientation."""

    nicking_agent_id: ReferenceId
    release_agent_id: ReferenceId
    nick_orientation: SiteOrientation
    release_orientation: SiteOrientation
    oriented_nick_motif_top_5to3: str
    oriented_release_motif_top_5to3: str
    evaluated_nick_boundary: Boundary
    boundary_displacement: NucleotideCount
    hit_kind: ReleasedFoldbackHitKind
    nick_site_start: int
    nick_site_end: int
    release_site_start: int
    release_site_end: int
    nick: NickEvent
    release_cut: DuplexCut | None
    active_product_span: Span
    active_nick_boundary: Boundary
    required_precursor: NucleotideCount
    resolved_domains: tuple[ReleasedFoldbackBaseDomain, ...]
    pairing_domains: tuple[FoldbackPairingDomain, ...]
    candidate_sequence_count: int = Field(ge=0)
    blockers: tuple[ReleasedFoldbackGeometryBlocker, ...]
    compatible: bool

    @model_validator(mode="after")
    def validate_internal_contract(self) -> ReleasedFoldbackGeometryFeasibility:
        if self.nick_site_end - self.nick_site_start != len(self.oriented_nick_motif_top_5to3):
            raise ValueError("Nick-site extent must equal the oriented motif length.")
        if self.release_site_end - self.release_site_start != len(
            self.oriented_release_motif_top_5to3
        ):
            raise ValueError("Release-site extent must equal the oriented motif length.")
        displacement = abs(self.evaluated_nick_boundary.offset - self.nick.boundary.offset)
        if displacement != 0:
            raise ValueError("The nick event must use the evaluated boundary.")
        expected_kind = "exact" if self.boundary_displacement.value == 0 else "nearest"
        if self.hit_kind != expected_kind:
            raise ValueError("Hit kind must derive from boundary displacement.")
        if tuple(domain.coordinate for domain in self.resolved_domains) != tuple(
            range(self.required_precursor.value)
        ):
            raise ValueError("Resolved domains must cover the complete precursor in order.")
        if len(set(self.blockers)) != len(self.blockers):
            raise ValueError("Geometry blockers must not contain duplicates.")
        if self.blockers != tuple(sorted(self.blockers, key=_BLOCKER_ORDER.__getitem__)):
            raise ValueError("Geometry blockers must use canonical order.")
        if self.compatible != (not self.blockers):
            raise ValueError("compatible must be true exactly when blockers are empty.")
        paired_coordinates = {
            coordinate
            for pair in self.pairing_domains
            for coordinate in (pair.left_coordinate, pair.right_coordinate)
        }
        unpaired_counts = (
            len(domain.allowed_bases)
            for domain in self.resolved_domains
            if domain.coordinate not in paired_coordinates
        )
        expected_count = prod(
            (*unpaired_counts, *(len(pair.allowed_pairs) for pair in self.pairing_domains))
        )
        if self.candidate_sequence_count != expected_count:
            raise ValueError("candidate_sequence_count must derive from independent domains.")
        if self.compatible and self.candidate_sequence_count < 1:
            raise ValueError("A compatible geometry must admit at least one sequence.")
        return self


def released_foldback_geometry_id(row: ReleasedFoldbackGeometryFeasibility) -> str:
    """Return content identity for one compatible physical geometry."""
    payload = row.model_dump(mode="json", by_alias=True)
    content = (
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"
    ).encode("utf-8")
    return f"hop:released-foldback-geometry/{hashlib.sha256(content).hexdigest()}@1"


class ReleasedFoldbackGeometryHit(ReleasedFoldbackGeometryFeasibility):
    """One compatible released-foldback geometry in policy-neutral order."""

    candidate_id: str = Field(pattern=r"^hop:released-foldback-geometry/[0-9a-f]{64}@1$")
    rank: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_hit(self) -> ReleasedFoldbackGeometryHit:
        if not self.compatible:
            raise ValueError("A released-foldback hit must be compatible.")
        feasibility = ReleasedFoldbackGeometryFeasibility.model_validate(
            self.model_dump(mode="python", exclude={"candidate_id", "rank"})
        )
        if self.candidate_id != released_foldback_geometry_id(feasibility):
            raise ValueError("candidate_id must match the complete geometry content.")
        return self


def released_foldback_hit_order_key(
    hit: ReleasedFoldbackGeometryHit | ReleasedFoldbackGeometryFeasibility,
) -> tuple[object, ...]:
    """Return exact-first physical order without caller desirability."""
    return (
        0 if hit.hit_kind == "exact" else 1,
        hit.boundary_displacement.value,
        hit.evaluated_nick_boundary.offset,
        hit.nicking_agent_id,
        hit.release_agent_id,
        hit.release_orientation,
    )


class ReleasedFoldbackGeometrySearchResult(HopModel):
    """Bounded cross-agent geometry search with replayable feasibility evidence."""

    schema_id: Literal["hop.released-foldback-geometry-search-result/v1"] = Field(
        default="hop.released-foldback-geometry-search-result/v1",
        alias="schema",
    )
    status: ReleasedFoldbackGeometryStatus
    catalog: ProcessingCatalog
    request: ReleasedFoldbackGeometryRequest
    limits: ReleasedFoldbackGeometrySearchLimits
    hits: tuple[ReleasedFoldbackGeometryHit, ...]
    feasibility: tuple[ReleasedFoldbackGeometryFeasibility, ...]
    candidate_space_size: int = Field(ge=0)
    search_nodes_examined: int = Field(ge=0)
    observed_hit_count: int = Field(ge=0)
    truncated_by: tuple[ReleasedFoldbackGeometryTruncation, ...] = ()

    @model_validator(mode="after")
    def validate_search(self) -> ReleasedFoldbackGeometrySearchResult:
        from hop_design.models.discovery.released_foldback_evaluation import (
            evaluate_released_foldback_geometry,
            iter_released_foldback_geometry_nodes,
            released_foldback_candidate_space_size,
        )

        expected_space = released_foldback_candidate_space_size(
            catalog=self.catalog,
            request=self.request,
        )
        if self.candidate_space_size != expected_space:
            raise ValueError("candidate_space_size must derive from the complete geometry axes.")
        expected_examined = min(expected_space, self.limits.max_search_nodes)
        if self.search_nodes_examined != expected_examined:
            raise ValueError("search_nodes_examined must exhaust the available node budget.")
        nodes = tuple(
            islice(
                iter_released_foldback_geometry_nodes(
                    catalog=self.catalog,
                    request=self.request,
                ),
                expected_examined,
            )
        )
        expected_rows = tuple(
            evaluate_released_foldback_geometry(
                nicking_agent=nick,
                release_agent=release,
                release_orientation=orientation,
                evaluated_nick_boundary=boundary,
                request=self.request,
            )
            for boundary, nick, release, orientation in nodes
        )
        if self.feasibility != expected_rows:
            raise ValueError("Feasibility rows must replay canonical physical search nodes.")
        compatible = tuple(row for row in expected_rows if row.compatible)
        if self.observed_hit_count != len(compatible):
            raise ValueError("observed_hit_count must equal compatible examined rows.")
        ordered = tuple(sorted(compatible, key=released_foldback_hit_order_key))
        expected_rows_returned = ordered[: self.limits.max_hits]
        if len(self.hits) != len(expected_rows_returned):
            raise ValueError("Returned hits must exhaust the available hit budget.")
        if tuple(hit.rank for hit in self.hits) != tuple(range(1, len(self.hits) + 1)):
            raise ValueError("Returned hit ranks must be contiguous and one-based.")
        expected_ids = tuple(released_foldback_geometry_id(row) for row in expected_rows_returned)
        if tuple(hit.candidate_id for hit in self.hits) != expected_ids:
            raise ValueError("Returned hits must project compatible rows in physical order.")

        expected_truncation: list[ReleasedFoldbackGeometryTruncation] = []
        if expected_examined < expected_space:
            expected_truncation.append("max_search_nodes")
        if len(compatible) > self.limits.max_hits:
            expected_truncation.append("max_hits")
        if self.truncated_by != tuple(expected_truncation):
            raise ValueError("truncated_by must exactly describe node and hit truncation.")
        if (self.status == "truncated") != bool(self.truncated_by):
            raise ValueError("Truncated status and truncation evidence must agree.")
        if self.status == "complete" and not self.hits:
            raise ValueError("A complete search must return compatible geometries.")
        if self.status == "infeasible" and (self.observed_hit_count or self.hits):
            raise ValueError("An infeasible search cannot contain compatible geometries.")
        return self


__all__ = [
    "FoldbackPairingDomain",
    "ReleasedFoldbackBaseDomain",
    "ReleasedFoldbackGeometryBlocker",
    "ReleasedFoldbackGeometryFeasibility",
    "ReleasedFoldbackGeometryHit",
    "ReleasedFoldbackGeometryRequest",
    "ReleasedFoldbackGeometrySearchLimits",
    "ReleasedFoldbackGeometrySearchResult",
    "ReleasedFoldbackGeometryTruncation",
]
