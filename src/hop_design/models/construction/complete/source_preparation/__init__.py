"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/source_preparation/__init__.py

Exposes exact source-ssDNA copying authorities for complete construction.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from .authority import (
    SourceDuplexPreparationAuthority,
    derive_source_duplex_preparation,
)
from .policy import (
    ConstrainedPrimerPolicy,
    DerivedPrimerPolicy,
    DerivedSourceSsdnaPolicy,
    FixedPrimerPolicy,
    FixedSourceSsdnaPolicy,
    SourceDuplexPreparationPolicy,
)
from .resolution import resolve_source_duplex_preparation

__all__ = [
    "ConstrainedPrimerPolicy",
    "DerivedPrimerPolicy",
    "DerivedSourceSsdnaPolicy",
    "FixedPrimerPolicy",
    "FixedSourceSsdnaPolicy",
    "SourceDuplexPreparationAuthority",
    "SourceDuplexPreparationPolicy",
    "derive_source_duplex_preparation",
    "resolve_source_duplex_preparation",
]
