"""Small contextual distributions with explicit preparation denominators."""

from collections import Counter
from typing import Any

from hop_design.models.construction.variants.parameters import parameter_definition


def geometry_distributions(
    paths: list[dict[str, Any]], keys: tuple[str, ...]
) -> list[dict[str, Any]]:
    rows = list({p["materialized_realization_id"]: p for p in paths}.values())
    eligible = [p for p in rows if p["matches"]]
    result = []
    for key in keys:
        definition = parameter_definition(key)
        recorded_counts = Counter(p["values"].get(key) for p in rows)
        eligible_counts = Counter(p["values"].get(key) for p in eligible)
        values = sorted(value for value in recorded_counts if type(value) is int)
        result.append(
            {
                "key": key,
                "label": definition.label,
                "unit": definition.unit,
                "stage": definition.stage,
                "counted": "preparations",
                "denominator": {"recorded": len(rows), "eligible": len(eligible)},
                "missing": {
                    "recorded": len(rows) - sum(recorded_counts[v] for v in values),
                    "eligible": len(eligible) - sum(eligible_counts[v] for v in values),
                },
                "bins": [
                    {
                        "value": value,
                        "recorded": recorded_counts[value],
                        "eligible": eligible_counts[value],
                    }
                    for value in values
                ],
            }
        )
    return result
