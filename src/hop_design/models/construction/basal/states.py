"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/basal/states.py

Defines exact basal construction evidence.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from hop_design.models.base import HopModel
from hop_design.models.construction import (
    ConstructionEndpoint,
)
from hop_design.models.coordinates import Span
from hop_design.models.molecular_state import (
    CohesiveEnd,
    CovalentBond,
    EndChemistry,
    MolecularStrand,
    StrandPairObservation,
)
from hop_design.models.sequence import (
    normalize_dna_sequence,
    reverse_complement_iupac,
)

from .pairing import BasalPairingProfile


class BasalMaterialRole(StrEnum):
    """Route-local accounting class for exact construction material."""

    RETAINED = "retained"
    TRANSIENT = "transient"
    AUXILIARY = "auxiliary"


class BasalMaterialRecord(HopModel):
    """One exact route material with an explicit accounting role."""

    material_id: str = Field(pattern=r"^[a-z][a-z0-9_-]*$")
    role: BasalMaterialRole
    sequence_5prime: str

    @field_validator("sequence_5prime", mode="before")
    @classmethod
    def normalize_sequence(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("Basal material sequence must be a DNA string.")
        return normalize_dna_sequence(value, allow_degenerate=False)


class BasalMaterialAccounting(HopModel):
    """Exact nucleotide totals by retained, transient, and auxiliary roles."""

    retained_nt: int = Field(ge=0)
    transient_nt: int = Field(ge=0)
    auxiliary_nt: int = Field(ge=0)


class BasalAdapterAnnealedComplex(HopModel):
    """Exact two-strand source-adapter pairing before ligation."""

    source_strand: MolecularStrand
    adapter_strand: MolecularStrand
    pairs: tuple[StrandPairObservation, ...] = Field(min_length=1)

    @property
    def strand_ids(self) -> tuple[str, str]:
        """Return the two physically present strand identities."""
        return (self.source_strand.strand_id, self.adapter_strand.strand_id)

    @model_validator(mode="after")
    def validate_pairs(self) -> BasalAdapterAnnealedComplex:
        if any(
            pair.left_strand_id != self.source_strand.strand_id
            or pair.right_strand_id != self.adapter_strand.strand_id
            for pair in self.pairs
        ):
            raise ValueError("Basal annealing pairs must reference the two present strands.")
        return self


class BasalLigatedHairpin(HopModel):
    """Exact source-adapter ligation before PCR copying."""

    source_strand: MolecularStrand
    adapter_strand: MolecularStrand
    bond: CovalentBond
    strand: MolecularStrand

    @property
    def source_strand_id(self) -> str:
        """Return the exact source component identity."""
        return self.source_strand.strand_id

    @property
    def adapter_strand_id(self) -> str:
        """Return the exact adapter component identity."""
        return self.adapter_strand.strand_id

    @model_validator(mode="after")
    def validate_ligation(self) -> BasalLigatedHairpin:
        if (
            self.bond.upstream_strand_id != self.source_strand_id
            or self.bond.downstream_strand_id != self.adapter_strand_id
        ):
            raise ValueError("Basal ligation bond must join source to adapter.")
        if self.strand.sequence != self.source_strand.sequence + self.adapter_strand.sequence:
            raise ValueError("Basal ligation must concatenate the exact component strands.")
        expected_lineage = tuple(
            item.model_copy(update={"product_index": index})
            for index, item in enumerate(
                (*self.source_strand.lineage, *self.adapter_strand.lineage)
            )
        )
        if self.strand.lineage != expected_lineage:
            raise ValueError("Basal ligation must preserve source and adapter lineage exactly.")
        return self


class BasalPcrCopyState(HopModel):
    """Exact duplex copy projection without asserting primer materials."""

    top_strand: MolecularStrand
    bottom_strand: MolecularStrand
    primer_bindings: tuple[()] = ()

    @model_validator(mode="after")
    def validate_copy(self) -> BasalPcrCopyState:
        if self.bottom_strand.sequence != reverse_complement_iupac(self.top_strand.sequence):
            raise ValueError("Basal PCR projection must preserve exact duplex complementarity.")
        return self


class BasalRestrictionProduct(HopModel):
    """Exact clone-ready product derived from two characterized bindings."""

    binding_ids: tuple[str, str]
    primary_parent_span: Span
    complementary_parent_span: Span
    primary_strand: MolecularStrand
    complementary_strand: MolecularStrand
    cohesive_ends: tuple[CohesiveEnd, CohesiveEnd]

    @model_validator(mode="after")
    def validate_parent_spans(self) -> BasalRestrictionProduct:
        if self.primary_parent_span.length.value != len(self.primary_strand.sequence):
            raise ValueError("Primary restriction span must equal its exact strand length.")
        if self.complementary_parent_span.length.value != len(self.complementary_strand.sequence):
            raise ValueError("Complementary restriction span must equal its exact strand length.")
        return self

    def assert_parent_replay(self, parent: BasalPcrCopyState) -> None:
        """Replay both product strands against exact PCR-parent coordinates."""
        for product, source, span in (
            (self.primary_strand, parent.top_strand, self.primary_parent_span),
            (
                self.complementary_strand,
                parent.bottom_strand,
                self.complementary_parent_span,
            ),
        ):
            start = span.start.offset
            end = span.end.offset
            expected_lineage = tuple(
                item.model_copy(update={"product_index": index})
                for index, item in enumerate(source.lineage[start:end])
            )
            if (
                start >= end
                or end > len(source.sequence)
                or product.sequence != source.sequence[start:end]
                or product.lineage != expected_lineage
                or product.five_prime_end is not EndChemistry.PHOSPHATE
                or product.three_prime_end is not EndChemistry.HYDROXYL
            ):
                raise ValueError(
                    "Clone restriction product must replay its exact parent coordinates, "
                    "sequence, lineage, and end chemistry."
                )


def assert_material_partition(
    *,
    endpoint: ConstructionEndpoint,
    source_precursor_sequence: str,
    pcr_duplex: BasalPcrCopyState | None,
    restriction_product: BasalRestrictionProduct | None,
    materials: tuple[BasalMaterialRecord, ...],
) -> None:
    """Validate endpoint-relative retained and transient sequence accounting."""
    retained = tuple(
        item.sequence_5prime for item in materials if item.role is BasalMaterialRole.RETAINED
    )
    transient = tuple(
        item.sequence_5prime for item in materials if item.role is BasalMaterialRole.TRANSIENT
    )
    if len(retained) != 1 or len(transient) > 1:
        raise ValueError("Endpoint retained and transient partition must be singular.")
    expected_transient: tuple[str, ...]
    if endpoint is ConstructionEndpoint.SSDNA_HAIRPIN:
        expected_retained = source_precursor_sequence
        expected_transient = ()
    elif endpoint is ConstructionEndpoint.HAIRPIN_PCR_DUPLEX:
        if pcr_duplex is None:
            raise ValueError("PCR material accounting requires its exact duplex state.")
        expected_retained = pcr_duplex.top_strand.sequence
        expected_transient = ()
    else:
        if pcr_duplex is None or restriction_product is None:
            raise ValueError("Clone material accounting requires exact digest states.")
        sequence = pcr_duplex.top_strand.sequence
        start = restriction_product.primary_parent_span.start.offset
        end = restriction_product.primary_parent_span.end.offset
        expected_retained = sequence[start:end]
        outside = sequence[:start] + sequence[end:]
        expected_transient = (outside,) if outside else ()
    if retained != (expected_retained,) or transient != expected_transient:
        raise ValueError(
            "Endpoint retained and transient partition must replay nonoverlapping sequence."
        )


class BasalEndpointProjection(HopModel):
    """Exact molecular obligations established for one endpoint."""

    endpoint: ConstructionEndpoint
    pairing_profile: BasalPairingProfile | None = None
    pcr_reference_sequence: str | None = None
    pcr_complement_sequence: str | None = None
    cohesive_ends: tuple[CohesiveEnd, ...] = ()
    asymmetric_end_encoding: bool = False

    @field_validator("pcr_reference_sequence", "pcr_complement_sequence", mode="before")
    @classmethod
    def normalize_optional_sequence(cls, value: object) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("Basal endpoint sequences must be DNA strings.")
        return normalize_dna_sequence(value, allow_degenerate=False)

    @model_validator(mode="after")
    def validate_endpoint(self) -> BasalEndpointProjection:
        if self.endpoint is ConstructionEndpoint.SSDNA_HAIRPIN:
            if self.pairing_profile is not None or self.pcr_reference_sequence is not None:
                raise ValueError("A direct endpoint must not contain adapter or PCR evidence.")
        else:
            if self.pairing_profile is None or self.pcr_reference_sequence is None:
                raise ValueError("PCR-bearing endpoints require exact pairing and copied strands.")
            if (
                reverse_complement_iupac(self.pcr_reference_sequence)
                != self.pcr_complement_sequence
            ):
                raise ValueError("The PCR complement must derive from the complete reference.")
        if self.endpoint is ConstructionEndpoint.CLONE_READY_DUPLEX:
            if tuple(end.product_end for end in self.cohesive_ends) != ("left", "right"):
                raise ValueError("Clone-ready endpoints require left and right cohesive ends.")
        elif self.cohesive_ends:
            raise ValueError("Only clone-ready endpoints may contain cohesive ends.")
        expected = len(self.cohesive_ends) == 2 and (
            self.cohesive_ends[0].sequence,
            self.cohesive_ends[0].overhang_end,
        ) != (
            self.cohesive_ends[1].sequence,
            self.cohesive_ends[1].overhang_end,
        )
        if self.asymmetric_end_encoding is not expected:
            raise ValueError("Asymmetric-end status must derive from exact cohesive ends.")
        return self
