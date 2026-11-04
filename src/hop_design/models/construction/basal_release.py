"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/basal_release.py

Defines future Type IIS obligations for one local basal construction boundary.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from collections.abc import Iterator
from itertools import product
from math import prod
from typing import Any, Literal, cast

from pydantic import Field, field_validator, model_validator

from hop_design.models.base import HopModel
from hop_design.models.enzymes import CharacterizedEnzyme, EnzymeClass
from hop_design.models.molecular_state import StrandEnd
from hop_design.models.physical import SiteOrientation
from hop_design.models.sequence import iupac_bases, normalize_dna_sequence, reverse_complement_iupac
from hop_design.serialization import canonical_json_bytes, sha256_digest


class BasalFutureReleaseRequirement(HopModel):
    """One cohesive-end obligation that becomes physical only after later cleavage."""

    product_end: Literal["left", "right"]
    orientation: SiteOrientation
    cohesive_end_sequence: str
    overhang_end: StrandEnd
    payload_end_offset_bp: int = Field(ge=0)
    recognition_material: Literal["source_duplex", "endpoint_material"] = "source_duplex"

    @field_validator("cohesive_end_sequence", mode="before")
    @classmethod
    def normalize_cohesive_end(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("A future cohesive end must be a DNA string.")
        return normalize_dna_sequence(value, allow_degenerate=True)

    @property
    def cardinality(self) -> int:
        """Count allowed exact ends without allocating their sequences."""
        return prod(len(iupac_bases(symbol)) for symbol in self.cohesive_end_sequence)

    def exact_requirements(self) -> Iterator[BasalFutureReleaseRequirement]:
        """Yield exact end obligations in 5-prime to 3-prime A/C/G/T order."""
        domains = tuple(tuple(sorted(iupac_bases(symbol))) for symbol in self.cohesive_end_sequence)
        for bases in product(*domains):
            yield self.model_copy(update={"cohesive_end_sequence": "".join(bases)})

    def permits(self, exact: BasalFutureReleaseRequirement) -> bool:
        """Check one exact end against its sequence domain and fixed obligations."""
        return (
            self.product_end == exact.product_end
            and self.orientation is exact.orientation
            and self.overhang_end is exact.overhang_end
            and self.payload_end_offset_bp == exact.payload_end_offset_bp
            and self.recognition_material == exact.recognition_material
            and self.permits_sequence(exact.cohesive_end_sequence)
        )

    def permits_sequence(self, exact: str) -> bool:
        """Check exact nucleotide membership without changing end geometry."""
        return len(self.cohesive_end_sequence) == len(exact) and all(
            base in iupac_bases(symbol)
            for base, symbol in zip(exact, self.cohesive_end_sequence, strict=True)
        )

    @property
    def endpoint_reference_sequence(self) -> str:
        """Return the end footprint on the endpoint's reference strand, 5-prime first."""
        requirement = self
        reverse = (
            requirement.overhang_end is StrandEnd.FIVE_PRIME and requirement.product_end == "right"
        ) or (
            requirement.overhang_end is StrandEnd.THREE_PRIME and requirement.product_end == "left"
        )
        return (
            reverse_complement_iupac(requirement.cohesive_end_sequence)
            if reverse
            else requirement.cohesive_end_sequence
        )

    def source_end_placement(
        self, *, payload_boundary: int, nick_offset_nt: int
    ) -> tuple[int, str] | None:
        """Constrain end bases supplied by the payload-forward source strand."""
        offset = self.payload_end_offset_bp
        sequence = self.endpoint_reference_sequence
        if self.product_end == "left":
            return payload_boundary - offset - len(sequence), sequence
        end = min(offset + len(sequence), nick_offset_nt)
        if end <= offset:
            return None
        return payload_boundary - end, reverse_complement_iupac(sequence[: end - offset])

    def source_contact_bases(self, *, nick_offset_nt: int) -> tuple[tuple[int, str], ...]:
        """Map exact source-supplied bases to contacts counted away from ligation."""
        if type(nick_offset_nt) is not int or nick_offset_nt < 0:
            raise ValueError("A nick offset must be a nonnegative integer.")
        if self.cardinality != 1:
            raise ValueError("Source contact projection requires an exact end.")
        boundary = nick_offset_nt + self.payload_end_offset_bp + len(self.cohesive_end_sequence)
        placement = self.source_end_placement(
            payload_boundary=boundary, nick_offset_nt=nick_offset_nt
        )
        if placement is None:
            return ()
        start, sequence = placement
        origin = boundary - nick_offset_nt
        return tuple(
            (position, base)
            for index, base in enumerate(sequence)
            if (position := origin - 1 - (start + index)) >= 0
        )


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

    @property
    def endpoint_reference_sequence(self) -> str:
        """Delegate strand coordinates to the shared end requirement."""
        return self.requirement.endpoint_reference_sequence

    def source_end_placement(
        self, *, payload_boundary: int, nick_offset_nt: int
    ) -> tuple[int, str] | None:
        """Delegate source coordinates to the shared end requirement."""
        return self.requirement.source_end_placement(
            payload_boundary=payload_boundary, nick_offset_nt=nick_offset_nt
        )

    def adapter_end_bases(self, *, nick_offset_nt: int) -> tuple[tuple[int, str], ...]:
        """Map adapter-supplied endpoint bases to positions from the ligation bond."""
        if self.requirement.product_end == "left":
            return ()
        start = self.requirement.payload_end_offset_bp - nick_offset_nt
        return tuple(
            (start + index, base)
            for index, base in enumerate(self.endpoint_reference_sequence)
            if start + index >= 0
        )

    def paired_end_positions(
        self, *, nick_offset_nt: int, pairing_length_nt: int
    ) -> tuple[int, ...]:
        """Locate source-adapter pairs whose coordinates intersect the future end."""
        start = self.requirement.payload_end_offset_bp - nick_offset_nt
        end = start + len(self.requirement.cohesive_end_sequence)
        return tuple(position for position in range(pairing_length_nt) if start <= position < end)

    def source_cut_boundaries(self, *, payload_boundary: int) -> tuple[int, int]:
        """Project future reference/complement cuts into the payload-forward source frame."""
        boundary = (
            payload_boundary
            - self.requirement.payload_end_offset_bp
            - len(self.requirement.cohesive_end_sequence)
        )
        if self.requirement.product_end == "right":
            return (
                boundary - self.complement_cut_from_release_boundary,
                boundary - self.reference_cut_from_release_boundary,
            )
        return (
            boundary + self.reference_cut_from_release_boundary,
            boundary + self.complement_cut_from_release_boundary,
        )

    def source_recognition_placement(self, *, payload_boundary: int) -> tuple[int, str]:
        """Map the future recognition site onto the payload-bearing source strand.

        The source-forward end footprint precedes the payload by the declared
        paired gap. Copying presents the interval at the left endpoint directly,
        or reverse-complemented at the right endpoint.
        """
        if self.requirement.recognition_material != "source_duplex":
            raise ValueError("Endpoint-supplied recognition has no source placement.")
        boundary = (
            payload_boundary
            - self.requirement.payload_end_offset_bp
            - len(self.requirement.cohesive_end_sequence)
        )
        start = self.recognition_start_from_release_boundary
        pattern = self.recognition_pattern_5prime
        if self.requirement.product_end == "right":
            return boundary - start - len(pattern), reverse_complement_iupac(pattern)
        return boundary + start, pattern

    def assert_source_recognition_replay(self, *, sequence: str, payload_boundary: int) -> None:
        """Require the source-encoded recognition pattern at its mapped coordinates."""
        start, pattern = self.source_recognition_placement(payload_boundary=payload_boundary)
        if (
            start < 0
            or start + len(pattern) > len(sequence)
            or any(
                base not in iupac_bases(symbol)
                for base, symbol in zip(
                    sequence[start : start + len(pattern)], pattern, strict=True
                )
            )
        ):
            raise ValueError("Source duplex must encode the future release recognition site.")

    @field_validator("recognition_pattern_5prime", mode="before")
    @classmethod
    def normalize_recognition_pattern(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("A future recognition pattern must be a DNA string.")
        return normalize_dna_sequence(value, allow_degenerate=True)

    @classmethod
    def create(cls, **content: object) -> BasalFutureReleaseAction:
        """Create a content-addressed future-action obligation."""
        draft = cls.model_construct(action_id="", **cast(Any, content))
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
        if self.requirement.cardinality != 1:
            raise ValueError("A future release action requires an exact cohesive end.")
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
