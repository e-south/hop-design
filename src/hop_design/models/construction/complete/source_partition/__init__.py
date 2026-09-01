"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/source_partition/__init__.py

Exports complete-route bindings to selected source-partition authorities.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from .binding import SourcePartitionBinding
from .errors import (
    COMPOSITION_REJECTION_BY_BINDING_FAILURE,
    SourcePartitionBindingError,
    SourcePartitionBindingFailure,
)
from .replay import bind_source_partition

__all__ = [
    "COMPOSITION_REJECTION_BY_BINDING_FAILURE",
    "SourcePartitionBinding",
    "SourcePartitionBindingError",
    "SourcePartitionBindingFailure",
    "bind_source_partition",
]
