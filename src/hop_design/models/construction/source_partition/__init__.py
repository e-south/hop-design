"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/source_partition/__init__.py

Exposes internal source-partition request and result contracts.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from .request import (
    SourceDuplexMaterial,
    SourcePartitionConstraints,
    SourcePartitionDiscoveryRequest,
    SourcePartitionEnumerationPolicy,
    SourcePartitionSurvivor,
)
from .result import (
    SourcePartitionCandidateDisposition,
    SourcePartitionDiscoveryResult,
    SourcePartitionRealization,
)
from .types import (
    PartitionNickFunction,
    SourcePartitionDispositionKind,
    SourcePartitionFailure,
    SourcePartitionNickFunction,
    SourcePartitionTruncationReason,
)

__all__ = [
    "PartitionNickFunction",
    "SourceDuplexMaterial",
    "SourcePartitionCandidateDisposition",
    "SourcePartitionConstraints",
    "SourcePartitionDiscoveryRequest",
    "SourcePartitionDiscoveryResult",
    "SourcePartitionDispositionKind",
    "SourcePartitionEnumerationPolicy",
    "SourcePartitionFailure",
    "SourcePartitionNickFunction",
    "SourcePartitionRealization",
    "SourcePartitionSurvivor",
    "SourcePartitionTruncationReason",
]
