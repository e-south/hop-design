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
    ConstructionSelection,
    LocalNeighborhoodDiscovery,
    SourcePartitionDiscovery,
    VerifiedConstructionBundle,
    compile_construction,
    compile_construction_from_local_realizations,
    compile_design_from_local_realizations,
    discover_local_neighborhood,
    discover_source_partition,
    load_construction_selection,
    load_verified_construction_bundle,
    load_verified_local_neighborhood,
    load_verified_source_partition,
    project_basal_feasibility,
    project_basal_minimum_overhead_matrix,
    project_complete_construction_summary,
    project_construction_navigation,
    project_construction_trajectory,
    project_foldback_feasibility,
    project_retained_overhead_frontier,
    select_construction_realization,
)

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
    "project_basal_minimum_overhead_matrix",
    "project_complete_construction_summary",
    "project_construction_navigation",
    "project_construction_trajectory",
    "project_foldback_feasibility",
    "project_retained_overhead_frontier",
    "select_construction_realization",
]
