"""Evaluate optional paired stem context outside the payload."""

from __future__ import annotations

from hop_design.kernel.stem import classify_paired_stem
from hop_design.models.coordinates import BasePairCount
from hop_design.models.junction import JunctionPairKind
from hop_design.models.stem import PairedStemExtension, PairedStemExtensionRequest


def evaluate_paired_stem_extension(
    request: PairedStemExtensionRequest,
) -> PairedStemExtension:
    """Return literal pair calls for one supplied stem extension."""
    pairs = classify_paired_stem(request)
    return PairedStemExtension(
        left_arm=request.left_arm,
        right_arm=request.right_arm,
        pair_count=BasePairCount(value=len(pairs)),
        pairs=pairs,
        watson_crick_count=sum(pair.kind is JunctionPairKind.WATSON_CRICK for pair in pairs),
        wobble_count=sum(pair.kind is JunctionPairKind.GT_WOBBLE for pair in pairs),
        hard_mismatch_count=sum(pair.kind is JunctionPairKind.HARD_MISMATCH for pair in pairs),
    )


__all__ = ["evaluate_paired_stem_extension"]
