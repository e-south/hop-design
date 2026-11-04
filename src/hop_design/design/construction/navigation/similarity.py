"""Fixed-context molecular dissimilarity without auxiliary-handle enumeration."""

from collections.abc import Sequence
from typing import Any

from hop_design.models.construction.variants.similarity import (
    MolecularComparisonBasis,
    MolecularDescriptor,
    MolecularDissimilarity,
    MolecularDistancePolicy,
)
from hop_design.serialization import canonical_json_bytes


def edit_distance(a: Sequence[Any], b: Sequence[Any]) -> int:
    """Linear-memory edit distance; alignments confer no molecular correspondence."""
    if len(a) < len(b):
        a, b = b, a
    row = list(range(len(b) + 1))
    for i, left in enumerate(a, 1):
        following = [i]
        for j, right in enumerate(b, 1):
            following.append(min(following[-1] + 1, row[j] + 1, row[j - 1] + (left != right)))
        row = following
    return row[-1]


def comparison_basis(
    rows: tuple[MolecularDescriptor, ...],
    *,
    weights: tuple[float, float, float] = (1.0, 1.0, 1.0),
    policy: MolecularDistancePolicy | None = None,
) -> MolecularComparisonBasis:
    """Freeze scales and varying features across the entire edition, before filtering."""
    if not rows or len({r.scope_key for r in rows}) != 1:
        raise ValueError("A molecular comparison needs one supplied-stem and endpoint scope.")
    shapes = [r.compared_shape for r in rows]
    sequences = [r.compared_sequences for r in rows]
    shape = {key: max(r[key] for r in shapes) - min(r[key] for r in shapes) for key in shapes[0]}
    sequence = tuple(
        key
        for key in sorted(sequences[0])
        if len({canonical_json_bytes(r[key]) for r in sequences}) > 1
    )
    interface = tuple(
        key
        for key in sorted(rows[0].interfaces or {})
        if len({(r.interfaces or {})[key] for r in rows}) > 1
    )
    scales = {k: v for k, v in shape.items() if v}
    if policy and policy.numeric_scaling == "declared":
        if set(policy.declared_scales) - shapes[0].keys():
            raise ValueError("Declared scales include a coordinate outside this molecular scope.")
        if any(policy.declared_scales.get(k, 0) < v for k, v in scales.items()):
            raise ValueError(
                "Each varying coordinate needs a declared scale covering its observed range."
            )
        scales = {k: policy.declared_scales[k] for k in scales}
    if policy:
        policy.validate_end_lengths(rows)
    return MolecularComparisonBasis(
        schema="hop.molecular-comparison/v2"
        if rows[0].retained_terminal_bases is not None
        else "hop.molecular-comparison/v1",
        scope_key=rows[0].scope_key,
        comparison_keys=tuple(sorted({r.comparison_key for r in rows})),
        shape_scales=scales,
        sequence_keys=sequence,
        interface_keys=interface,
        weights=weights,
        distance_policy=policy,
    )


def regional_difference(
    edits: int, left_length: int, right_length: int, *, normalized: bool
) -> float:
    if normalized:
        return edits / max(1, left_length, right_length)
    return min(
        1.0,
        max(0, edits - abs(left_length - right_length)) / max(1, min(left_length, right_length)),
    )


def dissimilarity(
    a: MolecularDescriptor, b: MolecularDescriptor, basis: MolecularComparisonBasis
) -> MolecularDissimilarity:
    if a.scope_key != basis.scope_key or b.scope_key != basis.scope_key:
        raise ValueError("Compared molecules must share the declared comparison scope.")
    if (
        a.comparison_key not in basis.comparison_keys
        or b.comparison_key not in basis.comparison_keys
    ):
        raise ValueError("Molecule is outside the declared comparison; create a new edition.")
    a_shape, b_shape = a.compared_shape, b.compared_shape
    a_sequence, b_sequence = a.compared_sequences, b.compared_sequences
    policy = basis.effective_policy
    shape = [abs(a_shape[k] - b_shape[k]) / scale for k, scale in basis.shape_scales.items()]
    sequence = []
    for key in basis.sequence_keys:
        left, right = a_sequence[key], b_sequence[key]
        sequence.append(
            regional_difference(
                edit_distance(left, right),
                len(left),
                len(right),
                normalized=policy.regional_metric == "normalized_edit",
            )
        )
    interface = []
    for name in basis.interface_keys:
        assert a.interfaces is not None and b.interfaces is not None
        x, y = a.interfaces[name], b.interfaces[name]
        if name.endswith("_word"):
            edits = (
                sum(a != b for a, b in zip(x, y, strict=True))
                if policy.end_word_metric == "hamming"
                else edit_distance(x, y)
            )
            interface.append(edits / max(1, len(x), len(y)))
        else:
            interface.append(float(x != y))
    values = [sum(v) / len(v) if v else None for v in (shape, sequence, interface)]
    active = [
        (value, weight)
        for value, weight in zip(values, basis.weights, strict=True)
        if value is not None
    ]
    total = sum(v * w for v, w in active) / sum(w for _, w in active) if active else 0.0
    return MolecularDissimilarity(
        shape=values[0], sequence=values[1], interface=values[2], total=total
    )
