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
from typing import Literal

from pydantic import Field, field_validator, model_validator

from hop_design.models.base import HopModel
from hop_design.models.construction import (
    ConstructionEndpoint,
)
from hop_design.models.molecular_state import (
    CovalentBond,
    MolecularStrand,
    StrandPairObservation,
)
from hop_design.models.sequence import (
    normalize_dna_sequence,
    reverse_complement_iupac,
)

from .pairing import BasalPairingState


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


class BasalAdapterLigatedProduct(HopModel):
    """Exact source-adapter ligation product before PCR copying."""

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
    def validate_ligation(self) -> BasalAdapterLigatedProduct:
        if (
            self.bond.upstream_strand_id != self.source_strand_id
            or self.bond.downstream_strand_id != self.adapter_strand_id
        ):
            raise ValueError("Basal ligation bond must join source to adapter.")
        if self.strand.sequence != self.source_strand.sequence + self.adapter_strand.sequence:
            raise ValueError(
                "Basal adapter-ligated product must concatenate the exact component strands."
            )
        expected_lineage = tuple(
            item.model_copy(update={"product_index": index})
            for index, item in enumerate(
                (*self.source_strand.lineage, *self.adapter_strand.lineage)
            )
        )
        if self.strand.lineage != expected_lineage:
            raise ValueError(
                "Basal adapter ligation must preserve source and adapter lineage exactly."
            )
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


def assert_material_partition(
    *,
    pcr_duplex: BasalPcrCopyState,
    materials: tuple[BasalMaterialRecord, ...],
) -> None:
    """Validate retained and transient accounting for the basal PCR intermediate."""
    retained = tuple(
        item.sequence_5prime for item in materials if item.role is BasalMaterialRole.RETAINED
    )
    transient = tuple(
        item.sequence_5prime for item in materials if item.role is BasalMaterialRole.TRANSIENT
    )
    if len(retained) != 1 or len(transient) > 1:
        raise ValueError("Endpoint retained and transient partition must be singular.")
    if retained != (pcr_duplex.top_strand.sequence,) or transient:
        raise ValueError(
            "Endpoint retained and transient partition must replay nonoverlapping sequence."
        )


class BasalEndpointProjection(HopModel):
    """Exact molecular obligations established for the basal PCR intermediate."""

    endpoint: Literal[ConstructionEndpoint.HAIRPIN_PCR_DUPLEX]
    pairing_state: BasalPairingState
    pcr_reference_sequence: str
    pcr_complement_sequence: str

    @field_validator("pcr_reference_sequence", "pcr_complement_sequence", mode="before")
    @classmethod
    def normalize_optional_sequence(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("Basal endpoint sequences must be DNA strings.")
        return normalize_dna_sequence(value, allow_degenerate=False)

    @model_validator(mode="after")
    def validate_endpoint(self) -> BasalEndpointProjection:
        if reverse_complement_iupac(self.pcr_reference_sequence) != self.pcr_complement_sequence:
            raise ValueError("The PCR complement must derive from the complete reference.")
        return self
