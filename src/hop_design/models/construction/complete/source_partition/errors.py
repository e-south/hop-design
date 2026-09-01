"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/source_partition/errors.py

Defines closed failure codes for binding one source partition to a complete route.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from enum import StrEnum

from ..evaluation.result import CompositionRejectionCode


class SourcePartitionBindingFailure(StrEnum):
    """Closed molecular incompatibilities at the partition-to-route boundary."""

    SOURCE_INCOMPATIBLE = "SOURCE_PARTITION_SOURCE_INCOMPATIBLE"
    STAGE_INCOMPATIBLE = "SOURCE_PARTITION_STAGE_INCOMPATIBLE"
    CUT_INCOMPATIBLE = "SOURCE_PARTITION_CUT_INCOMPATIBLE"
    SELECTION_INCOMPATIBLE = "SOURCE_PARTITION_SELECTION_INCOMPATIBLE"


class SourcePartitionBindingError(ValueError):
    """One replay-verified source partition cannot bind the selected route."""

    def __init__(self, code: SourcePartitionBindingFailure, message: str) -> None:
        self.code = code
        super().__init__(f"{code.value}: {message}")


COMPOSITION_REJECTION_BY_BINDING_FAILURE = {
    SourcePartitionBindingFailure.SOURCE_INCOMPATIBLE: (
        CompositionRejectionCode.SOURCE_PARTITION_SOURCE_INCOMPATIBLE
    ),
    SourcePartitionBindingFailure.STAGE_INCOMPATIBLE: (
        CompositionRejectionCode.SOURCE_PARTITION_STAGE_INCOMPATIBLE
    ),
    SourcePartitionBindingFailure.CUT_INCOMPATIBLE: (
        CompositionRejectionCode.SOURCE_PARTITION_CUT_INCOMPATIBLE
    ),
    SourcePartitionBindingFailure.SELECTION_INCOMPATIBLE: (
        CompositionRejectionCode.SOURCE_PARTITION_SELECTION_INCOMPATIBLE
    ),
}


__all__ = [
    "COMPOSITION_REJECTION_BY_BINDING_FAILURE",
    "SourcePartitionBindingError",
    "SourcePartitionBindingFailure",
]
