"""Evaluate family agreement without confusing a missing product with a matching one."""

from collections.abc import Mapping, Sequence
from typing import Any, get_args

from hop_design.models.construction.family.controls import ComparisonControl
from hop_design.models.construction.family.request import SharedProperty


def assess_controls(
    values: Mapping[str, dict[str, Any] | None],
    reference: str | None,
    required: Sequence[str],
) -> tuple[ComparisonControl, ...]:
    baseline = values.get(reference) if reference is not None else None
    checks = []
    for key in get_args(SharedProperty.__value__):
        if (
            key == "non_stem_sequences"
            and key not in required
            and not any(v is not None and key in v for v in values.values())
        ):
            continue
        missing = []
        different = []
        for name, member in values.items():
            if (
                baseline is None
                or member is None
                or baseline.get(key) is None
                or member.get(key) is None
            ):
                missing.append(name)
            elif member[key] != baseline[key]:
                different.append(name)
        is_required = key in required
        checks.append(
            ComparisonControl(
                property=key,
                required=is_required,
                reference=reference,
                members=tuple(values),
                status=(
                    "different"
                    if different
                    else "not_assessed"
                    if missing or len(values) < 2
                    else "required_and_verified"
                    if is_required
                    else "observed_agreement"
                ),
                differing_members=tuple(different),
                unassessed_members=tuple(missing),
            )
        )
    return tuple(checks)
