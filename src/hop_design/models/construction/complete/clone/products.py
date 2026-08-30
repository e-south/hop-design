"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/clone/products.py

Projects exact design-feature fates onto staggered clone-ready product strands.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.models.coordinates import Boundary, Span
from hop_design.models.plan import FeatureRole, SequenceFeature

from ..pcr import EndpointSequenceFate, EndpointSequenceFateSpan, EndpointStrand
from .digest import CloneDigest


def _span(start: int, end: int) -> Span:
    return Span(start=Boundary(offset=start), end=Boundary(offset=end))


def _fate(role: FeatureRole) -> EndpointSequenceFate:
    if role in {FeatureRole.PAYLOAD, FeatureRole.PAIRED_PAYLOAD}:
        return EndpointSequenceFate.PAYLOAD
    return EndpointSequenceFate.RETAINED_CONSTRUCTION


def _append(
    records: list[EndpointSequenceFateSpan],
    *,
    strand: EndpointStrand,
    start: int,
    end: int,
    fate: EndpointSequenceFate,
) -> None:
    if start == end:
        return
    if (
        records
        and records[-1].endpoint_strand is strand
        and records[-1].fate is fate
        and records[-1].endpoint_span.end.offset == start
    ):
        records[-1] = records[-1].model_copy(
            update={"endpoint_span": _span(records[-1].endpoint_span.start.offset, end)}
        )
        return
    records.append(
        EndpointSequenceFateSpan(
            endpoint_strand=strand,
            endpoint_span=_span(start, end),
            fate=fate,
        )
    )


def clone_endpoint_fate_spans(
    *,
    features: tuple[SequenceFeature, ...],
    digest: CloneDigest,
) -> tuple[EndpointSequenceFateSpan, ...]:
    """Intersect design feature fates with both exact digest product strands."""
    design_start = digest.encoding_projection.source_span.start.offset
    top_parent_start = digest.primary_parent_span.start.offset
    records: list[EndpointSequenceFateSpan] = []
    for endpoint_strand, product in (
        (EndpointStrand.TOP, digest.strands[0]),
        (EndpointStrand.BOTTOM, digest.strands[1]),
    ):
        for index in range(len(product.sequence)):
            if endpoint_strand is EndpointStrand.TOP:
                parent_top_index = top_parent_start + index
            else:
                parent_bottom_index = digest.complementary_parent_span.start.offset + index
                parent_top_index = digest.parent_length - 1 - parent_bottom_index
            design_index = parent_top_index - design_start
            feature = next(
                (
                    item
                    for item in features
                    if item.span.start.offset <= design_index < item.span.end.offset
                ),
                None,
            )
            if feature is None:
                raise ValueError("Clone endpoint bases must all map into the verified design.")
            _append(
                records,
                strand=endpoint_strand,
                start=index,
                end=index + 1,
                fate=_fate(feature.role),
            )
    return tuple(records)
