"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/complete/discovery.py

Composes exact local construction authorities into bounded complete routes.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from dataclasses import dataclass

from hop_design.design.bundle import VerifiedHopBundle, verify_hop_bundle_semantics
from hop_design.design.construction.verification import (
    VerifiedBasalNeighborhoodResult,
    VerifiedFoldbackNeighborhoodResult,
)
from hop_design.design.runtime import replay_authority
from hop_design.models.construction.complete import (
    ConstructionDiscoveryRequest,
    ConstructionSpaceResult,
)
from hop_design.models.construction.source_partition import SourcePartitionDiscoveryResult
from hop_design.serialization import canonical_json_bytes

from .admission import record_admission
from .composition import _discover_constructions_raw


@dataclass(frozen=True, eq=False)
class VerifiedConstructionSpaceResult:
    """Exact construction result admitted by derivation or independent replay."""

    result: ConstructionSpaceResult
    foldback: VerifiedFoldbackNeighborhoodResult
    basal: VerifiedBasalNeighborhoodResult | None
    design: VerifiedHopBundle

    def __post_init__(self) -> None:
        parsed, foldback, basal = _replay_construction_result(
            self.result,
            foldback=self.foldback,
            basal=self.basal,
            design=self.design,
        )
        object.__setattr__(self, "result", parsed)
        object.__setattr__(self, "foldback", foldback)
        object.__setattr__(self, "basal", basal)
        record_admission(self, parsed)


def verify_construction_space_result(
    result: ConstructionSpaceResult,
    *,
    foldback: VerifiedFoldbackNeighborhoodResult,
    basal: VerifiedBasalNeighborhoodResult | None,
    design: VerifiedHopBundle,
) -> VerifiedConstructionSpaceResult:
    """Rerun exact whole-route composition and admit only canonical-byte equality."""
    return VerifiedConstructionSpaceResult(
        result=result,
        foldback=foldback,
        basal=basal,
        design=design,
    )


def _replay_construction_result(
    result: ConstructionSpaceResult,
    *,
    foldback: VerifiedFoldbackNeighborhoodResult,
    basal: VerifiedBasalNeighborhoodResult | None,
    design: VerifiedHopBundle,
) -> tuple[
    ConstructionSpaceResult,
    VerifiedFoldbackNeighborhoodResult,
    VerifiedBasalNeighborhoodResult | None,
]:
    if not isinstance(foldback, VerifiedFoldbackNeighborhoodResult) or (
        basal is not None and not isinstance(basal, VerifiedBasalNeighborhoodResult)
    ):
        raise TypeError("Construction replay requires verified local construction authorities.")
    with replay_authority(design.provenance.compiler_version):
        verify_hop_bundle_semantics(design)
    foldback_result = foldback._verified_result()
    basal_result = None if basal is None else basal._verified_result()
    parsed = ConstructionSpaceResult.model_validate(result.model_dump(mode="python"))
    expected = _discover_constructions_raw(
        parsed.request,
        foldback=foldback_result,
        basal=basal_result,
        design=design,
        source_partition=parsed.source_partition_authority,
    )
    if canonical_json_bytes(expected) != canonical_json_bytes(parsed):
        raise ValueError(
            "Construction space result disagrees with deterministic composition replay."
        )
    return parsed, foldback, basal


def discover_constructions(
    request: ConstructionDiscoveryRequest,
    *,
    foldback: VerifiedFoldbackNeighborhoodResult,
    basal: VerifiedBasalNeighborhoodResult | None,
    design: VerifiedHopBundle,
    source_partition: SourcePartitionDiscoveryResult | None = None,
) -> VerifiedConstructionSpaceResult:
    """Compose and verify every exact compatible local combination within declared bounds."""
    if not isinstance(foldback, VerifiedFoldbackNeighborhoodResult) or (
        basal is not None and not isinstance(basal, VerifiedBasalNeighborhoodResult)
    ):
        raise TypeError("Complete composition requires verified local construction authorities.")
    with replay_authority(design.provenance.compiler_version):
        verify_hop_bundle_semantics(design)
    foldback_result = foldback._verified_result()
    basal_result = None if basal is None else basal._verified_result()
    raw = _discover_constructions_raw(
        request,
        foldback=foldback_result,
        basal=basal_result,
        design=design,
        source_partition=source_partition,
    )
    # This result was derived and strictly validated above, not supplied by a
    # caller. Seal that exact object without running the same composer twice.
    # Public receipt construction and all file admission still perform replay.
    admitted = object.__new__(VerifiedConstructionSpaceResult)
    for name, value in (
        ("result", raw),
        ("foldback", foldback),
        ("basal", basal),
        ("design", design),
    ):
        object.__setattr__(admitted, name, value)
    record_admission(admitted, raw)
    return admitted


__all__ = [
    "VerifiedConstructionSpaceResult",
    "discover_constructions",
    "verify_construction_space_result",
]
