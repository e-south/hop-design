"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/specs.py

Builds catalog-backed design specifications from one authored payload sequence.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import hashlib

from hop_design.catalog.defaults import (
    BASAL_REF,
    CONSTRAINT_PROFILE_REF,
    DEFAULTS_REF,
    DESIGN_DERIVATION_REF,
    FOLDBACK_REF,
)
from hop_design.models.payload import DegeneratePayload, ExactPayload
from hop_design.models.sequence import EXACT_DNA_ALPHABET, normalize_dna_sequence
from hop_design.models.spec import (
    BasalSelection,
    DesignLimits,
    FoldbackSelection,
    HopSpec,
    JunctionRequest,
)


def create_catalog_spec(*, sequence: str, design_id: str | None = None) -> HopSpec:
    """Build one strict design specification against the locked public catalog."""
    normalized = normalize_dna_sequence(sequence, allow_degenerate=True)
    payload = (
        ExactPayload(sequence=normalized)
        if set(normalized) <= EXACT_DNA_ALPHABET
        else DegeneratePayload(sequence=normalized)
    )
    resolved_design_id = (
        design_id or f"sequence-{hashlib.sha256(normalized.encode()).hexdigest()[:8]}"
    )
    return HopSpec(
        design_id=resolved_design_id,
        payload=payload,
        junction=JunctionRequest(
            foldback=FoldbackSelection(ref=FOLDBACK_REF),
            basal=BasalSelection(ref=BASAL_REF),
        ),
        design_derivation_ref=DESIGN_DERIVATION_REF,
        constraint_profile_ref=CONSTRAINT_PROFILE_REF,
        defaults_ref=DEFAULTS_REF,
        constraints=DesignLimits(max_candidates=1),
    )


__all__ = ["create_catalog_spec"]
