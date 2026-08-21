"""Pure pairing mechanics for optional non-payload stem context."""

from __future__ import annotations

from hop_design.models.junction import JunctionPairKind, JunctionPairObservation
from hop_design.models.sequence import reverse_complement_iupac
from hop_design.models.stem import PairedStemExtensionRequest


def classify_paired_stem(
    request: PairedStemExtensionRequest,
) -> tuple[JunctionPairObservation, ...]:
    """Classify every antiparallel pair without applying caller policy."""
    pairs: list[JunctionPairObservation] = []
    for left_index, left_base in enumerate(request.left_arm):
        right_index = len(request.right_arm) - 1 - left_index
        right_base = request.right_arm[right_index]
        if left_base == reverse_complement_iupac(right_base):
            kind = JunctionPairKind.WATSON_CRICK
        elif request.allow_gt_wobble and (left_base, right_base) in {
            ("G", "T"),
            ("T", "G"),
        }:
            kind = JunctionPairKind.GT_WOBBLE
        else:
            kind = JunctionPairKind.HARD_MISMATCH
        pairs.append(
            JunctionPairObservation(
                left_index=left_index,
                right_index=right_index,
                left_base=left_base,
                right_base=right_base,
                kind=kind,
            )
        )
    return tuple(pairs)


__all__ = ["classify_paired_stem"]
