"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/source_preparation/input_validation.py

Validates source-ssDNA and terminal primer inputs for exact duplex preparation.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.models.coordinates import Boundary, Span
from hop_design.models.molecular_state import EndChemistry
from hop_design.models.sequence import reverse_complement_iupac

from ..material import ExactConstructionMaterial, PcrPrimer
from ..pcr.products import validate_pcr_annealing_spans


def coordinate_span(start: int, end: int) -> Span:
    """Return one half-open coordinate span."""
    return Span(start=Boundary(offset=start), end=Boundary(offset=end))


def _overlaps(left: Span, right: Span) -> bool:
    return left.start.offset < right.end.offset and right.start.offset < left.end.offset


def validate_source_preparation_inputs(
    *,
    source_ssdna: ExactConstructionMaterial,
    forward_primer: PcrPrimer,
    reverse_primer: PcrPrimer,
    payload_source_span: Span,
) -> None:
    """Validate exact source-copying materials and payload exclusion."""
    for material in (
        source_ssdna,
        forward_primer.oligo,
        reverse_primer.oligo,
    ):
        ExactConstructionMaterial.model_validate(material.model_dump(mode="python"))
    if (
        forward_primer.oligo.three_prime_end is not EndChemistry.HYDROXYL
        or reverse_primer.oligo.three_prime_end is not EndChemistry.HYDROXYL
    ):
        raise ValueError("Source PCR primers require exact three-prime hydroxyl chemistry.")
    if forward_primer.five_prime_handle or reverse_primer.five_prime_handle:
        raise ValueError(
            "Source PCR five-prime handles require an explicit template-to-product map."
        )
    source_length = len(source_ssdna.sequence_5prime)
    validate_pcr_annealing_spans(source_length, forward_primer, reverse_primer)
    if (
        forward_primer.annealing_sequence
        != source_ssdna.sequence_5prime[: forward_primer.annealing_length_nt]
    ):
        raise ValueError("Source PCR forward primer must match the source prefix.")
    if reverse_primer.annealing_sequence != reverse_complement_iupac(
        source_ssdna.sequence_5prime[-reverse_primer.annealing_length_nt :]
    ):
        raise ValueError("Source PCR reverse primer must reverse-complement the source suffix.")
    if payload_source_span.length.value == 0 or payload_source_span.end.offset > source_length:
        raise ValueError("Source payload span must be nonempty and lie inside the source ssDNA.")
    primer_source_spans = (
        coordinate_span(0, forward_primer.annealing_length_nt),
        coordinate_span(source_length - reverse_primer.annealing_length_nt, source_length),
    )
    if any(_overlaps(span, payload_source_span) for span in primer_source_spans):
        raise ValueError("Source PCR primer annealing must remain outside the payload.")


__all__ = ["coordinate_span", "validate_source_preparation_inputs"]
