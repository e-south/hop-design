"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/evaluation_inputs.py

Derives complete-route source periphery and design spans from bound authorities.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from dataclasses import dataclass

from hop_design.models.construction import (
    ConstructionEndpoint,
    PayloadSourceMap,
    PayloadSourceSegment,
    SourceOrientation,
)
from hop_design.models.construction.basal import BasalRealizationRecord
from hop_design.models.construction.foldback import FoldbackLocalRealization
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.plan import FeatureRole
from hop_design.models.sequence import reverse_complement_iupac

from .material import PcrPrimer
from .request import ConstructionDiscoveryRequest


@dataclass(frozen=True, slots=True)
class LinearSourceEmbedding:
    """Exact placement of one local foldback duplex within a complete source duplex."""

    source_sequence: str
    complement_sequence: str
    local_reference_offset: int
    local_complement_offset: int
    local_source_length: int
    source_orientation: SourceOrientation


def derive_linear_source_embedding(
    *,
    foldback: FoldbackLocalRealization,
    prefix: str,
    source_return_arm: str,
) -> LinearSourceEmbedding:
    """Embed one verified local foldback source without choosing a preferred strand."""
    if len(foldback.payload_source_map.segments) != 1:
        raise ValueError("Foldback composition requires one exact payload source segment.")
    segment = foldback.payload_source_map.segments[0]
    local_source = foldback.source_reference_sequence
    local_complement = reverse_complement_iupac(local_source)
    if segment.orientation is SourceOrientation.FORWARD:
        return LinearSourceEmbedding(
            source_sequence=prefix + local_source,
            complement_sequence=local_complement + source_return_arm,
            local_reference_offset=len(prefix),
            local_complement_offset=0,
            local_source_length=len(local_source),
            source_orientation=segment.orientation,
        )
    if segment.orientation is SourceOrientation.REVERSE_COMPLEMENT:
        return LinearSourceEmbedding(
            source_sequence=local_source + source_return_arm,
            complement_sequence=prefix + local_complement,
            local_reference_offset=0,
            local_complement_offset=len(prefix),
            local_source_length=len(local_source),
            source_orientation=segment.orientation,
        )
    raise ValueError("Foldback composition requires an exact source orientation.")


def derive_complete_payload_source_map(
    *,
    foldback: FoldbackLocalRealization,
    embedding: LinearSourceEmbedding,
    source_material_id: str,
) -> PayloadSourceMap:
    """Lift the verified local payload map into complete source coordinates."""
    source_span = derive_complete_payload_source_span(
        foldback=foldback,
        embedding=embedding,
    )
    segment = foldback.payload_source_map.segments[0]
    return PayloadSourceMap(
        segments=(
            PayloadSourceSegment(
                payload_span=segment.payload_span,
                source_material_id=source_material_id,
                source_span=source_span,
                orientation=segment.orientation,
            ),
        )
    )


def derive_complete_payload_source_span(
    *,
    foldback: FoldbackLocalRealization,
    embedding: LinearSourceEmbedding,
) -> Span:
    """Lift the verified local payload occurrence into complete source coordinates."""
    segment = foldback.payload_source_map.segments[0]
    return Span(
        start=Boundary(offset=embedding.local_reference_offset + segment.source_span.start.offset),
        end=Boundary(offset=embedding.local_reference_offset + segment.source_span.end.offset),
    )


def replay_linear_source_embedding(
    *,
    foldback: FoldbackLocalRealization,
    source_sequence: str,
    complement_sequence: str,
) -> tuple[str, str, LinearSourceEmbedding]:
    """Recover and verify complete-route periphery from an exact embedded source pair."""
    segment = foldback.payload_source_map.segments[0]
    local_source = foldback.source_reference_sequence
    local_length = len(local_source)
    if segment.orientation is SourceOrientation.FORWARD:
        prefix = source_sequence[:-local_length]
        source_return_arm = complement_sequence[local_length:]
    elif segment.orientation is SourceOrientation.REVERSE_COMPLEMENT:
        source_return_arm = source_sequence[local_length:]
        prefix = complement_sequence[:-local_length]
    else:
        raise ValueError("Complete source replay requires an exact source orientation.")
    embedding = derive_linear_source_embedding(
        foldback=foldback,
        prefix=prefix,
        source_return_arm=source_return_arm,
    )
    if (
        embedding.source_sequence != source_sequence
        or embedding.complement_sequence != complement_sequence
    ):
        raise ValueError("Complete source must equal the verified foldback embedding.")
    return prefix, source_return_arm, embedding


def _design_context(request: ConstructionDiscoveryRequest) -> tuple[str, str, str]:
    features = request.design.plan.hairpin_encoding_insert.features
    payload_index = next(
        (index for index, feature in enumerate(features) if feature.role is FeatureRole.PAYLOAD),
        None,
    )
    paired_index = next(
        (
            index
            for index, feature in enumerate(features)
            if feature.role is FeatureRole.PAIRED_PAYLOAD
        ),
        None,
    )
    if payload_index is None or paired_index is None:
        raise ValueError("Complete route requires exact payload feature boundaries.")
    left = "".join(feature.sequence for feature in features[:payload_index])
    right = "".join(feature.sequence for feature in features[paired_index + 1 :])
    basal_left = tuple(
        feature.sequence for feature in features if feature.role is FeatureRole.BASAL_LEFT_ARM
    )
    if len(basal_left) != 1 or len(left) != len(right):
        raise ValueError("Complete route requires length-matched exact peripheral arms.")
    return left, right, basal_left[0]


def derive_route_prefix(
    request: ConstructionDiscoveryRequest,
    basal: BasalRealizationRecord | None,
    payload: str,
) -> str | None:
    """Return the exact prefix when the local source map agrees with the design."""
    design_prefix, _, basal_left = _design_context(request)
    if basal is None:
        return design_prefix
    if len(basal.payload_source_map.segments) != 1:
        return None
    segment = basal.payload_source_map.segments[0]
    start = segment.source_span.start.offset
    end = segment.source_span.end.offset
    if (
        segment.orientation is not SourceOrientation.FORWARD
        or end != len(basal.source_precursor_sequence)
        or basal.source_precursor_sequence[start:end] != payload
    ):
        return None
    pairing_state = basal.projection.pairing_state
    if (
        pairing_state is None
        or pairing_state.source_span.end != basal.basal_nick.boundary
        or pairing_state.source_span.end.offset > len(basal.source_precursor_sequence)
        or basal.source_precursor_sequence[pairing_state.source_span.start.offset : start]
        != basal_left
        or design_prefix != basal_left
    ):
        return None
    return basal.source_precursor_sequence[:start]


def derive_pcr_design_parent_span(
    request: ConstructionDiscoveryRequest,
    *,
    prefix: str,
    top_sequence: str,
    forward_primer: PcrPrimer,
) -> Span | None:
    """Locate the exact HOP design within one route-bearing PCR product."""
    design_prefix, _, _ = _design_context(request)
    if not prefix.endswith(design_prefix):
        return None
    start = len(forward_primer.five_prime_handle) + len(prefix) - len(design_prefix)
    end = start + len(request.design.encoding_sequence)
    if top_sequence[start:end] != request.design.encoding_sequence:
        return None
    return Span(start=Boundary(offset=start), end=Boundary(offset=end))


def derive_source_return_arm(prefix: str) -> str:
    """Derive the antiparallel PCR-source arm paired to the retained prefix."""
    return reverse_complement_iupac(prefix)


def derive_endpoint_source_return_arm(
    request: ConstructionDiscoveryRequest,
    *,
    prefix: str,
) -> str:
    """Derive the exact source-return arm required by the requested endpoint."""
    if request.endpoint is ConstructionEndpoint.SSDNA_HAIRPIN:
        _, design_return_arm, _ = _design_context(request)
        return design_return_arm
    return derive_source_return_arm(prefix)


__all__ = [
    "LinearSourceEmbedding",
    "derive_complete_payload_source_map",
    "derive_complete_payload_source_span",
    "derive_endpoint_source_return_arm",
    "derive_linear_source_embedding",
    "derive_pcr_design_parent_span",
    "derive_route_prefix",
    "derive_source_return_arm",
    "replay_linear_source_embedding",
]
