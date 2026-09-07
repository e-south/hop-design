"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/projections/__init__.py

Exports projection builders for replay-validated local construction results.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from .complete import (
    project_complete_construction_summary,
    verify_complete_construction_projection,
)
from .local import (
    project_basal_feasibility,
    project_foldback_feasibility,
    project_retained_overhead_frontier,
    verify_local_projection,
)
from .navigation import (
    project_complete_construction_navigation,
    verify_complete_construction_navigation,
)
from .trajectory import (
    project_complete_construction_trajectory,
    verify_complete_construction_trajectory,
)

__all__ = [
    "project_basal_feasibility",
    "project_complete_construction_navigation",
    "project_complete_construction_summary",
    "project_complete_construction_trajectory",
    "project_foldback_feasibility",
    "project_retained_overhead_frontier",
    "verify_complete_construction_navigation",
    "verify_complete_construction_projection",
    "verify_complete_construction_trajectory",
    "verify_local_projection",
]
