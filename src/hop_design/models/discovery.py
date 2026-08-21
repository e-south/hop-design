"""Strict contracts for bounded processing-agent geometry discovery."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator, model_validator

from hop_design.models.base import HopModel
from hop_design.models.catalog import SiteOrientation
from hop_design.models.coordinates import BasePairCount, Boundary, NucleotideCount, Span
from hop_design.models.junction import Strand
from hop_design.models.references import ReferenceId
from hop_design.models.sequence import SequenceValidationError, normalize_dna_sequence
from hop_design.models.strand_state import NickEvent

NickingPlacementBlocker = Literal["HOP-DISC-001", "HOP-DISC-002"]
NickingPlacementHitKind = Literal["exact", "nearest"]
NickingPlacementTruncation = Literal["max_search_nodes", "max_hits"]


class NickingPlacementTarget(HopModel):
    """Desired nick and available downstream foldback geometry."""

    nick_boundary: Boundary
    nicked_strand: Strand
    paired_tract: BasePairCount
    available_turn: NucleotideCount

    @model_validator(mode="after")
    def validate_paired_tract(self) -> NickingPlacementTarget:
        if self.paired_tract.value == 0:
            raise ValueError("paired_tract must contain at least one base pair.")
        return self


class NickingPlacementFeasibility(HopModel):
    """Geometry facts for one catalog agent in the target strand orientation."""

    agent_id: ReferenceId
    orientation: SiteOrientation
    oriented_motif_5to3: str
    site_start_at_target_boundary: int
    site_end_at_target_boundary: int
    exact_blockers: tuple[NickingPlacementBlocker, ...]
    earliest_feasible_boundary: Boundary | None

    @field_validator("oriented_motif_5to3", mode="before")
    @classmethod
    def normalize_motif(cls, value: object) -> str:
        if not isinstance(value, str):
            raise SequenceValidationError("DNA sequence must be a string.")
        return normalize_dna_sequence(value, allow_degenerate=True)

    @model_validator(mode="after")
    def validate_site_extent(self) -> NickingPlacementFeasibility:
        if self.site_end_at_target_boundary - self.site_start_at_target_boundary != len(
            self.oriented_motif_5to3
        ):
            raise ValueError("Target-relative site extent must equal the oriented motif length.")
        if len(set(self.exact_blockers)) != len(self.exact_blockers):
            raise ValueError("exact_blockers must not contain duplicates.")
        return self


class NickingPlacementHit(HopModel):
    """One exact or nearest physically placeable nicking-agent geometry."""

    hit_kind: NickingPlacementHitKind
    agent_id: ReferenceId
    orientation: SiteOrientation
    oriented_motif_5to3: str
    site_span: Span
    nick: NickEvent
    boundary_displacement: NucleotideCount
    required_precursor: NucleotideCount
    required_turn: NucleotideCount

    @field_validator("oriented_motif_5to3", mode="before")
    @classmethod
    def normalize_motif(cls, value: object) -> str:
        if not isinstance(value, str):
            raise SequenceValidationError("DNA sequence must be a string.")
        return normalize_dna_sequence(value, allow_degenerate=True)

    @model_validator(mode="after")
    def validate_site_extent(self) -> NickingPlacementHit:
        if self.site_span.length.value != len(self.oriented_motif_5to3):
            raise ValueError("Placed site extent must equal the oriented motif length.")
        if self.required_precursor.value < self.site_span.end.offset:
            raise ValueError("Required precursor length must contain the complete motif site.")
        return self


class NickingPlacementSearchLimits(HopModel):
    """Hard budgets for catalog geometry discovery and returned hits."""

    max_search_nodes: int = Field(ge=1)
    max_hits: int = Field(ge=1)


class NickingPlacementSearchResult(HopModel):
    """Bounded discovery result with distinct search and result truncation."""

    status: Literal["complete", "infeasible", "truncated"]
    catalog_id: ReferenceId
    target: NickingPlacementTarget
    hits: tuple[NickingPlacementHit, ...]
    feasibility: tuple[NickingPlacementFeasibility, ...]
    candidate_space_size: int = Field(ge=0)
    search_nodes_examined: int = Field(ge=0)
    observed_hit_count: int = Field(ge=0)
    truncated_by: tuple[NickingPlacementTruncation, ...] = ()

    @model_validator(mode="after")
    def validate_search_accounting(self) -> NickingPlacementSearchResult:
        if self.search_nodes_examined > self.candidate_space_size:
            raise ValueError("search_nodes_examined cannot exceed candidate_space_size.")
        if len(self.feasibility) != self.search_nodes_examined:
            raise ValueError("Feasibility rows must equal the number of examined search nodes.")
        if len({row.agent_id for row in self.feasibility}) != len(self.feasibility):
            raise ValueError("Feasibility rows must contain unique agent ids.")
        if self.observed_hit_count > self.search_nodes_examined:
            raise ValueError("observed_hit_count cannot exceed examined search nodes.")
        if len(self.hits) > self.observed_hit_count:
            raise ValueError("Returned hits cannot exceed observed hits.")

        expected_reasons: list[NickingPlacementTruncation] = []
        if self.search_nodes_examined < self.candidate_space_size:
            expected_reasons.append("max_search_nodes")
        if len(self.hits) < self.observed_hit_count:
            expected_reasons.append("max_hits")
        if self.truncated_by != tuple(expected_reasons):
            raise ValueError("truncated_by must exactly describe incomplete search or hit output.")
        if (self.status == "truncated") != bool(self.truncated_by):
            raise ValueError("truncated status and truncation reasons must be declared together.")

        if self.status == "infeasible" and (self.observed_hit_count or self.hits):
            raise ValueError("An infeasible search cannot contain hits.")
        if self.status == "complete" and not self.hits:
            raise ValueError("A complete search must return every observed hit.")

        paired_bp = self.target.paired_tract.value
        for hit in self.hits:
            if hit.nick.strand is not self.target.nicked_strand:
                raise ValueError("Every discovery hit must nick the target strand.")
            displacement = abs(hit.nick.boundary.offset - self.target.nick_boundary.offset)
            if hit.boundary_displacement.value != displacement:
                raise ValueError("Hit displacement must derive from the target nick boundary.")
            expected_kind = "exact" if displacement == 0 else "nearest"
            if hit.hit_kind != expected_kind:
                raise ValueError("Hit kind must agree with its target-boundary displacement.")
            paired_end = hit.nick.boundary.offset + paired_bp
            expected_precursor = max(paired_end, hit.site_span.end.offset)
            expected_turn = max(0, hit.site_span.end.offset - paired_end)
            if hit.required_precursor.value != expected_precursor:
                raise ValueError("Required precursor length must derive from placed geometry.")
            if hit.required_turn.value != expected_turn:
                raise ValueError("Required turn length must derive from placed geometry.")
        return self


__all__ = [
    "NickingPlacementBlocker",
    "NickingPlacementFeasibility",
    "NickingPlacementHit",
    "NickingPlacementSearchLimits",
    "NickingPlacementSearchResult",
    "NickingPlacementTarget",
]
