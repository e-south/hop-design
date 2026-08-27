"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/spaces.py

Exposes the minimal scientist-facing substrate-space and design-set operations.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from hop_design.design.spaces import (
    VerifiedHairpinDesignSet,
    compile_space,
    load_verified_design_set,
    preview_space,
)
from hop_design.models.design_space import (
    HairpinDesignSet,
    SubstrateSpacePreview,
    SubstrateSpaceSpec,
)

__all__ = [
    "HairpinDesignSet",
    "SubstrateSpacePreview",
    "SubstrateSpaceSpec",
    "VerifiedHairpinDesignSet",
    "compile_space",
    "load_verified_design_set",
    "preview_space",
]
