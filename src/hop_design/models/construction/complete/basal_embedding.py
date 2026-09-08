"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/basal_embedding.py

Maps an unchanged basal neighborhood into its complete upstream source context.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from hop_design.models.construction.basal import BasalRealizationRecord
from hop_design.models.construction.payload import SourceOrientation


def basal_source_offset(basal: BasalRealizationRecord, prefix: str) -> int:
    """Return the local-to-source offset while preserving every local source base."""
    segments = basal.payload_source_map.segments
    if len(segments) != 1 or segments[0].orientation is not SourceOrientation.FORWARD:
        raise ValueError("Basal embedding requires one forward payload source interval.")
    local_prefix = basal.source_precursor_sequence[: segments[0].source_span.start.offset]
    if not prefix.endswith(local_prefix):
        raise ValueError("Complete source prefix must preserve the exact basal neighborhood.")
    return len(prefix) - len(local_prefix)
