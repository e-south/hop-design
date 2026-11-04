"""Exact molecular addresses and display-independent processing-state inspection."""

from typing import Literal

from pydantic import Field, model_validator

from hop_design.models.base import HopModel
from hop_design.models.construction.complete.state import ConstructionState
from hop_design.models.construction.variants.inspection import MolecularAddress
from hop_design.models.construction.variants.query import Neighborhood
from hop_design.models.molecular_state import MaterialBaseLineage

from .inspection_annotations import (
    InspectionBoundary,
    InspectionInterface,
    InspectionOperation,
    InspectionRecognitionSite,
)


class InspectionStateChoice(HopModel):
    state_id: str
    phase: str
    roles: tuple[Literal["source", "hairpin", "endpoint"], ...] = ()


class InspectionBase(HopModel):
    address: MolecularAddress
    strand_index: int = Field(ge=0)
    base: str = Field(pattern="^[ACGT]$")
    region: str | None
    neighborhood: Neighborhood | None
    origin: MaterialBaseLineage
    material_role: str | None
    paired_addresses: tuple[MolecularAddress, ...] = ()
    focus_relation: Literal["same_address", "retained", "copied", "paired"] | None = None


class MolecularStateInspection(HopModel):
    state: ConstructionState
    materialized_realization_id: str
    available_states: tuple[InspectionStateChoice, ...]
    bases: tuple[InspectionBase, ...]
    focus: MolecularAddress | None = None
    focus_status: Literal["not_requested", "mapped", "removed", "not_yet_present", "not_present"]
    layout_frame: ConstructionState | None = None
    operations: tuple[InspectionOperation, ...] = ()
    recognition_sites: tuple[InspectionRecognitionSite, ...] = ()
    interfaces: tuple[InspectionInterface, ...] = ()
    formed_bond_boundaries: tuple[InspectionBoundary, ...] = ()

    @model_validator(mode="after")
    def recorded_annotation_addresses(self) -> "MolecularStateInspection":
        known = {
            (self.state.state_id, strand.strand_id, index)
            for strand in self.state.molecules
            for index in range(len(strand.sequence))
        }
        addresses = [a for operation in self.operations for a in operation.recognition]
        addresses.extend(a for site in self.recognition_sites for a in site.recognition)
        boundaries = [cut.boundary for operation in self.operations for cut in operation.cuts]
        boundaries.extend(self.formed_bond_boundaries)
        for interface in self.interfaces:
            addresses.extend(interface.overhang)
            boundaries.extend((interface.paired_start, interface.paired_end))
        addresses.extend(
            a for boundary in boundaries for a in (boundary.before, boundary.after) if a is not None
        )
        if any((a.state_id, a.strand_id, a.index) not in known for a in addresses):
            raise ValueError("Every annotation must address a base in the displayed state.")
        return self
