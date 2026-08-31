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
from .authority import SourceDuplexPreparationAuthority, derive_source_duplex_preparation
from .policy import (
    ConstrainedPrimerPolicy,
    DerivedPrimerPolicy,
    DerivedSourceSsdnaPolicy,
    FixedPrimerPolicy,
    FixedSourceSsdnaPolicy,
    PrimerResolutionPolicy,
    SourceDuplexPreparationPolicy,
)


class SourcePreparationResolutionError(ValueError):
    """Raised when an explicit source-preparation policy cannot resolve one route."""


def _resolution_mode(
    policy: DerivedSourceSsdnaPolicy | FixedSourceSsdnaPolicy | PrimerResolutionPolicy,
) -> MaterialResolutionMode:
    if isinstance(policy, (FixedSourceSsdnaPolicy, FixedPrimerPolicy)):
        return MaterialResolutionMode.FIXED
    if isinstance(policy, ConstrainedPrimerPolicy):
        return MaterialResolutionMode.CONSTRAIN
    return MaterialResolutionMode.DERIVE


def _source_material(
    policy: DerivedSourceSsdnaPolicy | FixedSourceSsdnaPolicy,
    *,
    source_sequence: str,
) -> ExactConstructionMaterial:
    if isinstance(policy, FixedSourceSsdnaPolicy):
        if policy.material.sequence_5prime != source_sequence:
            raise SourcePreparationResolutionError(
                "The fixed source ssDNA must equal the selected route source."
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
) -> int:
    if isinstance(policy, FixedPrimerPolicy):
        length = policy.primer.annealing_length_nt
        if length > available_length_nt:
            raise SourcePreparationResolutionError(
                "Source primer annealing must remain outside the payload."
            )
        return length
    length = (
        policy.annealing_length_nt
        if isinstance(policy, DerivedPrimerPolicy)
        else policy.min_annealing_length_nt
    )
    if length > available_length_nt:
        raise SourcePreparationResolutionError(
            "Source primer annealing must remain outside the payload."
        )
    if isinstance(policy, ConstrainedPrimerPolicy) and length > policy.max_annealing_length_nt:
        raise SourcePreparationResolutionError(
            "No source primer length satisfies the declared bounds."
        )
    return length


def _primer(
    policy: PrimerResolutionPolicy,
    *,
    sequence: str,
    annealing_length_nt: int,
    required_five_prime_end: EndChemistry,
) -> PcrPrimer:
    if isinstance(policy, FixedPrimerPolicy):
        if policy.primer.oligo.three_prime_end is not EndChemistry.HYDROXYL:
            raise SourcePreparationResolutionError(
                "Fixed source primer requires three-prime hydroxyl chemistry."
            )
        if policy.primer.five_prime_handle:
            raise SourcePreparationResolutionError(
                "Source primer five-prime handles require an explicit product map."
            )
        if policy.primer.oligo.five_prime_end is not required_five_prime_end:
            raise SourcePreparationResolutionError(
                "Fixed source primer lacks the required five-prime chemistry."
            )
        if (
            policy.primer.annealing_length_nt != annealing_length_nt
            or policy.primer.annealing_sequence != sequence
        ):
            raise SourcePreparationResolutionError(
                "Fixed source primer does not match the required terminal binding."
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
    )
    reverse_length = _primer_length(
        policy.reverse_primer,
        available_length_nt=len(source_sequence) - payload_source_span.end.offset,
    )
    forward = _primer(
        policy.forward_primer,
        sequence=source_sequence[:forward_length],
        annealing_length_nt=forward_length,
        required_five_prime_end=reference_five_prime_end,
    )
    reverse = _primer(
        policy.reverse_primer,
        sequence=reverse_complement_iupac(source_sequence[-reverse_length:]),
        annealing_length_nt=reverse_length,
        required_five_prime_end=complement_five_prime_end,
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
