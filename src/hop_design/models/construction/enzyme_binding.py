"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/enzyme_binding.py

Defines exact construction-enzyme placements, cut geometry, and cohesive ends.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import Field, model_validator

from hop_design.models.base import HopModel
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.enzymes import CharacterizedEnzyme, EnzymeClass, EnzymeRole
from hop_design.models.junction import Strand
from hop_design.models.molecular_state import CohesiveEnd, StrandEnd
from hop_design.models.physical import SiteOrientation
from hop_design.models.sequence import iupac_bases, reverse_complement_iupac
from hop_design.serialization import canonical_json_bytes, sha256_digest


class ConstructionEnzymeBinding(HopModel):
    """One exact recognition placement and operative cut geometry."""

    binding_id: str = Field(pattern=r"^hop:enzyme-binding/[0-9a-f]{64}@1$")
    enzyme_id: str
    role: EnzymeRole
    strand: Strand | None
    recognition_span: Span
    orientation: SiteOrientation
    reference_cut: Boundary | None
    complement_cut: Boundary | None

    @classmethod
    def create(
        cls,
        *,
        enzyme_id: str,
        role: EnzymeRole,
        strand: Strand | None,
        recognition_span: Span,
        orientation: SiteOrientation,
        reference_cut: Boundary | None,
        complement_cut: Boundary | None,
    ) -> ConstructionEnzymeBinding:
        facts: dict[str, object] = {
            "enzyme_id": enzyme_id,
            "role": role,
            "strand": strand,
            "recognition_span": recognition_span,
            "orientation": orientation,
            "reference_cut": reference_cut,
            "complement_cut": complement_cut,
        }
        content = cls._content(facts)
        digest = sha256_digest(canonical_json_bytes(content)).removeprefix("sha256:")
        return cls.model_validate({"binding_id": f"hop:enzyme-binding/{digest}@1", **facts})

    @staticmethod
    def _content(facts: dict[str, object]) -> dict[str, object]:
        return {
            key: (
                value.model_dump(mode="json")
                if isinstance(value, HopModel)
                else value.value
                if isinstance(value, StrEnum)
                else value
            )
            for key, value in facts.items()
        }

    @model_validator(mode="after")
    def validate_binding(self) -> ConstructionEnzymeBinding:
        facts = self.model_dump(mode="json", exclude={"binding_id"})
        digest = sha256_digest(canonical_json_bytes(facts)).removeprefix("sha256:")
        if self.binding_id != f"hop:enzyme-binding/{digest}@1":
            raise ValueError("Enzyme-binding identity must seal its exact placement and cuts.")
        operative = self.reference_cut if self.strand is Strand.TOP else self.complement_cut
        if self.role is EnzymeRole.BASAL_NICK and operative is None:
            raise ValueError("Basal nick binding must cut its controlled strand.")
        if self.role is EnzymeRole.END_GENERATION and (
            self.reference_cut is None or self.complement_cut is None
        ):
            raise ValueError("End generation requires two exact strand cuts.")
        return self

    def assert_definition_replay(
        self,
        *,
        enzyme: CharacterizedEnzyme,
        sequence: str,
    ) -> None:
        """Replay one embedded definition against its exact placement and cuts."""
        if self.enzyme_id != enzyme.enzyme_id:
            raise ValueError("Enzyme binding must reference its embedded enzyme definition.")
        if self.role is EnzymeRole.BASAL_NICK:
            if enzyme.enzyme_class is not EnzymeClass.NICKASE:
                raise ValueError("Basal nick bindings require a characterized nickase.")
        elif enzyme.enzyme_class is not EnzymeClass.DUPLEX_RESTRICTION:
            raise ValueError("End-generation bindings require a duplex restriction enzyme.")
        pattern = (
            enzyme.recognition_pattern
            if self.orientation is SiteOrientation.FORWARD
            else reverse_complement_iupac(enzyme.recognition_pattern)
        )
        observed = sequence[self.recognition_span.start.offset : self.recognition_span.end.offset]
        if len(observed) != len(pattern) or any(
            base not in iupac_bases(symbol) for base, symbol in zip(observed, pattern, strict=True)
        ):
            raise ValueError("Enzyme-binding recognition must replay its enzyme definition.")
        start = self.recognition_span.start.offset
        if self.orientation is SiteOrientation.FORWARD:
            reference_offset = enzyme.cut_offset_reference_strand
            complement_offset = enzyme.cut_offset_complement_strand
        elif enzyme.enzyme_class is EnzymeClass.NICKASE:
            reference_offset = None
            complement_offset = enzyme.recognition_length - enzyme.cut_offset_reference_strand
        else:
            if enzyme.cut_offset_complement_strand is None:
                raise ValueError("End-generation definitions require two cut offsets.")
            reference_offset = enzyme.recognition_length - enzyme.cut_offset_complement_strand
            complement_offset = enzyme.recognition_length - enzyme.cut_offset_reference_strand
        expected_reference = (
            Boundary(offset=start + reference_offset) if reference_offset is not None else None
        )
        expected_complement = (
            Boundary(offset=start + complement_offset) if complement_offset is not None else None
        )
        if self.reference_cut != expected_reference or self.complement_cut != expected_complement:
            raise ValueError("Enzyme-binding cuts must replay its enzyme definition.")


def derive_cohesive_end(
    *,
    side: Literal["left", "right"],
    top_sequence: str,
    binding: ConstructionEnzymeBinding,
    primary_strand_id: str,
    complementary_strand_id: str,
) -> CohesiveEnd:
    """Derive one exact cohesive end from an exact binding and cut geometry."""
    if binding.reference_cut is None or binding.complement_cut is None:
        raise ValueError("cohesive-end-unavailable")
    primary = binding.reference_cut.offset
    complement = binding.complement_cut.offset
    if primary == complement:
        raise ValueError("cohesive-end-unavailable")
    span = Span(
        start=Boundary(offset=min(primary, complement)),
        end=Boundary(offset=max(primary, complement)),
    )
    aligned = top_sequence[span.start.offset : span.end.offset]
    if primary < complement:
        protruding = primary_strand_id if side == "left" else complementary_strand_id
        sequence = aligned if side == "left" else reverse_complement_iupac(aligned)
        polarity = StrandEnd.FIVE_PRIME
    else:
        protruding = complementary_strand_id if side == "left" else primary_strand_id
        sequence = reverse_complement_iupac(aligned) if side == "left" else aligned
        polarity = StrandEnd.THREE_PRIME
    return CohesiveEnd(
        product_end=side,
        protruding_strand_id=protruding,
        overhang_end=polarity,
        sequence=sequence,
        source_span=span,
        primary_cut=binding.reference_cut,
        complementary_cut=binding.complement_cut,
    )


__all__ = ["ConstructionEnzymeBinding", "derive_cohesive_end"]
