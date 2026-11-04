"""Verified drawing correspondence, distinct from material identity and reaction kinetics."""

from typing import Literal

from hop_design.models.base import HopModel
from hop_design.models.construction.variants.inspection import MolecularAddress


class InspectionCorrespondence(HopModel):
    reference: MolecularAddress
    target: MolecularAddress
    relation: Literal["retained", "copied", "comparison"]


class InspectionTransition(HopModel):
    reference_state_id: str
    target_state_id: str
    mode: Literal["processing", "variant"]
    links: tuple[InspectionCorrespondence, ...]
    unmapped_reference: tuple[MolecularAddress, ...]
    unmapped_target: tuple[MolecularAddress, ...]
    notices: tuple[str, ...]
