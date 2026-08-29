"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/kernel/construction/basal/__init__.py

Enumerates exact basal construction programs and sequence solutions.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from .pairing import (
    derive_cohesive_end,
    resolve_basal_pairing_profile,
)
from .programs import (
    BasalPlacementFailure,
    BasalProgramCandidate,
    BasalSequenceSolution,
    iter_basal_programs,
)
from .sequences import iter_basal_program_solutions

__all__ = [
    "BasalPlacementFailure",
    "BasalProgramCandidate",
    "BasalSequenceSolution",
    "derive_cohesive_end",
    "iter_basal_program_solutions",
    "iter_basal_programs",
    "resolve_basal_pairing_profile",
]
