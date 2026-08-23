"""Strict contracts for bounded foldback-precursor sequence discovery."""

from __future__ import annotations

from enum import StrEnum
from itertools import pairwise
from typing import Literal

from pydantic import Field, field_validator, model_validator

from hop_design.models.base import HopModel
from hop_design.models.catalog import NickingAgent, ResolvedNickSite
from hop_design.models.discovery.placements import (
    NickingPlacementHit,
    NickingPlacementTarget,
)
from hop_design.models.foldback import FoldbackEvaluation
from hop_design.models.physical import orient_nick_geometry
from hop_design.models.sequence import (
    SequenceValidationError,
    normalize_dna_sequence,
)
from hop_design.serialization import canonical_json_bytes, sha256_digest

CandidateSearchStatus = Literal["complete", "infeasible", "truncated"]
CandidateSearchTruncation = Literal["max_search_nodes", "max_hits"]
CandidateRejectionCode = Literal["HOP-CAND-001", "HOP-CAND-002"]


def _normalize_optional_dna(value: object, *, allow_degenerate: bool) -> str:
    if not isinstance(value, str):
        raise SequenceValidationError("DNA sequence must be a string.")
    if not value or value.isspace():
        return ""
    return normalize_dna_sequence(value, allow_degenerate=allow_degenerate)


class AdditionalNickConstraint(StrEnum):
    """Caller policy for recognition sites beyond the selected placement."""

    ALLOW = "allow"
    FORBID_TARGET_STRAND = "forbid_target_strand"
    FORBID_ANY = "forbid_any"


class FoldbackPrecursorSearchRequest(HopModel):
    """Sequence domains for one selected nicking placement and foldback target."""

    schema_id: Literal["hop.foldback-precursor-search/v1"] = Field(
        default="hop.foldback-precursor-search/v1", alias="schema"
    )
    agent: NickingAgent
    target: NickingPlacementTarget
    placement: NickingPlacementHit
    precursor_template: str
    turn_extension_template: str
    additional_nicks: AdditionalNickConstraint

    @field_validator("precursor_template", mode="before")
    @classmethod
    def normalize_precursor_template(cls, value: object) -> str:
        if not isinstance(value, str):
            raise SequenceValidationError("DNA sequence must be a string.")
        return normalize_dna_sequence(value, allow_degenerate=True)

    @field_validator("turn_extension_template", mode="before")
    @classmethod
    def normalize_turn_extension_template(cls, value: object) -> str:
        return _normalize_optional_dna(value, allow_degenerate=True)

    @model_validator(mode="after")
    def validate_selected_placement(self) -> FoldbackPrecursorSearchRequest:
        placement = self.placement
        target = self.target
        agent = self.agent
        if placement.agent_id != agent.agent_id:
            raise ValueError("placement.agent_id must match the selected agent.")

        geometry = orient_nick_geometry(
            motif_top_5to3=agent.motif_top_5to3,
            native_nicked_strand=agent.nicked_strand,
            cut_offset=agent.cut_offset,
            target_strand=target.nicked_strand,
        )
        orientation = geometry.orientation
        oriented_motif = geometry.motif_top_5to3
        oriented_cut_offset = geometry.cut_offset

        target_boundary = target.nick_boundary.offset
        exact_site_start = target_boundary - oriented_cut_offset
        exact_site_end = exact_site_start + len(oriented_motif)
        available_end = target_boundary + target.paired_tract.value + target.available_turn.value
        exact_is_blocked = exact_site_start < 0 or exact_site_end > available_end
        if exact_is_blocked:
            extent_after_nick = len(oriented_motif) - oriented_cut_offset
            if extent_after_nick > target.paired_tract.value + target.available_turn.value:
                raise ValueError("placement is not feasible for the declared target.")
            expected_boundary = max(0, oriented_cut_offset)
        else:
            expected_boundary = target_boundary

        expected_start = expected_boundary - oriented_cut_offset
        expected_end = expected_start + len(oriented_motif)
        paired_end = expected_boundary + target.paired_tract.value
        expected_precursor = max(paired_end, expected_end)
        expected_turn = max(0, expected_end - paired_end)
        displacement = abs(expected_boundary - target_boundary)
        expected_kind = "exact" if displacement == 0 else "nearest"

        placement_facts = (
            placement.orientation == orientation,
            placement.oriented_motif_5to3 == oriented_motif,
            placement.site_span.start.offset == expected_start,
            placement.site_span.end.offset == expected_end,
            placement.nick.boundary.offset == expected_boundary,
            placement.nick.strand is target.nicked_strand,
            placement.boundary_displacement.value == displacement,
            placement.hit_kind == expected_kind,
            placement.required_precursor.value == expected_precursor,
            placement.required_turn.value == expected_turn,
        )
        if not all(placement_facts):
            raise ValueError("placement must replay exactly from the selected agent and target.")
        if len(self.precursor_template) != expected_precursor:
            raise ValueError("precursor_template length must equal placement.required_precursor.")
        expected_extension = target.available_turn.value - expected_turn
        if len(self.turn_extension_template) != expected_extension:
            raise ValueError(
                "turn_extension_template length must fill the remaining available turn."
            )
        return self


class FoldbackPrecursorSearchLimits(HopModel):
    """Hard budgets for concrete sequence enumeration and returned hits."""

    max_search_nodes: int = Field(ge=1)
    max_hits: int = Field(ge=1)


class CandidateRejectionSummary(HopModel):
    """Stable aggregate for one expected sequence-search rejection."""

    code: CandidateRejectionCode
    count: int = Field(ge=1)


def foldback_precursor_candidate_id(
    *,
    precursor_sequence: str,
    turn_extension: str,
    intended_site: ResolvedNickSite,
    extra_nick_sites: tuple[ResolvedNickSite, ...],
    evaluation: FoldbackEvaluation,
) -> str:
    """Return content identity for one exact foldback precursor candidate."""
    digest = sha256_digest(
        canonical_json_bytes(
            {
                "evaluation": evaluation.model_dump(mode="json", by_alias=True),
                "extra_nick_sites": [
                    site.model_dump(mode="json", by_alias=True) for site in extra_nick_sites
                ],
                "intended_site": intended_site.model_dump(mode="json", by_alias=True),
                "precursor_sequence": precursor_sequence,
                "turn_extension": turn_extension,
            }
        )
    ).removeprefix("sha256:")
    return f"hop:foldback-precursor-candidate/{digest}@2"


class FoldbackPrecursorCandidate(HopModel):
    """One exact precursor and foldback sequence for a selected placement."""

    candidate_id: str = Field(pattern=r"^hop:foldback-precursor-candidate/[0-9a-f]{64}@2$")
    precursor_sequence: str
    turn_extension: str
    intended_site: ResolvedNickSite
    extra_nick_sites: tuple[ResolvedNickSite, ...]
    extra_target_strand_nick_count: int = Field(ge=0)
    gc_fraction_added: float = Field(ge=0.0, le=1.0)
    max_homopolymer_run_added: int = Field(ge=1)
    evaluation: FoldbackEvaluation

    @field_validator("precursor_sequence", mode="before")
    @classmethod
    def normalize_precursor(cls, value: object) -> str:
        if not isinstance(value, str):
            raise SequenceValidationError("DNA sequence must be a string.")
        return normalize_dna_sequence(value, allow_degenerate=False)

    @field_validator("turn_extension", mode="before")
    @classmethod
    def normalize_turn_extension(cls, value: object) -> str:
        return _normalize_optional_dna(value, allow_degenerate=False)

    @model_validator(mode="after")
    def validate_projection(self) -> FoldbackPrecursorCandidate:
        if self.evaluation.precursor_sequence != self.precursor_sequence:
            raise ValueError("Candidate precursor must match its foldback evaluation.")
        if self.evaluation.turn_extension != self.turn_extension:
            raise ValueError("Candidate turn extension must match its foldback evaluation.")
        if self.intended_site in self.extra_nick_sites:
            raise ValueError("The intended site must not be repeated among extra nick sites.")
        if len(set(self.extra_nick_sites)) != len(self.extra_nick_sites):
            raise ValueError("extra_nick_sites must not contain duplicates.")
        observed_target_nicks = sum(
            site.nick.strand is self.intended_site.nick.strand for site in self.extra_nick_sites
        )
        if self.extra_target_strand_nick_count != observed_target_nicks:
            raise ValueError("Extra target-strand nick count must match extra_nick_sites.")
        added = f"{self.turn_extension}{self.evaluation.foldback_arm}"
        observed_gc = sum(base in "GC" for base in added) / len(added)
        if abs(self.gc_fraction_added - observed_gc) > 1e-12:
            raise ValueError("Added-sequence GC fraction must match the evaluated sequence.")
        longest = 1
        run = 1
        for previous, current in pairwise(added):
            run = run + 1 if current == previous else 1
            longest = max(longest, run)
        if self.max_homopolymer_run_added != longest:
            raise ValueError("Added-sequence homopolymer run must match the evaluated sequence.")
        expected_id = foldback_precursor_candidate_id(
            precursor_sequence=self.precursor_sequence,
            turn_extension=self.turn_extension,
            intended_site=self.intended_site,
            extra_nick_sites=self.extra_nick_sites,
            evaluation=self.evaluation,
        )
        if self.candidate_id != expected_id:
            raise ValueError("candidate_id must match the complete foldback candidate content.")
        return self


def foldback_precursor_candidate_order_key(
    candidate: FoldbackPrecursorCandidate,
) -> tuple[str, str, str]:
    """Return literal content order without preferring candidate measurements."""
    return (
        candidate.precursor_sequence,
        candidate.turn_extension,
        candidate.candidate_id,
    )


class FoldbackPrecursorSearchResult(HopModel):
    """Bounded concrete candidate search with explicit completion evidence."""

    status: CandidateSearchStatus
    request: FoldbackPrecursorSearchRequest
    limits: FoldbackPrecursorSearchLimits
    hits: tuple[FoldbackPrecursorCandidate, ...]
    candidate_space_size: int = Field(ge=0)
    search_nodes_examined: int = Field(ge=0)
    observed_hit_count: int = Field(ge=0)
    rejections: tuple[CandidateRejectionSummary, ...] = ()
    truncated_by: tuple[CandidateSearchTruncation, ...] = ()

    @model_validator(mode="after")
    def validate_accounting(self) -> FoldbackPrecursorSearchResult:
        if self.search_nodes_examined > self.candidate_space_size:
            raise ValueError("search_nodes_examined cannot exceed candidate_space_size.")
        if self.observed_hit_count > self.search_nodes_examined:
            raise ValueError("observed_hit_count cannot exceed examined search nodes.")
        if len(self.hits) > self.observed_hit_count:
            raise ValueError("Returned hits cannot exceed observed hits.")
        if self.hits != tuple(sorted(self.hits, key=foldback_precursor_candidate_order_key)):
            raise ValueError("Returned hits must use canonical content order.")
        if len({item.code for item in self.rejections}) != len(self.rejections):
            raise ValueError("Rejection summaries must contain unique codes.")

        expected_reasons: list[CandidateSearchTruncation] = []
        if self.search_nodes_examined < self.candidate_space_size:
            expected_reasons.append("max_search_nodes")
        if len(self.hits) < self.observed_hit_count:
            expected_reasons.append("max_hits")
        if self.truncated_by != tuple(expected_reasons):
            raise ValueError("truncated_by must exactly describe incomplete search or hit output.")
        if (self.status == "truncated") != bool(self.truncated_by):
            raise ValueError("truncated status and truncation reasons must be declared together.")
        if self.status == "infeasible":
            if self.search_nodes_examined != self.candidate_space_size:
                raise ValueError("An infeasible search must examine the full candidate space.")
            if self.observed_hit_count or self.hits:
                raise ValueError("An infeasible search cannot contain hits.")
        if self.status == "complete":
            if not self.hits:
                raise ValueError("A complete search must contain at least one hit.")
            if self.search_nodes_examined != self.candidate_space_size:
                raise ValueError("A complete search must examine the full candidate space.")

        rejected_candidates = sum(
            item.count for item in self.rejections if item.code == "HOP-CAND-002"
        )
        if rejected_candidates != self.search_nodes_examined - self.observed_hit_count:
            raise ValueError("Candidate rejection counts must match examined infeasible nodes.")
        template_conflicts = sum(
            item.count for item in self.rejections if item.code == "HOP-CAND-001"
        )
        if (self.candidate_space_size == 0) != (template_conflicts == 1):
            raise ValueError("Template conflict evidence must agree with an empty candidate space.")
        return self


__all__ = [
    "AdditionalNickConstraint",
    "CandidateRejectionSummary",
    "FoldbackPrecursorCandidate",
    "FoldbackPrecursorSearchLimits",
    "FoldbackPrecursorSearchRequest",
    "FoldbackPrecursorSearchResult",
    "foldback_precursor_candidate_id",
    "foldback_precursor_candidate_order_key",
]
