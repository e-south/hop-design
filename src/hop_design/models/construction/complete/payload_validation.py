"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/payload_validation.py

Replays final-payload coordinates against exact complete-route source materials.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from typing import Any

from hop_design.models.construction.payload import (
    SourceOrientation,
    validate_linear_source_map,
)
from hop_design.models.sequence import reverse_complement_iupac

from .request import ConstructionDiscoveryRequest


def validate_payload_source_map(request: ConstructionDiscoveryRequest, realization: Any) -> None:
    """Require mapped material bytes to replay the exact requested payload."""
    validate_linear_source_map(
        request.payload,
        realization.payload_source_map,
        allowed_orientations=(
            SourceOrientation.FORWARD,
            SourceOrientation.REVERSE_COMPLEMENT,
        ),
    )
    source_materials = {
        item.material_id: item
        for item in (
            realization.source_preparation.source_ssdna,
            *realization.materials,
        )
    }
    payload_parts: list[str] = []
    for segment in sorted(
        realization.payload_source_map.segments,
        key=lambda item: item.payload_span.start.offset,
    ):
        material = source_materials.get(segment.source_material_id)
        if material is None or segment.source_span.end.offset > len(material.sequence_5prime):
            raise ValueError("The payload source map must reference exact route material.")
        sequence = material.sequence_5prime[
            segment.source_span.start.offset : segment.source_span.end.offset
        ]
        payload_parts.append(
            sequence
            if segment.orientation is SourceOrientation.FORWARD
            else reverse_complement_iupac(sequence)
        )
    if "".join(payload_parts) != request.payload.payload.sequence:
        raise ValueError("The payload source map must replay exact requested payload bytes.")


__all__ = ["validate_payload_source_map"]
