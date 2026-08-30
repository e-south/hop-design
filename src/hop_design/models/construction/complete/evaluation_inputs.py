"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/evaluation_inputs.py

Derives exact complete-route prefix and return-arm inputs from bound authorities.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from dataclasses import dataclass

from hop_design.models.construction import (
    PayloadSourceMap,
    PayloadSourceSegment,
    SourceOrientation,
)
from hop_design.models.construction.basal import BasalRealizationRecord
from hop_design.models.construction.foldback import FoldbackLocalRealization
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.plan import FeatureRole
from hop_design.models.sequence import reverse_complement_iupac

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
    return_arm: str,
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
            complement_sequence=local_complement + return_arm,
            local_reference_offset=len(prefix),
            local_complement_offset=0,
            local_source_length=len(local_source),
            source_orientation=segment.orientation,
        )
    if segment.orientation is SourceOrientation.REVERSE_COMPLEMENT:
        return LinearSourceEmbedding(
            source_sequence=local_source + return_arm,
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
    segment = foldback.payload_source_map.segments[0]
    return PayloadSourceMap(
        segments=(
            PayloadSourceSegment(
                payload_span=segment.payload_span,
                source_material_id=source_material_id,
                source_span=Span(
                    start=Boundary(
                        offset=(embedding.local_reference_offset + segment.source_span.start.offset)
                    ),
                    end=Boundary(
                        offset=(embedding.local_reference_offset + segment.source_span.end.offset)
                    ),
                ),
                orientation=segment.orientation,
            ),
        )
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
        return_arm = complement_sequence[local_length:]
    elif segment.orientation is SourceOrientation.REVERSE_COMPLEMENT:
        return_arm = source_sequence[local_length:]
        prefix = complement_sequence[:-local_length]
    else:
        raise ValueError("Complete source replay requires an exact source orientation.")
    embedding = derive_linear_source_embedding(
        foldback=foldback,
        prefix=prefix,
        return_arm=return_arm,
    )
    if (
        embedding.source_sequence != source_sequence
        or embedding.complement_sequence != complement_sequence
    ):
        raise ValueError("Complete source must equal the verified foldback embedding.")
    return prefix, return_arm, embedding


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
    prefix = basal.source_precursor_sequence[:start]
    return design_prefix if prefix == basal_left else None


def derive_route_return_arm(
    request: ConstructionDiscoveryRequest,
    basal: BasalRealizationRecord | None,
) -> str | None:
    """Return the exact terminal arm or full clone adapter required by the endpoint."""
    _, design_return_arm, _ = _design_context(request)
    if basal is None:
        return design_return_arm
    adapter = next(
        (
            item.sequence_5prime
            for item in basal.materials
            if item.material_id == "ligation-adapter"
        ),
        None,
    )
    if adapter != design_return_arm:
        return None
    return adapter


__all__ = [
    "LinearSourceEmbedding",
    "derive_complete_payload_source_map",
    "derive_linear_source_embedding",
    "derive_route_prefix",
    "derive_route_return_arm",
    "replay_linear_source_embedding",
]
