"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/projections/local.py

Defines the discriminated union of local construction scientific projections.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from .basal import BasalFeasibilityProjection, BasalMinimumOverheadMatrixProjection
from .foldback import FoldbackFeasibilityProjection
from .overhead import RetainedOverheadFrontierProjection

LocalScientificProjection = Annotated[
    FoldbackFeasibilityProjection
    | BasalFeasibilityProjection
    | BasalMinimumOverheadMatrixProjection
    | RetainedOverheadFrontierProjection,
    Field(discriminator="schema_id"),
]

__all__ = ["LocalScientificProjection"]
