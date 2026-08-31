"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/pcr/products.py

Derives exact PCR duplex products and orthogonal endpoint span classifications.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from collections.abc import Iterable

from hop_design.models.coordinates import Boundary, Span
from hop_design.models.method import BindingOrientation
from hop_design.models.molecular_state import (
    EndChemistry,
    LineageStrand,
    MaterialBaseLineage,
    MolecularStrand,
)
from hop_design.models.plan import FeatureRole, SequenceFeature
from hop_design.models.sequence import reverse_complement_iupac

from ..material import ExactConstructionMaterial, PcrPrimer
from .authority import (
    EndpointSequenceFate,
    EndpointSequenceFateSpan,
    EndpointStrand,
    MaterialFunction,
    MaterialFunctionSpan,
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


def _top_lineage(
    template: MolecularStrand,
    forward: PcrPrimer,
    reverse: PcrPrimer,
) -> tuple[MaterialBaseLineage, ...]:
    records: list[MaterialBaseLineage] = []
    for index in range(len(forward.oligo.sequence_5prime)):
        records.append(
            _lineage_record(
                product_index=len(records),
                origin_id=forward.oligo.material_id,
                origin_strand=LineageStrand.PRIMARY,
                origin_index=index,
            )
        )
    middle = template.lineage[
        forward.annealing_length_nt : len(template.sequence) - reverse.annealing_length_nt
    ]
    records.extend(
        item.model_copy(update={"product_index": len(records) + index})
        for index, item in enumerate(middle)
    )
    records.extend(
        _lineage_record(
            product_index=len(records),
            origin_id=reverse.oligo.material_id,
            origin_strand=LineageStrand.COMPLEMENTARY,
            origin_index=index,
        )
        for index in reversed(range(len(reverse.oligo.sequence_5prime)))
    )
    return tuple(
        item.model_copy(update={"product_index": index}) for index, item in enumerate(records)
    )


def pcr_products(
    template: MolecularStrand,
    forward: PcrPrimer,
    reverse: PcrPrimer,
    *,
    top_strand_id: str = "complete-hairpin-pcr-top",
    bottom_strand_id: str = "complete-hairpin-pcr-bottom",
) -> tuple[MolecularStrand, MolecularStrand]:
    """Derive the ordered PCR duplex with exact primer and template lineage."""
    validate_pcr_annealing_spans(len(template.sequence), forward, reverse)
    middle = template.sequence[
        forward.annealing_length_nt : len(template.sequence) - reverse.annealing_length_nt
    ]
    top_sequence = (
        forward.oligo.sequence_5prime
        + middle
        + reverse_complement_iupac(reverse.oligo.sequence_5prime)
    )
    top_lineage = _top_lineage(template, forward, reverse)
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


def _runs(lineage: tuple[MaterialBaseLineage, ...]) -> Iterable[tuple[int, int]]:
    start = 0
    for index in range(1, len(lineage)):
        previous = lineage[index - 1]
        current = lineage[index]
        if (
            current.origin_id != previous.origin_id
            or abs(current.origin_index - previous.origin_index) != 1
        ):
            yield start, index
            start = index
    yield start, len(lineage)


def _material_function_spans(
    function_by_material: dict[str, MaterialFunction],
    *,
    top: MolecularStrand,
    bottom: MolecularStrand,
) -> tuple[MaterialFunctionSpan, ...]:
    records: list[MaterialFunctionSpan] = []
    for endpoint_strand, product in (
        (EndpointStrand.TOP, top),
        (EndpointStrand.BOTTOM, bottom),
    ):
        for start, end in _runs(product.lineage):
            run = product.lineage[start:end]
            function = function_by_material.get(run[0].origin_id)
            if function is None:
                raise ValueError("PCR product lineage must resolve to an exact route material.")
            minimum = min(item.origin_index for item in run)
            maximum = max(item.origin_index for item in run) + 1
            orientation = (
                BindingOrientation.SAME_5TO3
                if len(run) == 1 or run[-1].origin_index > run[0].origin_index
                else BindingOrientation.REVERSE_COMPLEMENT_5TO3
            )
            records.append(
                MaterialFunctionSpan(
                    material_id=run[0].origin_id,
                    function=function,
                    material_span=_span(minimum, maximum),
                    endpoint_strand=endpoint_strand,
                    endpoint_span=_span(start, end),
                    orientation=orientation,
                )
            )
    return tuple(records)


def material_function_spans(
    *,
    materials: tuple[ExactConstructionMaterial, ...],
    top: MolecularStrand,
    bottom: MolecularStrand,
) -> tuple[MaterialFunctionSpan, ...]:
    """Map every retained input-material run to its exact endpoint occurrence."""
    return _material_function_spans(
        {
            material.material_id: function
            for material, function in zip(materials, MaterialFunction, strict=True)
        },
        top=top,
        bottom=bottom,
    )


def validate_material_function_spans(
    *,
    records: tuple[MaterialFunctionSpan, ...],
    function_by_material: dict[str, MaterialFunction],
    top: MolecularStrand,
    bottom: MolecularStrand,
) -> None:
    """Require material functions to replay their exact endpoint lineage spans."""
    if set(function_by_material.values()) != set(MaterialFunction) or any(
        function_by_material.get(record.material_id) is not record.function for record in records
    ):
        raise ValueError("PCR material-function spans must bind exact route material roles.")
    if records != _material_function_spans(
        function_by_material,
        top=top,
        bottom=bottom,
    ):
        raise ValueError("PCR material-function spans must replay exact endpoint lineage.")


def _fate(role: FeatureRole) -> EndpointSequenceFate:
    if role in {FeatureRole.PAYLOAD, FeatureRole.PAIRED_PAYLOAD}:
        return EndpointSequenceFate.PAYLOAD
    return EndpointSequenceFate.RETAINED_CONSTRUCTION


def endpoint_fate_spans(
    features: tuple[SequenceFeature, ...],
    length: int,
    *,
    design_source_span: Span | None = None,
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
    for endpoint_strand in EndpointStrand:
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
            if (
                records
                and records[-1].endpoint_strand is endpoint_strand
                and records[-1].fate is fate
                and records[-1].endpoint_span.end.offset == span.start.offset
            ):
                records[-1] = records[-1].model_copy(
                    update={
                        "endpoint_span": _span(
                            records[-1].endpoint_span.start.offset, span.end.offset
                        )
                    }
                )
            else:
                records.append(
                    EndpointSequenceFateSpan(
                        endpoint_strand=endpoint_strand,
                        endpoint_span=span,
                        fate=fate,
                    )
                )
    return tuple(records)


__all__ = [
    "endpoint_fate_spans",
    "material_function_spans",
    "pcr_products",
    "validate_material_function_spans",
    "validate_pcr_annealing_spans",
]
