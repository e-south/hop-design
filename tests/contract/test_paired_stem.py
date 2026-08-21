from __future__ import annotations

import pytest
from pydantic import ValidationError

import hop_design as hop


def test_paired_stem_extension_preserves_literal_arms_and_pair_calls() -> None:
    extension = hop.evaluate_paired_stem_extension(
        hop.PairedStemExtensionRequest(
            left_arm="GCTA",
            right_arm="TAAC",
            allow_gt_wobble=True,
        )
    )

    assert extension.left_arm == "GCTA"
    assert extension.right_arm == "TAAC"
    assert extension.pair_count.value == 4
    assert tuple(pair.kind for pair in extension.pairs) == (
        hop.JunctionPairKind.WATSON_CRICK,
        hop.JunctionPairKind.HARD_MISMATCH,
        hop.JunctionPairKind.WATSON_CRICK,
        hop.JunctionPairKind.WATSON_CRICK,
    )
    assert extension.watson_crick_count == 3
    assert extension.wobble_count == 0
    assert extension.hard_mismatch_count == 1


def test_paired_stem_extension_rejects_empty_or_unequal_arms() -> None:
    with pytest.raises(ValidationError, match="equal nonzero lengths"):
        hop.PairedStemExtensionRequest(
            left_arm="GCTA",
            right_arm="TAA",
            allow_gt_wobble=True,
        )
    with pytest.raises(ValidationError, match="equal nonzero lengths"):
        hop.PairedStemExtensionRequest(
            left_arm="",
            right_arm="",
            allow_gt_wobble=True,
        )
