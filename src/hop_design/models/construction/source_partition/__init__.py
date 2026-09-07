"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/source_partition/__init__.py

Exposes internal source-partition request and result contracts.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from .certificate import (
    SourcePartitionBoundaryKind,
    SourcePartitionCertificate,
    SourcePartitionFragmentBoundary,
    SourcePartitionFragmentCertificate,
    SourcePartitionFragmentDisposition,
)
from .policy import SacrificialFragmentPolicy, SourcePartitionThresholdAssessment
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
    "SacrificialFragmentPolicy",
    "SourceDuplexMaterial",
    "SourcePartitionBoundaryKind",
    "SourcePartitionCandidateDisposition",
    "SourcePartitionCertificate",
    "SourcePartitionConstraints",
    "SourcePartitionDiscoveryRequest",
    "SourcePartitionDiscoveryResult",
    "SourcePartitionDispositionKind",
    "SourcePartitionEnumerationPolicy",
    "SourcePartitionFailure",
    "SourcePartitionFragmentBoundary",
    "SourcePartitionFragmentCertificate",
    "SourcePartitionFragmentDisposition",
    "SourcePartitionNickFunction",
    "SourcePartitionRealization",
    "SourcePartitionSurvivor",
    "SourcePartitionThresholdAssessment",
    "SourcePartitionTruncationReason",
]
