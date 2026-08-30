"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/evaluation_inputs.py

Derives exact complete-route prefix and return-arm inputs from bound authorities.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.models.construction.basal import BasalRealizationRecord
from hop_design.models.construction.payload import ConstructionEndpoint, SourceOrientation
from hop_design.models.plan import FeatureRole

from .request import ConstructionDiscoveryRequest


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
    if request.endpoint is ConstructionEndpoint.CLONE_READY_DUPLEX:
        return prefix if prefix.endswith(basal_left) else None
    return design_prefix if prefix == basal_left else None


def derive_route_return_arm(
    request: ConstructionDiscoveryRequest,
    basal: BasalRealizationRecord | None,
) -> str | None:
    """Return the exact terminal arm or full clone adapter required by the endpoint."""
    _, design_return_arm, _ = _design_context(request)
    if request.endpoint is not ConstructionEndpoint.CLONE_READY_DUPLEX:
        return design_return_arm
    if basal is None:
        return None
    adapter = next(
        (
            item.sequence_5prime
            for item in basal.materials
            if item.material_id == "ligation-adapter"
        ),
        None,
    )
    if adapter is None or not adapter.startswith(design_return_arm):
        return None
    return adapter


__all__ = ["derive_route_prefix", "derive_route_return_arm"]
