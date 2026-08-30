"""Material and source-duplex helpers for the linear-source method."""

from __future__ import annotations

from pydantic import JsonValue

from hop_design.models.coordinates import Boundary, Span
from hop_design.models.diagnostics import Diagnostic, Severity
from hop_design.models.linear_source_method import (
    LinearSourceMultinickHairpinPcrRequest,
    LinearSourceMultinickHairpinPcrResult,
)
from hop_design.models.method import (
    BindingOrientation,
    MethodImplementationStatus,
    MethodOutcome,
    MethodResolutionStatus,
    OligoModification,
    ProcessMaterial,
    ProcessMaterialRole,
)
from hop_design.models.method_states import SourcePcrDuplex
from hop_design.models.molecular_replay import strand_from_sequence
from hop_design.models.molecular_state import (
    EndChemistry,
    LineageStrand,
    PrimerBinding,
)
from hop_design.models.sequence import reverse_complement_iupac


def material_by_role(
    materials: tuple[ProcessMaterial, ...], role: ProcessMaterialRole
) -> ProcessMaterial:
    return next(material for material in materials if material.role is role)


def five_prime_chemistry(material: ProcessMaterial) -> EndChemistry:
    return (
        EndChemistry.PHOSPHATE
        if OligoModification.FIVE_PRIME_PHOSPHATE in material.modifications
        else EndChemistry.HYDROXYL
    )


def primer_binding(
    binding_id: str,
    primer_id: str,
    strand_id: str,
    span: Span,
    orientation: BindingOrientation,
) -> PrimerBinding:
    return PrimerBinding(
        binding_id=binding_id,
        primer_id=primer_id,
        template_strand_id=strand_id,
        template_span=span,
        orientation=orientation,
    )


def infeasible_result(
    request: LinearSourceMultinickHairpinPcrRequest,
    *,
    code: str,
    path: str,
    message: str,
    evidence: dict[str, JsonValue],
    suggestion: str,
) -> LinearSourceMultinickHairpinPcrResult:
    diagnostic = Diagnostic(
        code=code,
        severity=Severity.ERROR,
        path=path,
        message=message,
        evidence=evidence,
        suggestions=(suggestion,),
    )
    return LinearSourceMultinickHairpinPcrResult(
        request_id=request.request_id,
        outcome=MethodOutcome(
            implementation_status=MethodImplementationStatus.AVAILABLE,
            resolution_status=MethodResolutionStatus.INFEASIBLE,
            diagnostics=(diagnostic,),
        ),
        plan=None,
    )


def build_source_pcr_duplex(
    request: LinearSourceMultinickHairpinPcrRequest,
) -> SourcePcrDuplex:
    spec = request.materials
    source = spec.source_oligo.sequence
    top = strand_from_sequence(
        strand_id="source-top",
        sequence=source,
        five_prime_end=(
            EndChemistry.PHOSPHATE
            if OligoModification.FIVE_PRIME_PHOSPHATE
            in spec.source_pcr_forward_primer.modifications
            else EndChemistry.HYDROXYL
        ),
        three_prime_end=EndChemistry.HYDROXYL,
        origin_id=spec.source_oligo.material_id,
        origin_strand=LineageStrand.PRIMARY,
        origin_indexes=range(len(source)),
    )
    bottom = strand_from_sequence(
        strand_id="source-bottom",
        sequence=reverse_complement_iupac(source),
        five_prime_end=(
            EndChemistry.PHOSPHATE
            if OligoModification.FIVE_PRIME_PHOSPHATE
            in spec.source_pcr_reverse_primer.modifications
            else EndChemistry.HYDROXYL
        ),
        three_prime_end=EndChemistry.HYDROXYL,
        origin_id=spec.source_oligo.material_id,
        origin_strand=LineageStrand.COMPLEMENTARY,
        origin_indexes=range(len(source) - 1, -1, -1),
    )
    forward_nt = len(spec.source_pcr_forward_primer.sequence)
    reverse_nt = len(spec.source_pcr_reverse_primer.sequence)
    return SourcePcrDuplex(
        top_strand=top,
        bottom_strand=bottom,
        primer_bindings=(
            primer_binding(
                "source-pcr-forward",
                spec.source_pcr_forward_primer.material_id,
                top.strand_id,
                Span(start=Boundary(offset=0), end=Boundary(offset=forward_nt)),
                BindingOrientation.SAME_5TO3,
            ),
            primer_binding(
                "source-pcr-reverse",
                spec.source_pcr_reverse_primer.material_id,
                top.strand_id,
                Span(
                    start=Boundary(offset=len(source) - reverse_nt),
                    end=Boundary(offset=len(source)),
                ),
                BindingOrientation.REVERSE_COMPLEMENT_5TO3,
            ),
        ),
    )


__all__ = [
    "build_source_pcr_duplex",
    "five_prime_chemistry",
    "infeasible_result",
    "material_by_role",
    "primer_binding",
]
