"""Stage-bound addresses for operation overlays and paired end-to-stem distances."""

from typing import Literal

from pydantic import Field, model_validator

from hop_design.models.base import HopModel
from hop_design.models.construction.variants.inspection import MolecularAddress


class InspectionBoundary(HopModel):
    before: MolecularAddress | None = None
    after: MolecularAddress | None = None

    @model_validator(mode="after")
    def present_neighbor(self) -> "InspectionBoundary":
        if self.before is None and self.after is None:
            raise ValueError("A displayed boundary needs at least one recorded adjacent base.")
        return self


class InspectionCut(HopModel):
    strand: Literal["reference", "complement"]
    precursor_offset: int = Field(ge=0)
    boundary: InspectionBoundary


class InspectionOperation(HopModel):
    operation_id: str
    enzyme_id: str
    enzyme_name: str
    role: str
    precursor_state_id: str
    timing: Literal["planned", "applied"]
    orientation: Literal["forward", "reverse"]
    recognition_start: int = Field(ge=0)
    recognition_end: int = Field(ge=0)
    recognition: tuple[MolecularAddress, ...] = Field(min_length=1)
    cuts: tuple[InspectionCut, ...] = Field(min_length=1, max_length=2)


class InspectionRecognitionSite(HopModel):
    """Mapped footprint presence says nothing about substrate eligibility or activity."""

    site_id: str
    enzyme_id: str
    enzyme_name: str
    role: str
    orientation: Literal["forward", "reverse"]
    precursor_state_id: str
    presence: Literal["present", "partial", "not_yet_present", "removed", "unresolved"]
    reference_base_count: int = Field(gt=0)
    mapped_reference_bases: int = Field(ge=0)
    orientation_path: tuple[MolecularAddress, ...] = ()
    recognition: tuple[MolecularAddress, ...]
    substrate_eligibility: Literal["unassessed"] = "unassessed"

    @model_validator(mode="after")
    def coherent_presence(self) -> "InspectionRecognitionSite":
        if self.mapped_reference_bases > self.reference_base_count:
            raise ValueError("Mapped recognition count exceeds the bound reference.")
        if bool(self.recognition) != bool(self.mapped_reference_bases):
            raise ValueError("Recognition presence must agree with mapped addresses.")
        if self.presence == "present" and self.mapped_reference_bases != self.reference_base_count:
            raise ValueError("Present recognition footprint requires every bound base.")
        if (
            self.presence == "partial"
            and not 0 < self.mapped_reference_bases < self.reference_base_count
        ):
            raise ValueError("Partial recognition footprint requires a strict subset.")
        if self.presence in ("removed", "not_yet_present") and self.recognition:
            raise ValueError("Absent recognition footprint cannot contain present addresses.")
        if any(address not in self.recognition for address in self.orientation_path):
            raise ValueError("Orientation anchors must belong to the mapped footprint.")
        return self


class InspectionInterface(HopModel):
    side: Literal["left", "right"]
    sequence: str
    polarity: Literal["five_prime", "three_prime"]
    distance_bp: int = Field(ge=0)
    paired_start: InspectionBoundary
    paired_end: InspectionBoundary
    overhang: tuple[MolecularAddress, ...] = Field(min_length=1)
