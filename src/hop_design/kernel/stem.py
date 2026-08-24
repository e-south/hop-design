"""Pure pairing mechanics for optional non-payload stem context."""

from __future__ import annotations

from hop_design.models.junction import JunctionPairObservation, classify_literal_pair
from hop_design.models.stem import PairedStemExtensionRequest


def classify_paired_stem(
    request: PairedStemExtensionRequest,
) -> tuple[JunctionPairObservation, ...]:
    """Classify every antiparallel pair without applying caller policy."""
    pairs: list[JunctionPairObservation] = []
    for left_index, left_base in enumerate(request.left_arm):
        right_index = len(request.right_arm) - 1 - left_index
        right_base = request.right_arm[right_index]
        kind = classify_literal_pair(left_base=left_base, right_base=right_base)
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
