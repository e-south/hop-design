"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/public.py

Provides opaque construction receipts and deterministic scientific projections.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from hop_design.design.construction.projections import (
    project_basal_feasibility as _project_basal_feasibility,
)
from hop_design.design.construction.projections import (
    project_complete_construction_navigation as _project_complete_construction_navigation,
)
from hop_design.design.construction.projections import (
    project_complete_construction_summary as _project_complete_construction_summary,
)
from hop_design.design.construction.projections import (
    project_complete_construction_trajectory as _project_complete_construction_trajectory,
)
from hop_design.design.construction.projections import (
    project_foldback_feasibility as _project_foldback_feasibility,
)
from hop_design.design.construction.projections import (
    project_retained_overhead_frontier as _project_retained_overhead_frontier,
)
from hop_design.models.construction.basal import BasalNeighborhoodDiscoveryResult
from hop_design.models.construction.foldback import FoldbackNeighborhoodDiscoveryResult
from hop_design.models.construction.projections import (
    CompleteConstructionSummaryProjection,
    CompleteConstructionTrajectoryProjection,
    ConstructionNavigationProjection,
    LocalScientificProjection,
)

from .complete.bundle import ConstructionCompilation, VerifiedConstructionBundle
from .complete.discovery import VerifiedConstructionSpaceResult
from .design_authority import compile_design_from_local_realizations
from .local_public import (
    LocalNeighborhoodDiscovery,
    discover_local_neighborhood,
    load_verified_local_neighborhood,
)
from .projection_packet import ConstructionProjection
from .selection_reference import (
    ConstructionSelection,
    load_construction_selection,
    select_construction_realization,
)
from .source_partition import (
    SourcePartitionDiscovery,
    discover_source_partition,
    load_verified_source_partition,
)


def _source(
    receipt: ConstructionCompilation | VerifiedConstructionBundle,
) -> VerifiedConstructionSpaceResult:
    if not isinstance(receipt, ConstructionCompilation | VerifiedConstructionBundle):
        raise TypeError("Construction projections require a verified construction receipt.")
    return receipt._verified_source()


def _foldback_source(
    receipt: ConstructionCompilation | VerifiedConstructionBundle | LocalNeighborhoodDiscovery,
) -> FoldbackNeighborhoodDiscoveryResult:
    if isinstance(receipt, LocalNeighborhoodDiscovery):
        result = receipt._verified_source()
        if not isinstance(result, FoldbackNeighborhoodDiscoveryResult):
            raise ValueError("Local-neighborhood receipt contains basal evidence, not foldback.")
        return result
    return _source(receipt).foldback.result


def _basal_source(
    receipt: ConstructionCompilation | VerifiedConstructionBundle | LocalNeighborhoodDiscovery,
) -> BasalNeighborhoodDiscoveryResult:
    if isinstance(receipt, LocalNeighborhoodDiscovery):
        result = receipt._verified_source()
        if not isinstance(result, BasalNeighborhoodDiscoveryResult):
            raise ValueError("Local-neighborhood receipt contains foldback evidence, not basal.")
        return result
    basal = _source(receipt).basal
    if basal is None:
        raise ValueError("This construction does not contain a basal authority.")
    return basal.result


def _packet(
    projection: (
        LocalScientificProjection
        | CompleteConstructionSummaryProjection
        | CompleteConstructionTrajectoryProjection
        | ConstructionNavigationProjection
    ),
) -> ConstructionProjection:
    return ConstructionProjection._create(projection)


def compile_construction(
    source_path: str | Path,
    *,
    design_bundle_path: str | Path,
) -> ConstructionCompilation:
    """Compile one strict construction source against one verified design bundle."""
    from hop_design.design.construction.source import compile_construction_source

    return compile_construction_source(
        source_path,
        design_bundle_path=design_bundle_path,
    )


def compile_construction_from_local_realizations(
    source_path: str | Path,
    *,
    design_bundle_path: str | Path,
    foldback: LocalNeighborhoodDiscovery,
    foldback_realization_id: str,
    basal: LocalNeighborhoodDiscovery | None = None,
    basal_realization_id: str | None = None,
    source_partition: SourcePartitionDiscovery | None = None,
    source_partition_realization_id: str | None = None,
) -> ConstructionCompilation:
    """Compile one endpoint-complete selection from verified local receipts."""
    from hop_design.design.construction.source import (
        compile_construction_source_from_local_realizations,
    )

    return compile_construction_source_from_local_realizations(
        source_path,
        design_bundle_path=design_bundle_path,
        foldback=foldback,
        foldback_realization_id=foldback_realization_id,
        basal=basal,
        basal_realization_id=basal_realization_id,
        source_partition=source_partition,
        source_partition_realization_id=source_partition_realization_id,
    )


def load_verified_construction_bundle(
    bundle_path: str | Path,
) -> VerifiedConstructionBundle:
    """Load one portable construction authority after exact semantic replay."""
    from hop_design.design.construction.complete.bundle import (
        load_verified_construction_bundle as _load,
    )

    return _load(bundle_path)


def project_foldback_feasibility(
    receipt: ConstructionCompilation | VerifiedConstructionBundle | LocalNeighborhoodDiscovery,
) -> ConstructionProjection:
    """Project every exact foldback realization from one verified construction."""
    return _packet(_project_foldback_feasibility(_foldback_source(receipt)))


def project_basal_feasibility(
    receipt: ConstructionCompilation | VerifiedConstructionBundle | LocalNeighborhoodDiscovery,
) -> ConstructionProjection:
    """Project every exact basal realization from one verified construction."""
    return _packet(_project_basal_feasibility(_basal_source(receipt)))


def project_complete_construction_summary(
    receipt: ConstructionCompilation | VerifiedConstructionBundle,
) -> ConstructionProjection:
    """Project lossless complete-route accounting from one verified construction."""
    return _packet(_project_complete_construction_summary(_source(receipt)))


def project_construction_navigation(
    receipt: ConstructionCompilation | VerifiedConstructionBundle,
) -> ConstructionProjection:
    """Project rich browseable facts without changing construction authority."""
    return _packet(_project_complete_construction_navigation(_source(receipt)))


def project_construction_trajectory(
    receipt: ConstructionCompilation | VerifiedConstructionBundle,
    *,
    materialized_realization_id: str,
) -> ConstructionProjection:
    """Project one explicitly selected accepted construction chronology."""
    return _packet(
        _project_complete_construction_trajectory(
            _source(receipt),
            materialized_realization_id=materialized_realization_id,
        )
    )


def project_retained_overhead_frontier(
    receipt: ConstructionCompilation | VerifiedConstructionBundle | LocalNeighborhoodDiscovery,
    *,
    family: Literal["foldback", "basal"],
) -> ConstructionProjection:
    """Project retained-overhead coverage for one local neighborhood family."""
    if family == "foldback":
        return _packet(_project_retained_overhead_frontier(_foldback_source(receipt)))
    if family == "basal":
        return _packet(_project_retained_overhead_frontier(_basal_source(receipt)))
    raise ValueError("Construction projection family must be foldback or basal.")


__all__ = [
    "ConstructionCompilation",
    "ConstructionProjection",
    "ConstructionSelection",
    "LocalNeighborhoodDiscovery",
    "SourcePartitionDiscovery",
    "VerifiedConstructionBundle",
    "compile_construction",
    "compile_construction_from_local_realizations",
    "compile_design_from_local_realizations",
    "discover_local_neighborhood",
    "discover_source_partition",
    "load_construction_selection",
    "load_verified_construction_bundle",
    "load_verified_local_neighborhood",
    "load_verified_source_partition",
    "project_basal_feasibility",
    "project_complete_construction_summary",
    "project_construction_navigation",
    "project_construction_trajectory",
    "project_foldback_feasibility",
    "project_retained_overhead_frontier",
    "select_construction_realization",
]
