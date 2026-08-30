"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/state.py

Defines exact molecular association states in complete construction routes.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator

from hop_design.models.base import HopModel
from hop_design.models.construction.payload import _content_id
from hop_design.models.molecular_state import MolecularStrand, StrandPairObservation

from .associations import ConstructionBondState


class ConstructionStatePhase(StrEnum):
    """Closed physical association phases in a complete construction route."""

    UNSPECIFIED = "unspecified"
    DUPLEX = "duplex"
    CLEAVED_DUPLEX = "cleaved_duplex"
    DENATURED_FRAGMENTS = "denatured_fragments"
    SELECTED_FRAGMENTS = "selected_fragments"
    ANNEALED_COMPLEX = "annealed_complex"
    LIGATED_PRODUCT = "ligated_product"
    FOLDBACK_CLOSED_HAIRPIN = "foldback_closed_hairpin"
    ADAPTER_ANNEALED = "adapter_annealed"
    ADAPTER_LIGATED = "adapter_ligated"
    HAIRPIN_PCR_DUPLEX = "hairpin_pcr_duplex"
    CLONE_READY_DUPLEX = "clone_ready_duplex"


class ConstructionState(HopModel):
    """One complete exact molecular-state snapshot in a construction route."""

    state_id: str = Field(pattern=r"^hop:construction-state/[0-9a-f]{64}@1$")
    molecules: tuple[MolecularStrand, ...] = Field(min_length=1)
    phase: ConstructionStatePhase = ConstructionStatePhase.UNSPECIFIED
    pairings: tuple[StrandPairObservation, ...] = ()
    formed_bonds: tuple[ConstructionBondState, ...] = ()

    @classmethod
    def create(
        cls,
        *,
        molecules: tuple[MolecularStrand, ...],
        phase: ConstructionStatePhase = ConstructionStatePhase.UNSPECIFIED,
        pairings: tuple[StrandPairObservation, ...] = (),
        formed_bonds: tuple[ConstructionBondState, ...] = (),
    ) -> ConstructionState:
        content = {
            "molecules": tuple(item.model_dump(mode="json") for item in molecules),
            "phase": phase,
            "pairings": tuple(item.model_dump(mode="json") for item in pairings),
            "formed_bonds": tuple(item.model_dump(mode="json") for item in formed_bonds),
        }
        return cls(
            state_id=_content_id("construction-state", 1, content),
            molecules=molecules,
            phase=phase,
            pairings=pairings,
            formed_bonds=formed_bonds,
        )

    @model_validator(mode="after")
    def validate_identity(self) -> ConstructionState:
        ids = tuple(item.strand_id for item in self.molecules)
        if len(ids) != len(set(ids)):
            raise ValueError("Construction-state strand ids must be unique.")
        known_ids = set(ids)
        if any(
            pair.left_strand_id not in known_ids or pair.right_strand_id not in known_ids
            for pair in self.pairings
        ):
            raise ValueError("Construction-state pairings must reference present strands.")
        strands = {item.strand_id: item for item in self.molecules}
        pairing_coordinates = tuple(
            coordinate
            for pair in self.pairings
            for coordinate in (
                (pair.left_strand_id, pair.left_index),
                (pair.right_strand_id, pair.right_index),
            )
        )
        if len(pairing_coordinates) != len(set(pairing_coordinates)):
            raise ValueError("Construction-state pairing coordinates must be unique.")
        for pair in self.pairings:
            left = strands[pair.left_strand_id]
            right = strands[pair.right_strand_id]
            if (
                pair.left_index >= len(left.sequence)
                or pair.right_index >= len(right.sequence)
                or left.sequence[pair.left_index] != pair.left_base
                or right.sequence[pair.right_index] != pair.right_base
            ):
                raise ValueError("Construction-state pairings must replay exact strand bases.")
        if any(item.product_strand_id not in known_ids for item in self.formed_bonds):
            raise ValueError("Construction-state bonds must reference their present product.")
        paired_phases = {
            ConstructionStatePhase.DUPLEX,
            ConstructionStatePhase.CLEAVED_DUPLEX,
            ConstructionStatePhase.ANNEALED_COMPLEX,
            ConstructionStatePhase.LIGATED_PRODUCT,
            ConstructionStatePhase.FOLDBACK_CLOSED_HAIRPIN,
            ConstructionStatePhase.ADAPTER_ANNEALED,
            ConstructionStatePhase.ADAPTER_LIGATED,
            ConstructionStatePhase.HAIRPIN_PCR_DUPLEX,
            ConstructionStatePhase.CLONE_READY_DUPLEX,
        }
        unpaired_phases = {
            ConstructionStatePhase.DENATURED_FRAGMENTS,
            ConstructionStatePhase.SELECTED_FRAGMENTS,
        }
        if self.phase in paired_phases and not self.pairings:
            raise ValueError("A paired construction phase requires exact base associations.")
        if self.phase in unpaired_phases and self.pairings:
            raise ValueError("An unpaired construction phase must not retain base associations.")
        bonded_phases = {
            ConstructionStatePhase.LIGATED_PRODUCT,
            ConstructionStatePhase.FOLDBACK_CLOSED_HAIRPIN,
            ConstructionStatePhase.ADAPTER_ANNEALED,
            ConstructionStatePhase.ADAPTER_LIGATED,
        }
        if (self.phase in bonded_phases) != bool(self.formed_bonds):
            raise ValueError("Only covalently closed route phases require formed-bond evidence.")
        expected = _content_id(
            "construction-state",
            1,
            {
                "molecules": tuple(item.model_dump(mode="json") for item in self.molecules),
                "phase": self.phase,
                "pairings": tuple(item.model_dump(mode="json") for item in self.pairings),
                "formed_bonds": tuple(item.model_dump(mode="json") for item in self.formed_bonds),
            },
        )
        if self.state_id != expected:
            raise ValueError("Construction-state identity must seal every exact molecule.")
        return self


__all__ = ["ConstructionState", "ConstructionStatePhase"]
