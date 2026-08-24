"""Resolve route-required oligos for the linear-source hairpin-PCR method."""

from __future__ import annotations

from hop_design.models.coordinates import Boundary, Span
from hop_design.models.method import (
    BindingOrientation,
    LinearSourceHairpinPcrMaterialsPlan,
    LinearSourceHairpinPcrMaterialsSpec,
    MethodCapability,
    MethodImplementationStatus,
    MethodInputExactness,
    MethodKind,
    OligoBinding,
    ProcessMaterial,
    ProcessMaterialRole,
    ProcessOligo,
)
from hop_design.models.sequence import reverse_complement_iupac
from hop_design.serialization import canonical_json_bytes, sha256_digest


def list_method_capabilities() -> tuple[MethodCapability, ...]:
    """Return the closed, deterministic capability set for this HOP version."""
    capabilities = (
        MethodCapability(
            method_kind=MethodKind.LINEAR_SOURCE_MULTINICK_SIZE_SELECTION_HAIRPIN_PCR,
            implementation_status=MethodImplementationStatus.AVAILABLE,
            input_exactness=MethodInputExactness.EXACT_ONLY,
        ),
        MethodCapability(
            method_kind=(
                MethodKind.CIRCULAR_PRECURSOR_EXONUCLEASE_SELECTION_MULTIDIGEST_HAIRPIN_PCR
            ),
            implementation_status=MethodImplementationStatus.UNAVAILABLE,
            input_exactness=MethodInputExactness.NOT_DEFINED,
        ),
    )
    if tuple(capability.method_kind for capability in capabilities) != tuple(MethodKind):
        raise RuntimeError(
            "Method capability declarations must cover every named method exactly once."
        )
    return capabilities


def _terminal_binding(
    *,
    binding_id: str,
    primer: ProcessOligo,
    template: ProcessOligo,
    orientation: BindingOrientation,
    terminal: str,
    error_message: str,
) -> OligoBinding:
    binding_sequence = (
        primer.sequence
        if orientation is BindingOrientation.SAME_5TO3
        else reverse_complement_iupac(primer.sequence)
    )
    if terminal == "prefix":
        matches = template.sequence.startswith(binding_sequence)
        start = 0
    else:
        matches = template.sequence.endswith(binding_sequence)
        start = len(template.sequence) - len(binding_sequence)
    if not matches:
        raise ValueError(error_message)
    return OligoBinding(
        binding_id=binding_id,
        primer_id=primer.material_id,
        template_id=template.material_id,
        template_span=Span(
            start=Boundary(offset=start),
            end=Boundary(offset=start + len(binding_sequence)),
        ),
        orientation=orientation,
    )


def resolve_linear_source_hairpin_pcr_materials(
    spec: LinearSourceHairpinPcrMaterialsSpec,
) -> LinearSourceHairpinPcrMaterialsPlan:
    """Validate terminal handles and emit a deterministic six-material handoff."""
    bindings = (
        _terminal_binding(
            binding_id="source-pcr-forward",
            primer=spec.source_pcr_forward_primer,
            template=spec.source_oligo,
            orientation=BindingOrientation.SAME_5TO3,
            terminal="prefix",
            error_message="The source PCR forward primer must match the source-oligo prefix.",
        ),
        _terminal_binding(
            binding_id="source-pcr-reverse",
            primer=spec.source_pcr_reverse_primer,
            template=spec.source_oligo,
            orientation=BindingOrientation.REVERSE_COMPLEMENT_5TO3,
            terminal="suffix",
            error_message=(
                "The source PCR reverse primer must reverse-complement the source-oligo suffix."
            ),
        ),
        _terminal_binding(
            binding_id="hairpin-pcr-forward",
            primer=spec.hairpin_pcr_forward_primer,
            template=spec.source_oligo,
            orientation=BindingOrientation.SAME_5TO3,
            terminal="prefix",
            error_message="The hairpin PCR forward primer must match the source-oligo prefix.",
        ),
        _terminal_binding(
            binding_id="hairpin-pcr-reverse",
            primer=spec.hairpin_pcr_reverse_primer,
            template=spec.ligation_adapter,
            orientation=BindingOrientation.REVERSE_COMPLEMENT_5TO3,
            terminal="suffix",
            error_message=(
                "The hairpin PCR reverse primer must reverse-complement the adapter suffix."
            ),
        ),
    )
    roles = tuple(ProcessMaterialRole)
    materials = tuple(
        ProcessMaterial(
            role=role,
            material_id=oligo.material_id,
            sequence=oligo.sequence,
            modifications=oligo.modifications,
        )
        for role, oligo in zip(roles, spec.materials, strict=True)
    )
    return LinearSourceHairpinPcrMaterialsPlan(
        method_id=spec.method_id,
        spec_digest=sha256_digest(canonical_json_bytes(spec)),
        materials=materials,
        required_material_ids=tuple(material.material_id for material in materials),
        bindings=bindings,
        ligation_end_preparation=spec.ligation_end_preparation,
    )


__all__ = [
    "list_method_capabilities",
    "resolve_linear_source_hairpin_pcr_materials",
]
