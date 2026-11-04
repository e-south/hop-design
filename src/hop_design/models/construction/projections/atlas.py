"""Recorded route composition with occurrence, ancestry and binding identities separate."""

from itertools import pairwise
from typing import Literal

from pydantic import Field, model_validator

from hop_design.models.base import HopModel
from hop_design.models.construction.complete.material import ExactConstructionMaterial, MaterialUse
from hop_design.models.construction.variants.inspection import MolecularAddress
from hop_design.models.molecular_state import PrimerBinding

from .inspection import MolecularStateInspection
from .inspection_transition import InspectionTransition
from .overhead.complete import ConstructionCost
from .sequence_difference import SequenceRegionDifference


class AtlasMaterialInput(HopModel):
    authority_id: str
    pre_state_id: str
    post_state_id: str
    material: ExactConstructionMaterial
    material_use: MaterialUse
    binding: PrimerBinding | None = None
    binding_state_id: str | None = None
    binding_context: Literal["recorded_state", "derived_template", "not_applicable"]
    annealing_length_nt: int | None = Field(default=None, ge=1)
    # Ordered locations beside which an input is introduced; not binding contacts.
    introduction_reference: tuple[MolecularAddress, ...] = ()


class AtlasTransition(HopModel):
    authority_id: str
    kind: str
    correspondence: InspectionTransition


class MolecularScenes(HopModel):
    """Exact state inspections without claiming a connected processing trajectory."""

    materialized_realization_id: str
    states: tuple[MolecularStateInspection, ...] = Field(min_length=2)
    inputs: tuple[AtlasMaterialInput, ...] = ()
    construction_cost: ConstructionCost | None = Field(
        default=None, exclude_if=lambda value: value is None
    )

    @model_validator(mode="after")
    def validate_scenes(self) -> "MolecularScenes":
        ids = tuple(s.state.state_id for s in self.states)
        if len(ids) != len(set(ids)):
            raise ValueError("Atlas states must have unique identities.")
        if any(
            s.materialized_realization_id != self.materialized_realization_id for s in self.states
        ):
            raise ValueError("Atlas cannot mix preparations.")
        bases = {b.address: b.base for s in self.states for b in s.bases}
        for item in self.inputs:
            if item.material.material_id != item.material_use.material_id:
                raise ValueError("Atlas input use must match its exact material.")
            reference = item.introduction_reference
            if any(a not in bases or a.state_id != item.pre_state_id for a in reference):
                raise ValueError("Input placement must reference its recorded introduction state.")
            if reference:
                if item.binding is None or len(reference) != item.annealing_length_nt:
                    raise ValueError(
                        "Incoming primer placement must retain its complete annealing span."
                    )
                # The future complement is not present yet. These addresses
                # locate the corresponding original sequence, not an annealed primer.
                expected = item.material.sequence_5prime[-len(reference) :]
                if "".join(bases[a] for a in reference) != expected:
                    raise ValueError("Incoming primer reference disagrees with its sequence.")
        return self


class MolecularAtlas(MolecularScenes):
    transitions: tuple[AtlasTransition, ...] = Field(min_length=1)
    inputs: tuple[AtlasMaterialInput, ...]

    @model_validator(mode="after")
    def validate_composition(self) -> "MolecularAtlas":
        ids = tuple(s.state.state_id for s in self.states)
        edges = tuple(
            (t.correspondence.reference_state_id, t.correspondence.target_state_id)
            for t in self.transitions
        )
        if edges != tuple(pairwise(ids)):
            raise ValueError("Atlas transitions must preserve consecutive recorded states.")
        addresses = {b.address for s in self.states for b in s.bases}
        for transition in self.transitions:
            c = transition.correspondence
            if any(a not in addresses for a in (*c.unmapped_reference, *c.unmapped_target)) or any(
                link.reference not in addresses or link.target not in addresses for link in c.links
            ):
                raise ValueError("Atlas correspondence must name displayed occurrences.")
        for item in self.inputs:
            if item.pre_state_id not in ids or item.post_state_id not in ids:
                raise ValueError("Atlas inputs must enter at recorded transitions.")
            if item.binding_context == "recorded_state" and item.binding_state_id not in ids:
                raise ValueError("Primer binding must identify its recorded template state.")
        return self


class AtlasBaseSubstitution(HopModel):
    address: MolecularAddress
    reference_base: str
    observed_base: str


class AtlasMaterialDifference(HopModel):
    role: str
    reference: ExactConstructionMaterial | None
    observed: ExactConstructionMaterial | None


class AtlasComparison(HopModel):
    reference: str
    option_label: str
    transitions: tuple[InspectionTransition, ...]
    substitutions: tuple[AtlasBaseSubstitution, ...]
    notices: tuple[str, ...]
    material_roles: tuple[str, ...]
    reference_loop: str
    observed_loop: str
    regions: tuple[SequenceRegionDifference, ...] = ()
    endpoint_regions: tuple[SequenceRegionDifference, ...] = ()
    materials: tuple[AtlasMaterialDifference, ...] = ()
    additions: tuple[MolecularAddress, ...] = ()
    unresolved_positions: tuple[MolecularAddress, ...] = ()
