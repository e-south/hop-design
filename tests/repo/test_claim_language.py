"""
--------------------------------------------------------------------------------
HOP Design
tests/repo/test_claim_language.py

Calibrates forbidden positive downstream claims against explicit nonclaims.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import pytest

from tests.support.claim_language import find_positive_downstream_claims


@pytest.mark.parametrize(
    "claim",
    (
        "HOP returns optimal designs.",
        "HOP returns optimized routes.",
        "The result establishes physical construction.",
        "The evidence demonstrates physical construction.",
        "The products were constructed.",
        "Physically recovered products are ready for use.",
        "Validated designs are included.",
        "The validated products are listed.",
        "HOP returns assay-ready products.",
        "The products are QC-passed.",
        "HOP ranks candidates.",
        "The output contains ranked designs.",
    ),
)
def test_positive_downstream_claims_are_forbidden(claim: str) -> None:
    assert find_positive_downstream_claims(claim)


@pytest.mark.parametrize(
    "nonclaim",
    (
        "This does not establish physical construction.",
        "Relaxation is not an optimization.",
        "The output is not assay-ready.",
        "No QC record is attached.",
    ),
)
def test_explicit_downstream_nonclaims_are_allowed(nonclaim: str) -> None:
    assert find_positive_downstream_claims(nonclaim) == ()
