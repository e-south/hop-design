"""Strict contracts for geometry and concrete-sequence discovery."""

from hop_design.models.discovery.candidates import (
    AdditionalNickConstraint,
    CandidateRejectionCode,
    CandidateRejectionSummary,
    CandidateSearchStatus,
    CandidateSearchTruncation,
    FoldbackPrecursorCandidate,
    FoldbackPrecursorSearchLimits,
    FoldbackPrecursorSearchRequest,
    FoldbackPrecursorSearchResult,
)
from hop_design.models.discovery.placements import (
    NickingPlacementBlocker,
    NickingPlacementFeasibility,
    NickingPlacementHit,
    NickingPlacementSearchLimits,
    NickingPlacementSearchResult,
    NickingPlacementTarget,
    NickingPlacementTruncation,
)

__all__ = [
    "AdditionalNickConstraint",
    "CandidateRejectionCode",
    "CandidateRejectionSummary",
    "CandidateSearchStatus",
    "CandidateSearchTruncation",
    "FoldbackPrecursorCandidate",
    "FoldbackPrecursorSearchLimits",
    "FoldbackPrecursorSearchRequest",
    "FoldbackPrecursorSearchResult",
    "NickingPlacementBlocker",
    "NickingPlacementFeasibility",
    "NickingPlacementHit",
    "NickingPlacementSearchLimits",
    "NickingPlacementSearchResult",
    "NickingPlacementTarget",
    "NickingPlacementTruncation",
]
