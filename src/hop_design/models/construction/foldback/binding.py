"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/foldback/binding.py

Defines exact foldback construction evidence.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field, TypeAdapter, model_validator

from hop_design.models.base import HopModel
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.enzymes import EnzymeClass, EnzymeRole
from hop_design.models.molecular_state import (
    EndChemistry,
)
from hop_design.models.physical import SiteOrientation, Strand
from hop_design.models.references import ReferenceId
from hop_design.serialization import canonical_json_bytes, sha256_digest

_CONTENT_ADAPTER: TypeAdapter[dict[str, object]] = TypeAdapter(dict[str, object])


class FoldbackCleavageProgramKind(StrEnum):
    """Concrete local programs that create the two controlled foldback termini."""

    SINGLE_CLEAVAGE = "single_cleavage"
    SEQUENTIAL_TERMINUS_PLUS_NICK = "sequential_terminus_plus_nick"


class FoldbackTerminusKind(StrEnum):
    """Physical source of the foldback-side five-prime terminus."""

    SOURCE_TERMINUS = "source_terminus"
    ENZYME_CLEAVAGE = "enzyme_cleavage"


class FoldbackMaterialRequirement(StrEnum):
    """Route material property that local discovery cannot itself satisfy."""

    SOURCE_BOTTOM_5PRIME_PHOSPHATE = "source_bottom_5prime_phosphate"


class FoldbackEnzymeBinding(HopModel):
    """One exact recognition span and operative local cut."""

    binding_id: str = Field(pattern=r"^hop:enzyme-binding/[0-9a-f]{64}@1$")
    enzyme_id: ReferenceId
    role: EnzymeRole
    strand: Strand
    recognition_span: Span
    orientation: SiteOrientation
    reference_cut: Boundary | None
    complement_cut: Boundary | None

    @staticmethod
    def _identity(
        *,
        enzyme_id: str,
        role: EnzymeRole,
        strand: Strand,
        recognition_span: Span,
        orientation: SiteOrientation,
        reference_cut: Boundary | None,
        complement_cut: Boundary | None,
    ) -> str:
        content = {
            "enzyme_id": enzyme_id,
            "role": role,
            "strand": strand,
            "recognition_span": recognition_span.model_dump(mode="json"),
            "orientation": orientation,
            "reference_cut": (
                reference_cut.model_dump(mode="json") if reference_cut is not None else None
            ),
            "complement_cut": (
                complement_cut.model_dump(mode="json") if complement_cut is not None else None
            ),
        }
        digest = sha256_digest(canonical_json_bytes(content)).removeprefix("sha256:")
        return f"hop:enzyme-binding/{digest}@1"

    @classmethod
    def create(
        cls,
        *,
        enzyme_id: str,
        role: EnzymeRole,
        strand: Strand,
        recognition_span: Span,
        orientation: SiteOrientation,
        reference_cut: Boundary | None,
        complement_cut: Boundary | None,
    ) -> FoldbackEnzymeBinding:
        """Create content identity over recognition and operative cut facts."""
        return cls(
            binding_id=cls._identity(
                enzyme_id=enzyme_id,
                role=role,
                strand=strand,
                recognition_span=recognition_span,
                orientation=orientation,
                reference_cut=reference_cut,
                complement_cut=complement_cut,
            ),
            enzyme_id=enzyme_id,
            role=role,
            strand=strand,
            recognition_span=recognition_span,
            orientation=orientation,
            reference_cut=reference_cut,
            complement_cut=complement_cut,
        )

    @model_validator(mode="after")
    def validate_identity(self) -> FoldbackEnzymeBinding:
        expected = self._identity(
            enzyme_id=self.enzyme_id,
            role=self.role,
            strand=self.strand,
            recognition_span=self.recognition_span,
            orientation=self.orientation,
            reference_cut=self.reference_cut,
            complement_cut=self.complement_cut,
        )
        if self.binding_id != expected:
            raise ValueError("Foldback enzyme-binding identity must match its exact site and cuts.")
        operative = self.reference_cut if self.strand is Strand.TOP else self.complement_cut
        if operative is None:
            raise ValueError("A foldback enzyme binding must cut its declared controlled strand.")
        return self


class FoldbackBoundaryControl(HopModel):
    """One controlled strand boundary produced by a source end or enzyme."""

    kind: FoldbackTerminusKind
    strand: Strand
    boundary: Boundary
    end_chemistry: EndChemistry
    enzyme_id: ReferenceId | None = None
    enzyme_class: EnzymeClass | None = None
    binding_id: str | None = None

    @model_validator(mode="after")
    def validate_source(self) -> FoldbackBoundaryControl:
        enzyme_fields = (self.enzyme_id, self.enzyme_class, self.binding_id)
        if self.kind is FoldbackTerminusKind.SOURCE_TERMINUS:
            if any(value is not None for value in enzyme_fields):
                raise ValueError("A source terminus must not invent an enzyme binding.")
        elif any(value is None for value in enzyme_fields):
            raise ValueError("An enzyme-defined terminus requires enzyme and binding identity.")
        return self
