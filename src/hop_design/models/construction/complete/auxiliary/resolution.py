"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/auxiliary/resolution.py

Resolves exact endpoint auxiliary materials from local and caller constraints.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from hop_design.models.construction.basal import BasalRealizationRecord
from hop_design.models.molecular_state import EndChemistry
from hop_design.models.sequence import reverse_complement_iupac

from ..material import ExactConstructionMaterial, MaterialResolutionMode, PcrPrimer
from ..pcr.pairing import complete_adapter_pairing
from .policy import (
    ConstrainedAdapterPolicy,
    ConstrainedEndpointPrimerPolicy,
    DerivedAdapterPolicy,
    DerivedEndpointPrimerPolicy,
    EndpointAuxiliaryPolicy,
    EndpointPrimerResolutionPolicy,
    FixedAdapterPolicy,
    FixedEndpointPrimerPolicy,
)


class EndpointAuxiliaryResolutionFailure(StrEnum):
    """Closed endpoint auxiliary-resolution failure classes."""

    ADAPTER = "adapter"
    PRIMER = "primer"


class EndpointAuxiliaryResolutionError(ValueError):
    """Raised when one exact endpoint auxiliary policy cannot be resolved."""

    def __init__(self, failure: EndpointAuxiliaryResolutionFailure, message: str) -> None:
        self.failure = failure
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class EndpointAuxiliaryResolution:
    """Exact endpoint materials plus their declared specification-resolution modes."""

    adapter: ExactConstructionMaterial
    forward_primer: PcrPrimer
    reverse_primer: PcrPrimer
    adapter_mode: MaterialResolutionMode
    forward_primer_mode: MaterialResolutionMode
    reverse_primer_mode: MaterialResolutionMode

    @property
    def resolution_modes(
        self,
    ) -> tuple[MaterialResolutionMode, MaterialResolutionMode, MaterialResolutionMode]:
        """Return modes in the canonical adapter, forward, reverse order."""
        return (
            self.adapter_mode,
            self.forward_primer_mode,
            self.reverse_primer_mode,
        )


def _material(
    sequence: str,
    *,
    five_prime_end: EndChemistry,
    three_prime_end: EndChemistry,
) -> ExactConstructionMaterial:
    return ExactConstructionMaterial.model_validate(
        {
            "sequence_5prime": sequence,
            "five_prime_end": five_prime_end,
            "three_prime_end": three_prime_end,
        }
    )


def _adapter_pairing_sequence(basal: BasalRealizationRecord) -> str:
    pairing_state = basal.projection.pairing_state
    if pairing_state.adapter_span.start.offset != 0 or pairing_state.adapter_span.end.offset != len(
        pairing_state.adapter_sequence_5prime
    ):
        raise EndpointAuxiliaryResolutionError(
            EndpointAuxiliaryResolutionFailure.ADAPTER,
            "Basal authority must define one terminal adapter-pairing segment.",
        )
    try:
        return complete_adapter_pairing(basal).adapter_sequence_5prime
    except ValueError as exc:
        raise EndpointAuxiliaryResolutionError(
            EndpointAuxiliaryResolutionFailure.ADAPTER, str(exc)
        ) from exc


def _resolve_adapter(
    policy: DerivedAdapterPolicy | ConstrainedAdapterPolicy | FixedAdapterPolicy,
    *,
    basal: BasalRealizationRecord,
) -> ExactConstructionMaterial:
    pairing_sequence = _adapter_pairing_sequence(basal)
    if isinstance(policy, FixedAdapterPolicy):
        adapter = policy.material
    else:
        handle = (
            policy.three_prime_handle_sequence
            if isinstance(policy, ConstrainedAdapterPolicy)
            else ""
        )
        adapter = _material(
            pairing_sequence + handle,
            five_prime_end=EndChemistry.PHOSPHATE,
            three_prime_end=EndChemistry.HYDROXYL,
        )
    if (
        not adapter.sequence_5prime.startswith(pairing_sequence)
        or adapter.five_prime_end is not EndChemistry.PHOSPHATE
        or adapter.three_prime_end is not EndChemistry.HYDROXYL
    ):
        raise EndpointAuxiliaryResolutionError(
            EndpointAuxiliaryResolutionFailure.ADAPTER,
            "Adapter must preserve complete basal annealing and ligation chemistry.",
        )
    return adapter


def _primer_length(
    policy: EndpointPrimerResolutionPolicy,
    *,
    template_length_nt: int,
) -> int:
    if isinstance(policy, FixedEndpointPrimerPolicy):
        length = policy.primer.annealing_length_nt
    elif isinstance(policy, DerivedEndpointPrimerPolicy):
        length = policy.annealing_length_nt
    else:
        length = policy.min_annealing_length_nt
        if length > policy.max_annealing_length_nt:
            raise EndpointAuxiliaryResolutionError(
                EndpointAuxiliaryResolutionFailure.PRIMER,
                "No endpoint primer length satisfies the declared bounds.",
            )
    if length > template_length_nt:
        raise EndpointAuxiliaryResolutionError(
            EndpointAuxiliaryResolutionFailure.PRIMER,
            "Endpoint primer annealing length exceeds the exact PCR template.",
        )
    return length


def _resolve_primer(
    policy: EndpointPrimerResolutionPolicy,
    *,
    template: str,
    reverse: bool,
    annealing_region_length_nt: int,
) -> PcrPrimer:
    length = _primer_length(policy, template_length_nt=len(template))
    if length > annealing_region_length_nt:
        raise EndpointAuxiliaryResolutionError(
            EndpointAuxiliaryResolutionFailure.PRIMER,
            "Endpoint primer annealing must remain within invariant construction sequence.",
        )
    annealing = reverse_complement_iupac(template[-length:]) if reverse else template[:length]
    if isinstance(policy, FixedEndpointPrimerPolicy):
        primer = policy.primer
    else:
        handle = (
            policy.five_prime_handle_sequence
            if isinstance(policy, ConstrainedEndpointPrimerPolicy)
            else ""
        )
        primer = PcrPrimer(
            oligo=_material(
                handle + annealing,
                five_prime_end=policy.five_prime_end,
                three_prime_end=EndChemistry.HYDROXYL,
            ),
            annealing_length_nt=length,
        )
    if (
        primer.oligo.three_prime_end is not EndChemistry.HYDROXYL
        or primer.annealing_length_nt != length
        or primer.annealing_sequence != annealing
    ):
        raise EndpointAuxiliaryResolutionError(
            EndpointAuxiliaryResolutionFailure.PRIMER,
            "Endpoint primer must preserve exact terminal binding and three-prime chemistry.",
        )
    return primer


def resolve_endpoint_auxiliaries(
    *,
    policy: EndpointAuxiliaryPolicy,
    basal: BasalRealizationRecord,
    pcr_core_sequence: str,
    source_primer_region_length_nt: int,
) -> EndpointAuxiliaryResolution:
    """Resolve one exact adapter and primer set without thermodynamic ranking."""
    if not 1 <= source_primer_region_length_nt <= len(pcr_core_sequence):
        raise EndpointAuxiliaryResolutionError(
            EndpointAuxiliaryResolutionFailure.PRIMER,
            "Source primer region must be a nonempty prefix of the exact PCR core.",
        )
    adapter = _resolve_adapter(policy.adapter, basal=basal)
    template = pcr_core_sequence + adapter.sequence_5prime
    forward = _resolve_primer(
        policy.forward_primer,
        template=template,
        reverse=False,
        annealing_region_length_nt=source_primer_region_length_nt,
    )
    reverse = _resolve_primer(
        policy.reverse_primer,
        template=template,
        reverse=True,
        annealing_region_length_nt=len(adapter.sequence_5prime),
    )
    return EndpointAuxiliaryResolution(
        adapter=adapter,
        forward_primer=forward,
        reverse_primer=reverse,
        adapter_mode=policy.adapter.mode,
        forward_primer_mode=policy.forward_primer.mode,
        reverse_primer_mode=policy.reverse_primer.mode,
    )


__all__ = [
    "EndpointAuxiliaryResolution",
    "EndpointAuxiliaryResolutionError",
    "EndpointAuxiliaryResolutionFailure",
    "resolve_endpoint_auxiliaries",
]
