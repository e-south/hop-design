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

__all__ = [
    "SourceDuplexPreparationAuthority",
    "derive_source_duplex_preparation",
]
