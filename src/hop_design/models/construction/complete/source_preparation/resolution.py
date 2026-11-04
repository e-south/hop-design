"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/source_preparation/resolution.py

Resolves exact source-ssDNA and primer specifications under explicit policies.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.models.coordinates import Span
from hop_design.models.molecular_state import EndChemistry
from hop_design.models.sequence import reverse_complement_iupac

from ..material import ExactConstructionMaterial, MaterialResolutionMode, PcrPrimer
from ..preparation_diagnostics import PreparationConstraintCode, PreparationConstraintDiagnostic
from .authority import SourceDuplexPreparationAuthority, derive_source_duplex_preparation
from .policy import (
    ConstrainedPrimerPolicy,
    ConstrainedSourceSsdnaPolicy,
    DerivedPrimerPolicy,
    FixedPrimerPolicy,
    FixedSourceSsdnaPolicy,
    PrimerResolutionPolicy,
    SourceDuplexPreparationPolicy,
    SourceSsdnaPolicy,
    primer_required_length,
)


class SourcePreparationResolutionError(ValueError):
    """Raised with exact violated input facts when one preparation cannot resolve."""

    def __init__(
        self,
        message: str,
        *,
        code: PreparationConstraintCode,
        field: str,
        requested: int | str,
        available: int | str | None,
    ) -> None:
        super().__init__(message)
        self.diagnostic = PreparationConstraintDiagnostic(
            code=code,
            field=f"materialization.source_preparation.{field}",
            requirement="at-most"
            if code in {"primer-annealing-span-exceeded", "primer-length-bounds-incompatible"}
            else "equals",
            requested=requested,
            available=available,
            message=message,
        )


def _resolution_mode(
    policy: SourceSsdnaPolicy | PrimerResolutionPolicy,
) -> MaterialResolutionMode:
    if isinstance(policy, (FixedSourceSsdnaPolicy, FixedPrimerPolicy)):
        return MaterialResolutionMode.FIXED
    if isinstance(policy, (ConstrainedPrimerPolicy, ConstrainedSourceSsdnaPolicy)):
        return MaterialResolutionMode.CONSTRAIN
    return MaterialResolutionMode.DERIVE


def _source_material(
    policy: SourceSsdnaPolicy,
    *,
    source_sequence: str,
) -> ExactConstructionMaterial:
    if isinstance(policy, FixedSourceSsdnaPolicy):
        if policy.material.sequence_5prime != source_sequence:
            raise SourcePreparationResolutionError(
                "The fixed source ssDNA must equal the selected route source.",
                code="fixed-source-sequence-mismatch",
                field="source_ssdna.material.sequence_5prime",
                requested=policy.material.sequence_5prime,
                available=source_sequence,
            )
        return policy.material
    return ExactConstructionMaterial.model_validate(
        {
            "sequence_5prime": source_sequence,
            "five_prime_end": policy.five_prime_end,
            "three_prime_end": policy.three_prime_end,
        }
    )


def _primer_length(
    policy: PrimerResolutionPolicy,
    *,
    available_length_nt: int,
    field: str,
) -> int:
    length = primer_required_length(policy)
    if isinstance(policy, FixedPrimerPolicy):
        length_field = "primer.annealing_length_nt"
    elif isinstance(policy, DerivedPrimerPolicy):
        length_field = "annealing_length_nt"
    else:
        length_field = "min_annealing_length_nt"
    if length > available_length_nt:
        raise SourcePreparationResolutionError(
            "Source primer annealing must remain outside the payload.",
            code="primer-annealing-span-exceeded",
            field=f"{field}.{length_field}",
            requested=length,
            available=available_length_nt,
        )
    if isinstance(policy, ConstrainedPrimerPolicy) and length > policy.max_annealing_length_nt:
        raise SourcePreparationResolutionError(
            "No source primer length satisfies the declared bounds.",
            code="primer-length-bounds-incompatible",
            field=f"{field}.min_annealing_length_nt",
            requested=length,
            available=policy.max_annealing_length_nt,
        )
    return length


def _primer(
    policy: PrimerResolutionPolicy,
    *,
    sequence: str,
    annealing_length_nt: int,
    required_five_prime_end: EndChemistry,
    field: str,
) -> PcrPrimer:
    if isinstance(policy, FixedPrimerPolicy):
        if policy.primer.oligo.three_prime_end is not EndChemistry.HYDROXYL:
            raise SourcePreparationResolutionError(
                "Fixed source primer requires three-prime hydroxyl chemistry.",
                code="fixed-primer-end-chemistry-mismatch",
                field=f"{field}.primer.oligo.three_prime_end",
                requested=policy.primer.oligo.three_prime_end.value,
                available=EndChemistry.HYDROXYL.value,
            )
        if policy.primer.five_prime_handle:
            raise SourcePreparationResolutionError(
                "Source primer five-prime handles require an explicit product map.",
                code="source-primer-handle-unsupported",
                field=f"{field}.primer.oligo.sequence_5prime",
                requested=policy.primer.oligo.sequence_5prime,
                available=policy.primer.annealing_sequence,
            )
        if policy.primer.oligo.five_prime_end is not required_five_prime_end:
            raise SourcePreparationResolutionError(
                "Fixed source primer lacks the required five-prime chemistry.",
                code="fixed-primer-end-chemistry-mismatch",
                field=f"{field}.primer.oligo.five_prime_end",
                requested=policy.primer.oligo.five_prime_end.value,
                available=required_five_prime_end.value,
            )
        if (
            policy.primer.annealing_length_nt != annealing_length_nt
            or policy.primer.annealing_sequence != sequence
        ):
            raise SourcePreparationResolutionError(
                "Fixed source primer does not match the required terminal binding.",
                code="fixed-primer-binding-mismatch",
                field=f"{field}.primer.oligo.sequence_5prime",
                requested=policy.primer.annealing_sequence,
                available=sequence,
            )
        return policy.primer
    material = ExactConstructionMaterial.model_validate(
        {
            "sequence_5prime": sequence,
            "five_prime_end": required_five_prime_end,
            "three_prime_end": EndChemistry.HYDROXYL,
        }
    )
    return PcrPrimer(oligo=material, annealing_length_nt=annealing_length_nt)


def resolve_source_duplex_preparation(
    *,
    policy: SourceDuplexPreparationPolicy,
    source_sequence: str,
    payload_source_span: Span,
    reference_five_prime_end: EndChemistry,
    complement_five_prime_end: EndChemistry,
) -> SourceDuplexPreparationAuthority:
    """Resolve exact external roots and derive their copied source duplex."""
    source = _source_material(policy.source_ssdna, source_sequence=source_sequence)
    forward_length = _primer_length(
        policy.forward_primer,
        available_length_nt=payload_source_span.start.offset,
        field="forward_primer",
    )
    reverse_length = _primer_length(
        policy.reverse_primer,
        available_length_nt=len(source_sequence) - payload_source_span.end.offset,
        field="reverse_primer",
    )
    forward = _primer(
        policy.forward_primer,
        sequence=source_sequence[:forward_length],
        annealing_length_nt=forward_length,
        required_five_prime_end=reference_five_prime_end,
        field="forward_primer",
    )
    reverse = _primer(
        policy.reverse_primer,
        sequence=reverse_complement_iupac(source_sequence[-reverse_length:]),
        annealing_length_nt=reverse_length,
        required_five_prime_end=complement_five_prime_end,
        field="reverse_primer",
    )
    return derive_source_duplex_preparation(
        source_ssdna=source,
        forward_primer=forward,
        reverse_primer=reverse,
        payload_source_span=payload_source_span,
        source_resolution_mode=_resolution_mode(policy.source_ssdna),
        forward_primer_resolution_mode=_resolution_mode(policy.forward_primer),
        reverse_primer_resolution_mode=_resolution_mode(policy.reverse_primer),
    )


__all__ = ["SourcePreparationResolutionError", "resolve_source_duplex_preparation"]
