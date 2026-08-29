"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/verification.py

Admits local construction results after deterministic discovery replay.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from dataclasses import dataclass

from hop_design.models.construction.basal import BasalNeighborhoodDiscoveryResult
from hop_design.models.construction.foldback import FoldbackNeighborhoodDiscoveryResult
from hop_design.serialization import canonical_json_bytes

from .basal.discovery import discover_basal_neighborhood
from .foldback.discovery import discover_foldback_neighborhood


class ConstructionVerificationError(ValueError):
    """Raised when deterministic construction discovery replay disagrees."""


@dataclass(frozen=True)
class VerifiedFoldbackNeighborhoodResult:
    """Foldback result admitted after exact deterministic discovery replay."""

    result: FoldbackNeighborhoodDiscoveryResult

    def __post_init__(self) -> None:
        object.__setattr__(self, "result", _replay_foldback_result(self.result))


@dataclass(frozen=True)
class VerifiedBasalNeighborhoodResult:
    """Basal result admitted after exact deterministic discovery replay."""

    result: BasalNeighborhoodDiscoveryResult

    def __post_init__(self) -> None:
        object.__setattr__(self, "result", _replay_basal_result(self.result))


def _replay_foldback_result(
    result: FoldbackNeighborhoodDiscoveryResult,
) -> FoldbackNeighborhoodDiscoveryResult:
    parsed = FoldbackNeighborhoodDiscoveryResult.model_validate(result.model_dump(mode="python"))
    expected = discover_foldback_neighborhood(parsed.neighborhood.request)
    if canonical_json_bytes(expected) != canonical_json_bytes(parsed):
        raise ConstructionVerificationError(
            "Foldback neighborhood result disagrees with deterministic discovery replay."
        )
    return parsed


def _replay_basal_result(
    result: BasalNeighborhoodDiscoveryResult,
) -> BasalNeighborhoodDiscoveryResult:
    parsed = BasalNeighborhoodDiscoveryResult.model_validate(result.model_dump(mode="python"))
    expected = discover_basal_neighborhood(parsed.discovery.request)
    if canonical_json_bytes(expected) != canonical_json_bytes(parsed):
        raise ConstructionVerificationError(
            "Basal neighborhood result disagrees with deterministic discovery replay."
        )
    return parsed


def verify_foldback_neighborhood_result(
    result: FoldbackNeighborhoodDiscoveryResult,
) -> VerifiedFoldbackNeighborhoodResult:
    """Rerun the exact foldback request and admit only canonical-byte equality."""
    return VerifiedFoldbackNeighborhoodResult(result=result)


def verify_basal_neighborhood_result(
    result: BasalNeighborhoodDiscoveryResult,
) -> VerifiedBasalNeighborhoodResult:
    """Rerun the exact basal request and admit only canonical-byte equality."""
    return VerifiedBasalNeighborhoodResult(result=result)


__all__ = [
    "ConstructionVerificationError",
    "VerifiedBasalNeighborhoodResult",
    "VerifiedFoldbackNeighborhoodResult",
    "verify_basal_neighborhood_result",
    "verify_foldback_neighborhood_result",
]
