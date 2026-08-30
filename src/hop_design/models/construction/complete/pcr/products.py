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

from ..request import ExactConstructionMaterial
from .authority import (
    EndpointSequenceFate,
    EndpointSequenceFateSpan,
    EndpointStrand,
    MaterialFunction,
    MaterialFunctionSpan,
)


def _span(start: int, end: int) -> Span:
    return Span(start=Boundary(offset=start), end=Boundary(offset=end))


def _product_lineage(
    template: MolecularStrand,
    primer: ExactConstructionMaterial,
    *,
    reverse_template: bool,
) -> tuple[MaterialBaseLineage, ...]:
    length = len(template.sequence)
    primer_length = len(primer.sequence_5prime)
    records: list[MaterialBaseLineage] = []
    for index in range(length):
        if index < primer_length:
            record = MaterialBaseLineage(
                product_index=index,
                origin_id=primer.material_id,
                origin_strand=LineageStrand.PRIMARY,
                origin_index=index,
            )
        else:
            template_index = length - 1 - index if reverse_template else index
            record = template.lineage[template_index].model_copy(update={"product_index": index})
        records.append(record)
    return tuple(records)


def pcr_products(
    template: MolecularStrand,
    forward: ExactConstructionMaterial,
    reverse: ExactConstructionMaterial,
) -> tuple[MolecularStrand, MolecularStrand]:
    """Derive the ordered PCR duplex with exact primer and template lineage."""
    top = MolecularStrand(
        strand_id="complete-hairpin-pcr-top",
        sequence=template.sequence,
        five_prime_end=forward.five_prime_end,
        three_prime_end=EndChemistry.HYDROXYL,
        lineage=_product_lineage(template, forward, reverse_template=False),
    )
    bottom = MolecularStrand(
        strand_id="complete-hairpin-pcr-bottom",
        sequence=reverse_complement_iupac(template.sequence),
        five_prime_end=reverse.five_prime_end,
        three_prime_end=EndChemistry.HYDROXYL,
        lineage=_product_lineage(template, reverse, reverse_template=True),
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
) -> tuple[EndpointSequenceFateSpan, ...]:
    """Project exact plan-feature fates across both ordered endpoint strands."""
    records: list[EndpointSequenceFateSpan] = []
    for endpoint_strand in EndpointStrand:
        ordered = features if endpoint_strand is EndpointStrand.TOP else tuple(reversed(features))
        for feature in ordered:
            span = (
                feature.span
                if endpoint_strand is EndpointStrand.TOP
                else _span(length - feature.span.end.offset, length - feature.span.start.offset)
            )
            fate = _fate(feature.role)
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
]
