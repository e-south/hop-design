"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/construction.py

Exposes file-oriented construction compilation and scientific projections.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from hop_design.design.construction.public import (
    ConstructionCompilation,
    ConstructionProjection,
    LocalNeighborhoodDiscovery,
    SourcePartitionDiscovery,
    VerifiedConstructionBundle,
    compile_construction,
    compile_design_from_local_realizations,
    discover_local_neighborhood,
    discover_source_partition,
    load_verified_construction_bundle,
    load_verified_local_neighborhood,
    load_verified_source_partition,
    project_basal_feasibility,
    project_complete_construction_summary,
    project_construction_trajectory,
    project_foldback_feasibility,
    project_relaxation_frontier,
)

__all__ = [
    "ConstructionCompilation",
    "ConstructionProjection",
    "LocalNeighborhoodDiscovery",
    "SourcePartitionDiscovery",
    "VerifiedConstructionBundle",
    "compile_construction",
    "compile_design_from_local_realizations",
    "discover_local_neighborhood",
    "discover_source_partition",
    "load_verified_construction_bundle",
    "load_verified_local_neighborhood",
    "load_verified_source_partition",
    "project_basal_feasibility",
    "project_complete_construction_summary",
    "project_construction_trajectory",
    "project_foldback_feasibility",
    "project_relaxation_frontier",
]
