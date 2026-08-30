"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/complete/design_authority.py

Validates the exact design authority bound to complete construction.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.design.bundle import VerifiedHopBundle
from hop_design.models.construction.complete import ConstructionDiscoveryRequest


def assert_design_authority(
    request: ConstructionDiscoveryRequest,
    design: VerifiedHopBundle,
) -> None:
    """Require the request to bind every exact verified design fact."""
    encoding = design.plan.hairpin_encoding_insert
    observed = (
        design.bundle.bundle_id,
        design.spec,
        design.plan,
        design.plan.plan_id,
        design.plan.design_id,
        design.spec.payload.sequence,
        encoding.sequence,
        encoding.sequence_digest,
    )
    expected = (
        request.design.bundle.bundle_id,
        request.design.spec,
        request.design.plan,
        request.design.plan_id,
        request.design.design_id,
        request.design.payload_sequence,
        request.design.encoding_sequence,
        request.design.encoding_digest,
    )
    if observed != expected:
        raise ValueError("Construction request must bind the exact verified HOP design bundle.")


__all__ = ["assert_design_authority"]
