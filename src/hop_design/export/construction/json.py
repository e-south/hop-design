"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/export/construction/json.py

Serializes typed construction projections as deterministic canonical JSON.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.models.construction.projections import (
    ConstructionScientificProjection,
)
from hop_design.serialization import canonical_json_bytes


def render_projection_json(projection: ConstructionScientificProjection) -> bytes:
    """Render one typed scientific projection as canonical JSON bytes."""
    return canonical_json_bytes(projection)
