"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/basal_release.py

Defines future Type IIS obligations for one local basal construction boundary.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator, model_validator

from hop_design.models.base import HopModel
from hop_design.models.enzymes import CharacterizedEnzyme, EnzymeClass
from hop_design.models.molecular_state import StrandEnd
from hop_design.models.physical import SiteOrientation
from hop_design.models.sequence import normalize_dna_sequence, reverse_complement_iupac
from hop_design.serialization import canonical_json_bytes, sha256_digest


class BasalFutureReleaseRequirement(HopModel):
    """One cohesive-end obligation that becomes physical only after later cleavage."""

    product_end: Literal["left", "right"]
    orientation: SiteOrientation
    cohesive_end_sequence: str
    overhang_end: StrandEnd

    @field_validator("cohesive_end_sequence", mode="before")
    @classmethod
    def normalize_cohesive_end(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("A future cohesive end must be a DNA string.")
        return normalize_dna_sequence(value, allow_degenerate=False)


class BasalFutureReleaseAction(HopModel):
    """One enzyme action positioned relative to a future endpoint boundary."""

    action_id: str = Field(pattern=r"^hop:basal-future-release-action/[0-9a-f]{64}@1$")
    enzyme_id: str
    enzyme_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    requirement: BasalFutureReleaseRequirement
    recognition_pattern_5prime: str
    recognition_start_from_release_boundary: int
    reference_cut_from_release_boundary: int
    complement_cut_from_release_boundary: int

    @field_validator("recognition_pattern_5prime", mode="before")
    @classmethod
    def normalize_recognition_pattern(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("A future recognition pattern must be a DNA string.")
        return normalize_dna_sequence(value, allow_degenerate=True)

    @classmethod
    def create(cls, **content: object) -> BasalFutureReleaseAction:
        """Create a content-addressed future-action obligation."""
        draft = cls.model_construct(action_id="", **content)
        facts = draft.model_dump(mode="json", exclude={"action_id"})
        digest = sha256_digest(canonical_json_bytes(facts)).removeprefix("sha256:")
        return cls.model_validate(
            {
                "action_id": f"hop:basal-future-release-action/{digest}@1",
                **content,
            }
        )

    @model_validator(mode="after")
    def validate_action(self) -> BasalFutureReleaseAction:
        content = self.model_dump(mode="json", exclude={"action_id"})
        digest = sha256_digest(canonical_json_bytes(content)).removeprefix("sha256:")
        if self.action_id != f"hop:basal-future-release-action/{digest}@1":
            raise ValueError("Future release action identity must seal its exact obligation.")
        cuts = (
            self.reference_cut_from_release_boundary,
            self.complement_cut_from_release_boundary,
        )
        if abs(cuts[0] - cuts[1]) != len(self.requirement.cohesive_end_sequence):
            raise ValueError("Future release cuts must produce the required overhang length.")
        if self.requirement.product_end == "left" and min(cuts) != 0:
            raise ValueError("A left future release action must begin at its endpoint boundary.")
        if self.requirement.product_end == "right" and max(cuts) != 0:
            raise ValueError("A right future release action must end at its endpoint boundary.")
        expected_end = StrandEnd.FIVE_PRIME if cuts[0] < cuts[1] else StrandEnd.THREE_PRIME
        if self.requirement.overhang_end is not expected_end:
            raise ValueError("Future release cut polarity must match the required cohesive end.")
        return self

    def assert_definition_replay(self, enzyme: CharacterizedEnzyme) -> None:
        """Replay the relative recognition and cuts against one enzyme definition."""
        if (
            enzyme.enzyme_id != self.enzyme_id
            or enzyme.enzyme_class is not EnzymeClass.DUPLEX_RESTRICTION
            or enzyme.cut_offset_complement_strand is None
        ):
            raise ValueError("Future release action requires its exact duplex enzyme definition.")
        pattern = (
            enzyme.recognition_pattern
            if self.requirement.orientation is SiteOrientation.FORWARD
            else reverse_complement_iupac(enzyme.recognition_pattern)
        )
        if pattern != self.recognition_pattern_5prime:
            raise ValueError("Future release recognition must replay the enzyme orientation.")
        if self.requirement.orientation is SiteOrientation.FORWARD:
            reference_offset = enzyme.cut_offset_reference_strand
            complement_offset = enzyme.cut_offset_complement_strand
        else:
            reference_offset = enzyme.recognition_length - enzyme.cut_offset_complement_strand
            complement_offset = enzyme.recognition_length - enzyme.cut_offset_reference_strand
        if (
            self.recognition_start_from_release_boundary + reference_offset
            != self.reference_cut_from_release_boundary
            or self.recognition_start_from_release_boundary + complement_offset
            != self.complement_cut_from_release_boundary
        ):
            raise ValueError("Future release cuts must replay the enzyme definition.")


__all__ = ["BasalFutureReleaseAction", "BasalFutureReleaseRequirement"]
