"""Strict method identities, outcomes, and route-material contracts."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import Field, field_validator, model_validator

from hop_design.models.base import HopModel
from hop_design.models.coordinates import Span
from hop_design.models.diagnostics import Diagnostic, Severity
from hop_design.models.sequence import (
    EXACT_DNA_ALPHABET,
    SequenceValidationError,
    normalize_dna_sequence,
    reverse_complement_iupac,
)


class OligoModification(StrEnum):
    FIVE_PRIME_PHOSPHATE = "five_prime_phosphate"


class LigationEndPreparation(StrEnum):
    PRE_PHOSPHORYLATED_OLIGOS = "pre_phosphorylated_oligos"
    KINASE_STEP = "kinase_step"


class ProcessMaterialRole(StrEnum):
    SOURCE_OLIGO = "source_oligo"
    SOURCE_PCR_FORWARD_PRIMER = "source_pcr_forward_primer"
    SOURCE_PCR_REVERSE_PRIMER = "source_pcr_reverse_primer"
    LIGATION_ADAPTER = "ligation_adapter"
    HAIRPIN_PCR_FORWARD_PRIMER = "hairpin_pcr_forward_primer"
    HAIRPIN_PCR_REVERSE_PRIMER = "hairpin_pcr_reverse_primer"


class BindingOrientation(StrEnum):
    SAME_5TO3 = "same_5to3"
    REVERSE_COMPLEMENT_5TO3 = "reverse_complement_5to3"


class ProcessOligo(HopModel):
    """One vendor-neutral sequence material and its terminal chemistry."""

    material_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
    sequence: str
    modifications: tuple[OligoModification, ...] = ()

    @field_validator("sequence", mode="before")
    @classmethod
    def normalize_sequence(cls, value: object) -> str:
        if not isinstance(value, str):
            raise SequenceValidationError("DNA sequence must be a string.")
        return normalize_dna_sequence(value, allow_degenerate=True)

    @model_validator(mode="after")
    def validate_modifications(self) -> ProcessOligo:
        if len(self.modifications) != len(set(self.modifications)):
            raise ValueError("Oligo modifications must not contain duplicates.")
        return self


class MethodKind(StrEnum):
    """Transformation-defined method families known to HOP."""

    LINEAR_SOURCE_MULTINICK_SIZE_SELECTION_HAIRPIN_PCR = (
        "linear-source-multinick-size-selection-hairpin-pcr@1"
    )
    CIRCULAR_PRECURSOR_EXONUCLEASE_SELECTION_MULTIDIGEST_HAIRPIN_PCR = (
        "circular-precursor-exonuclease-selection-multidigest-hairpin-pcr@1"
    )


class MethodImplementationStatus(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class MethodInputExactness(StrEnum):
    """Sequence exactness accepted by a named method's public request."""

    EXACT_ONLY = "exact_only"
    NOT_DEFINED = "not_defined"


class MethodCapability(HopModel):
    """Version-local method availability without request construction."""

    method_kind: MethodKind
    implementation_status: MethodImplementationStatus
    input_exactness: MethodInputExactness

    @model_validator(mode="after")
    def validate_availability(self) -> MethodCapability:
        if (
            self.implementation_status is MethodImplementationStatus.AVAILABLE
            and self.input_exactness is MethodInputExactness.NOT_DEFINED
        ):
            raise ValueError("An available method must define input exactness.")
        if (
            self.implementation_status is MethodImplementationStatus.UNAVAILABLE
            and self.input_exactness is not MethodInputExactness.NOT_DEFINED
        ):
            raise ValueError("An unavailable method cannot define input exactness.")
        return self


class MethodResolutionStatus(StrEnum):
    NOT_EVALUATED = "not_evaluated"
    COMPLETE = "complete"
    INFEASIBLE = "infeasible"
    TRUNCATED = "truncated"


class MethodOutcome(HopModel):
    """Independent implementation-availability and request-resolution facets."""

    implementation_status: MethodImplementationStatus
    resolution_status: MethodResolutionStatus
    diagnostics: tuple[Diagnostic, ...] = ()

    @model_validator(mode="after")
    def validate_facets(self) -> MethodOutcome:
        if (
            self.implementation_status is MethodImplementationStatus.UNAVAILABLE
            and self.resolution_status is not MethodResolutionStatus.NOT_EVALUATED
        ):
            raise ValueError("An unavailable method cannot have a resolution.")
        has_errors = any(item.severity is Severity.ERROR for item in self.diagnostics)
        if self.resolution_status is MethodResolutionStatus.COMPLETE and has_errors:
            raise ValueError("A complete method resolution cannot contain error diagnostics.")
        if self.resolution_status is MethodResolutionStatus.INFEASIBLE and not has_errors:
            raise ValueError("An infeasible method resolution requires an error diagnostic.")
        return self


class LinearSourceHairpinPcrMaterialsSpec(HopModel):
    """The six sequence materials consumed by the linear-source method."""

    schema_id: Literal["hop.linear-source-hairpin-pcr-materials/v1"] = Field(
        default="hop.linear-source-hairpin-pcr-materials/v1",
        alias="schema",
    )
    method_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,63}$")
    source_oligo: ProcessOligo
    source_pcr_forward_primer: ProcessOligo
    source_pcr_reverse_primer: ProcessOligo
    ligation_adapter: ProcessOligo
    hairpin_pcr_forward_primer: ProcessOligo
    hairpin_pcr_reverse_primer: ProcessOligo
    ligation_end_preparation: LigationEndPreparation

    @model_validator(mode="after")
    def validate_materials(self) -> LinearSourceHairpinPcrMaterialsSpec:
        materials = self.materials
        material_ids = tuple(material.material_id for material in materials)
        if len(material_ids) != len(set(material_ids)):
            raise ValueError("Hairpin method material ids must be unique.")
        for material in materials[1:]:
            if not set(material.sequence) <= EXACT_DNA_ALPHABET:
                raise ValueError("Primers and the ligation adapter must use exact DNA.")
        if self.ligation_end_preparation is LigationEndPreparation.PRE_PHOSPHORYLATED_OLIGOS:
            required = (
                ("source PCR reverse primer", self.source_pcr_reverse_primer),
                ("ligation adapter", self.ligation_adapter),
            )
            for label, material in required:
                if OligoModification.FIVE_PRIME_PHOSPHATE not in material.modifications:
                    raise ValueError(
                        f"The {label} requires a five-prime phosphate for "
                        "pre_phosphorylated_oligos."
                    )
        return self

    @property
    def materials(self) -> tuple[ProcessOligo, ...]:
        return (
            self.source_oligo,
            self.source_pcr_forward_primer,
            self.source_pcr_reverse_primer,
            self.ligation_adapter,
            self.hairpin_pcr_forward_primer,
            self.hairpin_pcr_reverse_primer,
        )


class ProcessMaterial(HopModel):
    role: ProcessMaterialRole
    material_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
    sequence: str
    modifications: tuple[OligoModification, ...] = ()

    @field_validator("sequence", mode="before")
    @classmethod
    def normalize_sequence(cls, value: object) -> str:
        if not isinstance(value, str):
            raise SequenceValidationError("DNA sequence must be a string.")
        return normalize_dna_sequence(value, allow_degenerate=True)


class OligoBinding(HopModel):
    binding_id: str = Field(min_length=1)
    primer_id: str = Field(min_length=1)
    template_id: str = Field(min_length=1)
    template_span: Span
    orientation: BindingOrientation


class LinearSourceHairpinPcrMaterialsPlan(HopModel):
    """Derived method materials and terminal binding relationships."""

    schema_id: Literal["hop.linear-source-hairpin-pcr-materials-plan/v1"] = Field(
        default="hop.linear-source-hairpin-pcr-materials-plan/v1",
        alias="schema",
    )
    method_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,63}$")
    spec_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    materials: tuple[ProcessMaterial, ...] = Field(min_length=6, max_length=6)
    required_material_ids: tuple[str, ...] = Field(min_length=6, max_length=6)
    bindings: tuple[OligoBinding, ...] = Field(min_length=4, max_length=4)
    ligation_end_preparation: LigationEndPreparation

    @model_validator(mode="after")
    def validate_derivations(self) -> LinearSourceHairpinPcrMaterialsPlan:
        expected_roles = tuple(ProcessMaterialRole)
        if tuple(material.role for material in self.materials) != expected_roles:
            raise ValueError("Method materials must follow the declared role order.")
        material_ids = tuple(material.material_id for material in self.materials)
        if self.required_material_ids != material_ids:
            raise ValueError("Required material ids must match the resolved materials.")
        if len(material_ids) != len(set(material_ids)):
            raise ValueError("Resolved method material ids must be unique.")
        known_ids = set(material_ids)
        if any(
            binding.primer_id not in known_ids or binding.template_id not in known_ids
            for binding in self.bindings
        ):
            raise ValueError("Bindings must reference resolved method materials.")
        by_role = {material.role: material for material in self.materials}
        if self.ligation_end_preparation is LigationEndPreparation.PRE_PHOSPHORYLATED_OLIGOS:
            required_phosphates = (
                by_role[ProcessMaterialRole.SOURCE_PCR_REVERSE_PRIMER],
                by_role[ProcessMaterialRole.LIGATION_ADAPTER],
            )
            if any(
                OligoModification.FIVE_PRIME_PHOSPHATE not in material.modifications
                for material in required_phosphates
            ):
                raise ValueError(
                    "Pre-phosphorylated material plans require phosphates on both "
                    "ligation-end oligos."
                )
        expected = (
            (
                "source-pcr-forward",
                ProcessMaterialRole.SOURCE_PCR_FORWARD_PRIMER,
                ProcessMaterialRole.SOURCE_OLIGO,
                BindingOrientation.SAME_5TO3,
                "prefix",
            ),
            (
                "source-pcr-reverse",
                ProcessMaterialRole.SOURCE_PCR_REVERSE_PRIMER,
                ProcessMaterialRole.SOURCE_OLIGO,
                BindingOrientation.REVERSE_COMPLEMENT_5TO3,
                "suffix",
            ),
            (
                "hairpin-pcr-forward",
                ProcessMaterialRole.HAIRPIN_PCR_FORWARD_PRIMER,
                ProcessMaterialRole.SOURCE_OLIGO,
                BindingOrientation.SAME_5TO3,
                "prefix",
            ),
            (
                "hairpin-pcr-reverse",
                ProcessMaterialRole.HAIRPIN_PCR_REVERSE_PRIMER,
                ProcessMaterialRole.LIGATION_ADAPTER,
                BindingOrientation.REVERSE_COMPLEMENT_5TO3,
                "suffix",
            ),
        )
        for binding, (
            binding_id,
            primer_role,
            template_role,
            orientation,
            terminal,
        ) in zip(self.bindings, expected, strict=True):
            primer = by_role[primer_role]
            template = by_role[template_role]
            binding_sequence = (
                primer.sequence
                if orientation is BindingOrientation.SAME_5TO3
                else reverse_complement_iupac(primer.sequence)
            )
            start = 0 if terminal == "prefix" else len(template.sequence) - len(binding_sequence)
            if (
                binding.binding_id != binding_id
                or binding.primer_id != primer.material_id
                or binding.template_id != template.material_id
                or binding.orientation is not orientation
                or binding.template_span.start.offset != start
                or binding.template_span.end.offset != start + len(binding_sequence)
                or template.sequence[start : start + len(binding_sequence)] != binding_sequence
            ):
                raise ValueError(
                    "Method-material binding derivations must match the resolved sequences."
                )
        return self


__all__ = [
    "BindingOrientation",
    "LigationEndPreparation",
    "LinearSourceHairpinPcrMaterialsPlan",
    "LinearSourceHairpinPcrMaterialsSpec",
    "MethodCapability",
    "MethodImplementationStatus",
    "MethodInputExactness",
    "MethodKind",
    "MethodOutcome",
    "MethodResolutionStatus",
    "OligoBinding",
    "OligoModification",
    "ProcessMaterial",
    "ProcessMaterialRole",
    "ProcessOligo",
]
