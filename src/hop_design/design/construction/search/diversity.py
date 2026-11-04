"""Shared diversity class accounting; molecular search remains endpoint-owned."""

from collections import defaultdict
from typing import Any

from hop_design.models.construction.variants.objective import DesignSearchObjective
from hop_design.models.construction.variants.parameters import parameter_definition
from hop_design.serialization import canonical_json_bytes, sha256_digest


def diversity_class(objective: DesignSearchObjective, values: dict[str, Any]) -> str:
    """One exact class in the requested dimensions, never a preparation count."""
    if any(values.get(key) is None for key in objective.parameters):
        raise ValueError("Diversity class requires every requested coordinate.")
    return sha256_digest(canonical_json_bytes({key: values[key] for key in objective.parameters}))


def allocation_classes(
    objective: DesignSearchObjective, values: dict[str, Any], *, allow_unknown: bool = False
) -> tuple[str | None, ...]:
    """Prioritize structural contrasts, then exact words, under one objective.

    An unknown loop word still has a known length in its geometry. That length
    partitions allocation without replacing exact-word diversity accounting.
    Unknown candidate coordinates are not evidence of either novelty or absence.
    """
    parameters = objective.parameters
    structural = tuple("loop_nt" if key == "loop_word" else key for key in parameters)
    levels = (parameters,) if structural == parameters else (structural, parameters)
    result: list[str | None] = []
    for level in levels:
        if any(values.get(key) is None for key in level):
            if not allow_unknown:
                raise ValueError("Allocation feedback requires every achieved coordinate.")
            result.append(None)
        else:
            result.append(sha256_digest(canonical_json_bytes({key: values[key] for key in level})))
    return tuple(result)


def stratified_costs(
    rows: list[dict[str, Any]], costs: tuple[int, ...], parameters: tuple[str, ...]
) -> tuple[int, ...]:
    # Unknown sequence coordinates cannot establish sameness or diversity yet.
    # Keep the existing costs until admission supplies their actual values.
    keys = tuple(
        key for key in parameters if rows and all(row.get(key) is not None for row in rows)
    )
    if not keys:
        return costs
    groups: dict[tuple[Any, ...], list[int]] = defaultdict(list)
    for index, row in enumerate(rows):
        groups[tuple(row[key] for key in keys)].append(index)
    result = [0] * len(rows)
    for indices in groups.values():
        # Introduce one representative of each requested class before revisiting
        # that class with different unrequested coordinates. Ties are canonical.
        for rank, index in enumerate(sorted(indices, key=lambda i: (costs[i], i))):
            result[index] = rank
    return tuple(result)


def diversity_summary(
    objective: DesignSearchObjective, paths: list[dict[str, Any]]
) -> dict[str, Any]:
    def signature(path: dict[str, Any]) -> tuple[Any, ...]:
        if any(path["values"].get(key) is None for key in objective.parameters):
            raise ValueError("Diversity accounting requires an achieved value for every dimension.")
        return tuple(path["values"].get(key) for key in objective.parameters)

    signatures = {signature(path) for path in paths}
    return {
        **objective.model_dump(mode="json"),
        "target_policy": objective.target_policy,
        "dimensions": [
            parameter_definition(key).model_dump(mode="json") for key in objective.parameters
        ],
        "observed_classes": len(signatures),
        "matching_classes": len({signature(p) for p in paths if p.get("matches", True)}),
        "scope": "complete_recorded_preparations; unobserved_classes_remain_unresolved",
    }
