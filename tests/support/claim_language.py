"""
--------------------------------------------------------------------------------
HOP Design
tests/support/claim_language.py

Detects positive downstream claims on HOP's default digital-only surfaces.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import re

_FORBIDDEN_POSITIVE_CLAIM_PATTERNS = {
    "constructed product": (
        r"\b(?:is|are|was|were|has been|have been|successfully)\s+"
        r"(?:physically\s+)?constructed\b|"
        r"\bconstructed\s+(?:hairpins?|products?|libraries)\b|"
        r"\bphysically recovered\s+(?:hairpins?|products?|libraries)\b"
    ),
    "physical construction": (
        r"\b(?:establishes|demonstrates|proves|confirms)\s+"
        r"(?:successful\s+)?physical construction\b"
    ),
    "manufactured product": (
        r"\b(?:is|are|was|were|has been|have been|successfully)\s+manufactured\b|"
        r"\bmanufactured\s+(?:hairpins?|products?|libraries)\b"
    ),
    "assay-ready product": (
        r"\b(?:is|are|was|were|becomes?|returns?|produces?|yields?)\s+"
        r"(?:an?\s+)?assay-ready\b|"
        r"(?<!not )\bassay-ready\s+(?:designs?|hairpins?|products?|libraries?|output|material)\b"
    ),
    "QC-passed product": (
        r"\b(?:is|are|was|were|becomes?|returns?|produces?|yields?)\s+"
        r"(?:an?\s+)?QC-passed\b|"
        r"(?<!not )\bQC-passed\s+(?:designs?|hairpins?|products?|libraries?|output|material)\b"
    ),
    "optimal result": (
        r"\b(?:optimal|optimized)\s+"
        r"(?:designs?|candidates?|routes?|geometries|products?|methods?|architectures?)\b"
    ),
    "minimum result": (
        r"\bminimum\s+"
        r"(?:designs?|candidates?|routes?|geometries|products?|methods?|architectures?)\b"
    ),
    "ranking": (
        r"\b(?:ranks?|ranked)\s+(?:the\s+)?"
        r"(?:designs?|candidates?|routes?|geometries|products?)\b|"
        r"\b(?:produces?|provides?|establishes?)\s+(?:an?\s+)?ranking\s+"
        r"(?:of|for)\s+(?:designs?|candidates?|routes?|geometries|products?)\b"
    ),
    "validated product": (
        r"\bvalidated\s+(?:hairpin\s+anatomy|designs?|bundles?|construction|methods?|"
        r"products?|routes?)\b|"
        r"\b(?:designs?|bundles?|products?|routes?)\s+"
        r"(?:is|are|was|were|has been|have been)\s+validated\b|"
        r"\bbundle validated\b|"
        r"\bvalidate\s+(?:and compile|designs?|bundles?|construction|methods?|products?)\b"
    ),
}


def find_positive_downstream_claims(text: str) -> tuple[str, ...]:
    """Return calibrated positive-claim matches without flagging explicit nonclaims."""
    matches = []
    for claim, pattern in _FORBIDDEN_POSITIVE_CLAIM_PATTERNS.items():
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            matches.append(f"{claim}: {match.group(0)!r}")
    return tuple(matches)


def assert_no_positive_downstream_claims(text: str, *, surface: str) -> None:
    """Assert that one default digital-only surface stays within its claim boundary."""
    matches = find_positive_downstream_claims(text)
    assert not matches, f"{surface} makes forbidden positive claims: {', '.join(matches)}"
