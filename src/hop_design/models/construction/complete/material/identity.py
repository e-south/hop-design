"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/material/identity.py

Defines deterministic identities for exact construction materials.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from typing import Literal

from hop_design.models.molecular_state import EndChemistry
from hop_design.models.sequence import normalize_dna_sequence
from hop_design.serialization import canonical_json_bytes, sha256_digest


def construction_material_id(
    sequence: str,
    *,
    five_prime_end: EndChemistry,
    three_prime_end: EndChemistry,
    polymer_type: Literal["DNA"] = "DNA",
    strandedness: Literal["single_stranded"] = "single_stranded",
    topology: Literal["linear"] = "linear",
) -> str:
    """Return molecular content identity independent of contextual route use."""
    normalized = normalize_dna_sequence(sequence, allow_degenerate=False)
    digest = sha256_digest(
        canonical_json_bytes(
            {
                "schema": "hop.exact-construction-material/v1",
                "polymer_type": polymer_type,
                "strandedness": strandedness,
                "topology": topology,
                "sequence_5prime": normalized,
                "five_prime_end": five_prime_end,
                "three_prime_end": three_prime_end,
            }
        )
    ).removeprefix("sha256:")
    return f"hop:construction-material/{digest}@1"


__all__ = ["construction_material_id"]
