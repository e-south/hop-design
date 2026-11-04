"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/foldback_space.py

Defines finite foldback sequence populations with exact enzyme-program support.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from hop_design.models.base import HopModel
from hop_design.models.enzymes import EnzymeProvisioningPolicy
from hop_design.models.physical import SiteOrientation, Strand
from hop_design.models.references import ReferenceId
from hop_design.models.sequence import normalize_dna_sequence

from .foldback import FoldbackCleavageProgramKind
from .payload import FinalPayloadReference, RouteFamily, _content_id, validate_linear_source_payload
from .search import FoldbackGeometryDomain
from .sequence_sets import SequenceSet, SequenceSpaceLimits
from .targets import FoldbackTarget


class FoldbackSequenceRequest(HopModel):
    """Exhaustive local admission within one finite foldback geometry domain."""

    schema_id: Literal["hop.foldback-sequence-request/v1"] = Field(
        default="hop.foldback-sequence-request/v1", alias="schema"
    )
    payload: FinalPayloadReference
    route_family: RouteFamily
    geometry_domain: FoldbackGeometryDomain
    enzyme_provisioning: EnzymeProvisioningPolicy
    max_retained_overhead_nt: int = Field(ge=0, le=256)
    limits: SequenceSpaceLimits

    @model_validator(mode="after")
    def validate_route(self) -> FoldbackSequenceRequest:
        validate_linear_source_payload(self.payload)
        return self


class FoldbackProgramSupport(HopModel):
    """Retained words and their joint source-tail completions for one examined program."""

    kind: FoldbackCleavageProgramKind
    nick_enzyme_id: ReferenceId
    nick_orientation: SiteOrientation
    terminus_enzyme_id: ReferenceId | None
    terminus_orientation: SiteOrientation | None
    placement_failure: str | None
    placement_count: int = Field(ge=0)
    sequences: SequenceSet
    source_assignments: SequenceSet

    @model_validator(mode="after")
    def validate_support(self) -> FoldbackProgramSupport:
        sequential = self.kind is FoldbackCleavageProgramKind.SEQUENTIAL_TERMINUS_PLUS_NICK
        if sequential != (self.terminus_enzyme_id is not None) or sequential != (
            self.terminus_orientation is not None
        ):
            raise ValueError("Foldback program kind and terminus definition disagree.")
        if not self.sequences.cardinality <= self.placement_count <= 4**self.sequences.length_nt:
            raise ValueError("Foldback admission must be contained within placement choices.")
        if self.placement_failure is not None and self.placement_count != 0:
            raise ValueError("Excluded foldback placement cannot contain sequence choices.")
        if (
            self.source_assignments.length_nt < self.sequences.length_nt
            or self.source_assignments.cardinality < self.sequences.cardinality
            or bool(self.source_assignments.cardinality) != bool(self.sequences.cardinality)
        ):
            raise ValueError("Foldback precursor completions must support the retained words.")
        return self


def foldback_case_id(payload_sequence: str, target: FoldbackTarget) -> str:
    """Identify a molecular population independently of its search budget and programs."""
    return _content_id(
        "foldback-sequence-case",
        1,
        {
            "payload_sequence": payload_sequence,
            "target": target.model_dump(mode="json"),
        },
    )


class FoldbackSequenceCase(HopModel):
    """One exact payload, geometry, and nick strand before pooling enzyme support."""

    case_id: str = Field(pattern=r"^hop:foldback-sequence-case/[0-9a-f]{64}@1$")
    payload_sequence: str
    target: FoldbackTarget
    candidate_count: int = Field(ge=1)
    programs: tuple[FoldbackProgramSupport, ...] = Field(max_length=100_000)
    sequences: SequenceSet

    @model_validator(mode="after")
    def validate_population(self) -> FoldbackSequenceCase:
        if self.case_id != foldback_case_id(self.payload_sequence, self.target):
            raise ValueError("Foldback case identity disagrees with its molecular population.")
        if (
            normalize_dna_sequence(self.payload_sequence, allow_degenerate=False)
            != self.payload_sequence
        ):
            raise ValueError("Foldback case payload must be canonical exact DNA.")
        if not isinstance(self.target.nick_strand, Strand):
            raise ValueError("Foldback case requires one exact nick strand.")
        length = self.target.annealing_arm_length_bp + self.target.loop_length_nt
        if self.candidate_count != 4**length:
            raise ValueError(
                "Foldback raw population must contain every independent A+C assignment."
            )
        if any(
            item.length_nt != length
            for item in (self.sequences, *(p.sequences for p in self.programs))
        ):
            raise ValueError("Foldback sequence lengths disagree with the geometry.")
        return self


class FoldbackSequenceResult(HopModel):
    """Complete local sequence membership; no full-material or experimental claim."""

    schema_id: Literal["hop.foldback-sequence-result/v2"] = Field(
        default="hop.foldback-sequence-result/v2", alias="schema"
    )
    request: FoldbackSequenceRequest
    hop_version: str
    route_implementation_version: str
    admission_implementation_version: Literal["foldback-sequence-space/2"] = (
        "foldback-sequence-space/2"
    )
    completion: Literal["complete"] = "complete"
    claim_scope: Literal["local_molecular_admission"] = "local_molecular_admission"
    cases: tuple[FoldbackSequenceCase, ...] = Field(max_length=100_000)
    candidate_count: int = Field(ge=0)
    admitted_count: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_totals(self) -> FoldbackSequenceResult:
        if self.candidate_count != sum(case.candidate_count for case in self.cases):
            raise ValueError("Foldback candidate total disagrees with its cases.")
        if self.admitted_count != sum(case.sequences.cardinality for case in self.cases):
            raise ValueError("Foldback admitted total disagrees with its cases.")
        if len({case.case_id for case in self.cases}) != len(self.cases):
            raise ValueError("Foldback population cases must be unique.")
        limits = self.request.limits
        if (
            len(self.cases) > limits.max_cases
            or sum(len(case.programs) for case in self.cases) > limits.max_programs
        ):
            raise ValueError("Foldback result exceeds its case or program budget.")
        if (
            sum(
                len(s.decisions)
                for case in self.cases
                for s in (
                    case.sequences,
                    *(s for p in case.programs for s in (p.sequences, p.source_assignments)),
                )
            )
            > limits.max_result_decisions
        ):
            raise ValueError("Foldback result exceeds its serialized decision budget.")
        return self

    @property
    def result_id(self) -> str:
        """Bind the request, implementation, complete coverage, and exact supported sets."""
        return _content_id("foldback-sequence-result", 1, self)
