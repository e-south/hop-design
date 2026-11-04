"""Shared conditional predicates over complete preparations, with no new search."""

from typing import Any

from hop_design.models.construction.variants.parameters import ParameterSelection


def selection_reasons(
    values: dict[str, Any], selections: tuple[ParameterSelection, ...]
) -> list[dict[str, Any]]:
    return [
        {
            "kind": "parameter_constraint",
            "parameter": selection.key,
            "observed": values.get(selection.key),
            "status": "unassessed" if values.get(selection.key) is None else "different",
        }
        for selection in selections
        if not selection.accepts(values.get(selection.key))
    ]


def conditional_availability(
    paths: list[dict[str, Any]],
    axes: list[dict[str, Any]],
    selections: tuple[ParameterSelection, ...],
) -> dict[str, dict[str, int]]:
    availability = {}
    for axis in axes:
        counts = {
            ("null" if entry["value"] is None else str(entry["value"])): 0
            for entry in axis["values"]
        }
        for path in paths:
            if all(
                s.key == axis["key"] or s.accepts(path["values"].get(s.key)) for s in selections
            ):
                value = path["values"].get(axis["key"])
                key = "null" if value is None else str(value)
                counts[key] = counts.get(key, 0) + 1
        availability[axis["key"]] = counts
    return availability


def domain_marks(domain: dict[str, Any]) -> set[int | str]:
    """Sparse integer ticks expose unobserved interiors; brushing retains the full domain."""
    marks = set(domain.get("values", []))
    intervals = domain.get("intervals", [domain] if "minimum" in domain else [])
    for interval in intervals:
        low, high = interval["minimum"], interval["maximum"]
        steps = min(6, high - low)
        marks.update(
            low + (high - low) * i // steps for i in range(steps + 1)
        ) if steps else marks.add(low)
    return marks
