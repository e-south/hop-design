"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/source_partition/types.py

Defines closed source-partition dispositions, failure reasons, and nick functions.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from enum import StrEnum

from hop_design.models.base import HopModel
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.junction import Strand
from hop_design.models.physical import SiteOrientation
from hop_design.models.references import ReferenceId


class PartitionNickFunction(StrEnum):
    """Physical consequence of one nick within the complete source partition."""

    RETAINED_FRAGMENT_BOUNDARY = "retained_fragment_boundary"
    EXCLUDED_FRAGMENT_CLEANUP = "excluded_fragment_cleanup"


class SourcePartitionFailure(StrEnum):
    """Closed rejection reasons for one exact enzyme subset."""

    NO_ACTIONABLE_SITES = "no_actionable_sites"
    CONFLICTING_CUT_BOUNDARIES = "conflicting_cut_boundaries"
    OPERATION_LIMIT_EXCEEDED = "operation_limit_exceeded"
    RETAINED_FRAGMENT_SET_MISMATCH = "retained_fragment_set_mismatch"


class SourcePartitionDispositionKind(StrEnum):
    """Whether one exact enzyme subset produces the required source partition."""

    ACCEPTED = "accepted"
    REJECTED = "rejected"


class SourcePartitionNickFunction(HopModel):
    """One exact nick and its route-level partition role."""

    enzyme_id: ReferenceId
    recognition_span: Span
    orientation: SiteOrientation
    strand: Strand
    boundary: Boundary
    function: PartitionNickFunction


class SourcePartitionTruncationReason(StrEnum):
    """Closed execution bounds that may stop source-partition enumeration."""

    MAX_SEARCH_NODES = "max_search_nodes"
    MAX_REALIZATIONS = "max_realizations"


__all__ = [
    "PartitionNickFunction",
    "SourcePartitionDispositionKind",
    "SourcePartitionFailure",
    "SourcePartitionNickFunction",
    "SourcePartitionTruncationReason",
]
