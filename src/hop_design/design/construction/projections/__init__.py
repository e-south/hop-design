"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/projections/__init__.py

Exports projection builders for replay-validated local construction results.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from .basal import (
    project_basal_feasibility,
    project_basal_minimum_overhead_matrix,
)
from .complete import (
    project_complete_construction_summary,
    verify_complete_construction_projection,
)
from .foldback import (
    project_foldback_feasibility,
)
from .navigation import (
    project_complete_construction_navigation,
    verify_complete_construction_navigation,
)
from .overhead import (
    project_retained_overhead_frontier,
)
from .source_partition import (
    project_source_partition_certificate,
    verify_source_partition_projection,
)
from .trajectory import (
    project_complete_construction_trajectory,
    verify_complete_construction_trajectory,
)
from .verification import (
    verify_local_projection,
)

__all__ = [
    "project_basal_feasibility",
    "project_basal_minimum_overhead_matrix",
    "project_complete_construction_navigation",
    "project_complete_construction_summary",
    "project_complete_construction_trajectory",
    "project_foldback_feasibility",
    "project_retained_overhead_frontier",
    "project_source_partition_certificate",
    "verify_complete_construction_navigation",
    "verify_complete_construction_projection",
    "verify_complete_construction_trajectory",
    "verify_local_projection",
    "verify_source_partition_projection",
]
