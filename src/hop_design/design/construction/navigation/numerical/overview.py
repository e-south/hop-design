"""Read distances from the same declared fields used by a recorded overview."""

from typing import Any, cast

from hop_design.models.construction.variants.overview import (
    PreparationDissimilarity,
    PreparationOverview,
)
from hop_design.models.construction.variants.similarity import ShapeKey

from ..similarity import edit_distance


def overview_difference(
    overview: PreparationOverview, left: int, right: int
) -> PreparationDissimilarity:
    groups: dict[str, list[float]] = {
        key: [] for key in ("shape", "sequence", "interface", "processing")
    }
    for column in overview.columns:
        block, key = column.key.split(".")
        a: Any = column.dictionary[column.indices[left]]
        b: Any = column.dictionary[column.indices[right]]
        if block == "shape":
            value = abs(a - b) / overview.basis.shape_scales[cast(ShapeKey, key)]
        elif block == "sequences":
            value = edit_distance(a, b) / max(1, len(a), len(b))
        elif block == "interfaces" and key.endswith("_word"):
            value = sum(x != y for x, y in zip(a, b, strict=True)) / len(a)
        else:
            value = float(a != b)
        groups[{"sequences": "sequence", "interfaces": "interface"}.get(block, block)].append(value)
    means = {key: sum(values) / len(values) if values else None for key, values in groups.items()}
    active = [
        (means[key], weight)
        for key, weight in zip(groups, overview.basis.weights, strict=True)
        if means[key] is not None
    ]
    total = sum(cast(float, value) * weight for value, weight in active) / sum(
        weight for _, weight in active
    )
    return PreparationDissimilarity(**means, total=total)
