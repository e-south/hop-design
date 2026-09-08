"""
--------------------------------------------------------------------------------
HOP Design
tests/contract/test_basal_cohesive_end_domain.py

Tests variable cohesive-end requirements and their exact basal targets.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import pytest

from hop_design.models.construction import (
    BasalFutureReleaseRequirement,
    BasalGeometryDomain,
    BasalPairAllowance,
    BasalPairConstraint,
    BasalTarget,
    geometry_id,
)
from hop_design.models.molecular_state import StrandEnd
from hop_design.models.physical import SiteOrientation, Strand


def _release(sequence: str) -> BasalFutureReleaseRequirement:
    return BasalFutureReleaseRequirement.model_validate(
        {
            "product_end": "right",
            "orientation": SiteOrientation.REVERSE,
            "cohesive_end_sequence": sequence,
            "overhang_end": StrandEnd.FIVE_PRIME,
            "recognition_material": "source_duplex",
        }
    )


def _domain(sequence: str, *, offsets: tuple[int, ...] = (0, 2)) -> BasalGeometryDomain:
    return BasalGeometryDomain(
        nick_offsets_nt=offsets,
        pairing_constraints=(
            BasalPairConstraint(position_from_ligation=0, allowed_class=BasalPairAllowance.MATCH),
        ),
        future_release=_release(sequence),
    )


def test_basal_domain_expands_only_declared_cohesive_end_bases() -> None:
    domain = _domain("aary")
    targets = tuple(domain.exact_targets())
    assert domain.future_release.cohesive_end_sequence == "AARY"
    assert [
        (target.nick_offset_nt, target.future_release.cohesive_end_sequence) for target in targets
    ] == [
        (0, "AAAC"),
        (0, "AAAT"),
        (0, "AAGC"),
        (0, "AAGT"),
        (2, "AAAC"),
        (2, "AAAT"),
        (2, "AAGC"),
        (2, "AAGT"),
    ]
    assert len({geometry_id(target) for target in targets}) == 8
    assert all(target.future_release.recognition_material == "source_duplex" for target in targets)


def test_an_exact_basal_target_cannot_retain_a_symbolic_overhang() -> None:
    with pytest.raises(ValueError, match=r"exact.*cohesive|cohesive.*exact"):
        BasalTarget(
            nick_strand=Strand.TOP,
            nick_offset_nt=0,
            future_release=_release("AANN"),
        )


def test_cohesive_end_membership_preserves_other_release_requirements() -> None:
    domain = _release("AARY")
    assert domain.permits(_release("AAAC"))
    assert not domain.permits(_release("AACC"))
    assert not domain.permits(_release("AAA"))
    assert not domain.permits(_release("AARY"))
    assert not domain.permits(
        _release("AAAC").model_copy(update={"recognition_material": "endpoint_material"})
    )


def test_basal_geometry_size_is_checked_before_sequence_expansion() -> None:
    with pytest.raises(ValueError, match="100000 exact basal targets"):
        _domain("N" * 1000)
