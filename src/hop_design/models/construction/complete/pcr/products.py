"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/pcr/products.py

Derives exact PCR duplex products and orthogonal endpoint span classifications.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from itertools import pairwise

from hop_design.models.coordinates import Boundary, Span
from hop_design.models.molecular_state import (
    EndChemistry,
    LineageStrand,
    MaterialBaseLineage,
    MolecularStrand,
)
from hop_design.models.plan import FeatureRole, SequenceFeature
from hop_design.models.sequence import reverse_complement_iupac

from ..material import PcrPrimer
from .authority import (
    EndpointSequenceFate,
    EndpointSequenceFateSpan,
    EndpointStrand,
)


def _span(start: int, end: int) -> Span:
    return Span(start=Boundary(offset=start), end=Boundary(offset=end))


def _lineage_record(
    *,
    product_index: int,
    origin_id: str,
    origin_strand: LineageStrand,
    origin_index: int,
) -> MaterialBaseLineage:
    return MaterialBaseLineage(
        product_index=product_index,
        origin_id=origin_id,
        origin_strand=origin_strand,
        origin_index=origin_index,
    )


def validate_pcr_annealing_spans(
    template_length: int,
    forward: PcrPrimer,
    reverse: PcrPrimer,
) -> None:
    """Require nonoverlapping terminal primer-binding spans on one template."""
    if forward.annealing_length_nt + reverse.annealing_length_nt > template_length:
        raise ValueError("PCR primer annealing spans must not overlap on the template.")


def derive_pcr_product_sequence(
    template_sequence: str,
    forward: PcrPrimer,
    reverse: PcrPrimer,
) -> str:
    """Derive the exact top-strand PCR product from terminal primer bindings."""
    validate_pcr_annealing_spans(len(template_sequence), forward, reverse)
    middle = template_sequence[
        forward.annealing_length_nt : len(template_sequence) - reverse.annealing_length_nt
    ]
    return (
        forward.oligo.sequence_5prime
        + middle
        + reverse_complement_iupac(reverse.oligo.sequence_5prime)
    )


def _top_lineage(
    template: MolecularStrand,
    forward: PcrPrimer,
    reverse: PcrPrimer,
    *,
    forward_use_id: str,
    reverse_use_id: str,
) -> tuple[MaterialBaseLineage, ...]:
    records: list[MaterialBaseLineage] = []
    for index in range(len(forward.oligo.sequence_5prime)):
        records.append(
            _lineage_record(
                product_index=len(records),
                origin_id=forward_use_id,
                origin_strand=LineageStrand.PRIMARY,
                origin_index=index,
            )
        )
    middle = template.lineage[
        forward.annealing_length_nt : len(template.sequence) - reverse.annealing_length_nt
    ]
    for item in middle:
        records.append(item.model_copy(update={"product_index": len(records)}))
    for index in reversed(range(len(reverse.oligo.sequence_5prime))):
        records.append(
            _lineage_record(
                product_index=len(records),
                origin_id=reverse_use_id,
                origin_strand=LineageStrand.COMPLEMENTARY,
                origin_index=index,
            )
        )
    return tuple(records)


def pcr_products(
    template: MolecularStrand,
    forward: PcrPrimer,
    reverse: PcrPrimer,
    *,
    forward_use_id: str,
    reverse_use_id: str,
    top_strand_id: str = "complete-hairpin-pcr-top",
    bottom_strand_id: str = "complete-hairpin-pcr-bottom",
) -> tuple[MolecularStrand, MolecularStrand]:
    """Derive the ordered PCR duplex with exact primer and template lineage."""
    top_sequence = derive_pcr_product_sequence(template.sequence, forward, reverse)
    top_lineage = _top_lineage(
        template,
        forward,
        reverse,
        forward_use_id=forward_use_id,
        reverse_use_id=reverse_use_id,
    )
    top = MolecularStrand(
        strand_id=top_strand_id,
        sequence=top_sequence,
        five_prime_end=forward.oligo.five_prime_end,
        three_prime_end=EndChemistry.HYDROXYL,
        lineage=top_lineage,
    )
    bottom = MolecularStrand(
        strand_id=bottom_strand_id,
        sequence=reverse_complement_iupac(top_sequence),
        five_prime_end=reverse.oligo.five_prime_end,
        three_prime_end=EndChemistry.HYDROXYL,
        lineage=tuple(
            _lineage_record(
                product_index=index,
                origin_id=record.origin_id,
                origin_strand=(
                    LineageStrand.COMPLEMENTARY
                    if record.origin_strand is LineageStrand.PRIMARY
                    else LineageStrand.PRIMARY
                ),
                origin_index=record.origin_index,
            )
            for index, record in enumerate(reversed(top_lineage))
        ),
    )
    return top, bottom


def _fate(role: FeatureRole) -> EndpointSequenceFate:
    if role in {FeatureRole.PAYLOAD, FeatureRole.PAIRED_PAYLOAD}:
        return EndpointSequenceFate.PAYLOAD
    return EndpointSequenceFate.RETAINED_CONSTRUCTION


def endpoint_fate_spans(
    features: tuple[SequenceFeature, ...],
    length: int,
    *,
    design_source_span: Span | None = None,
    retained_parent_spans: tuple[Span, Span] | None = None,
) -> tuple[EndpointSequenceFateSpan, ...]:
    """Project exact plan-feature fates across both ordered endpoint strands."""
    source_span = design_source_span or _span(0, length)
    if source_span.length.value != sum(feature.span.length.value for feature in features):
        raise ValueError("PCR design span must equal the complete ordered feature length.")
    if source_span.end.offset > length:
        raise ValueError("PCR design span must lie inside the complete template.")
    top_segments: list[tuple[Span, EndpointSequenceFate]] = []
    if source_span.start.offset:
        top_segments.append(
            (_span(0, source_span.start.offset), EndpointSequenceFate.TRANSIENT_CONSTRUCTION)
        )
    top_segments.extend(
        (
            _span(
                source_span.start.offset + feature.span.start.offset,
                source_span.start.offset + feature.span.end.offset,
            ),
            _fate(feature.role),
        )
        for feature in features
    )
    if source_span.end.offset < length:
        top_segments.append(
            (
                _span(source_span.end.offset, length),
                EndpointSequenceFate.TRANSIENT_CONSTRUCTION,
            )
        )
    records: list[EndpointSequenceFateSpan] = []
    if retained_parent_spans is not None and any(
        span.length.value == 0 or span.end.offset > length for span in retained_parent_spans
    ):
        raise ValueError("Endpoint retention must name nonempty spans within both PCR strands.")
    for strand_index, endpoint_strand in enumerate(EndpointStrand):
        ordered = (
            tuple(top_segments)
            if endpoint_strand is EndpointStrand.TOP
            else tuple(reversed(top_segments))
        )
        for source, fate in ordered:
            span = (
                source
                if endpoint_strand is EndpointStrand.TOP
                else _span(length - source.end.offset, length - source.start.offset)
            )
            pieces = (
                ((span, fate),)
                if retained_parent_spans is None
                else _retained_fates(span, fate, retained_parent_spans[strand_index])
            )
            for piece, final_fate in pieces:
                if (
                    records
                    and records[-1].endpoint_strand is endpoint_strand
                    and records[-1].fate is final_fate
                    and records[-1].endpoint_span.end.offset == piece.start.offset
                ):
                    records[-1] = records[-1].model_copy(
                        update={
                            "endpoint_span": _span(
                                records[-1].endpoint_span.start.offset, piece.end.offset
                            )
                        }
                    )
                else:
                    records.append(
                        EndpointSequenceFateSpan(
                            endpoint_strand=endpoint_strand,
                            endpoint_span=piece,
                            fate=final_fate,
                        )
                    )
    return tuple(records)


def _retained_fates(
    span: Span,
    fate: EndpointSequenceFate,
    retained: Span,
) -> tuple[tuple[Span, EndpointSequenceFate], ...]:
    boundaries = sorted(
        {
            span.start.offset,
            span.end.offset,
            *(
                boundary
                for boundary in (retained.start.offset, retained.end.offset)
                if span.start.offset < boundary < span.end.offset
            ),
        }
    )
    pieces = []
    for start, end in pairwise(boundaries):
        final_fate = (
            (
                EndpointSequenceFate.PAYLOAD
                if fate is EndpointSequenceFate.PAYLOAD
                else EndpointSequenceFate.RETAINED_CONSTRUCTION
            )
            if retained.start.offset <= start < retained.end.offset
            else EndpointSequenceFate.TRANSIENT_CONSTRUCTION
        )
        pieces.append((_span(start, end), final_fate))
    return tuple(pieces)


__all__ = [
    "endpoint_fate_spans",
    "pcr_products",
    "validate_pcr_annealing_spans",
]
