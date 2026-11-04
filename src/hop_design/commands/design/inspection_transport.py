"""Private browser columns; the complete public query remains in the session."""

import json
from collections.abc import Iterable
from typing import Any


def _column(values: Iterable[Any]) -> dict[str, Any]:
    dictionary: list[Any] = []
    indices: list[int] = []
    positions: dict[tuple[type | None, Any], int] = {}
    for value in values:
        # Most coordinates are plain words or counts. Keep JSON's distinct
        # scalar types without serializing every repeated value. Composite
        # records and floats retain their existing JSON equivalence rules.
        key = (
            (type(value), value)
            if type(value) in (str, int, bool, type(None))
            else (None, json.dumps(value, sort_keys=True, separators=(",", ":")))
        )
        if key not in positions:
            positions[key] = len(dictionary)
            dictionary.append(value)
        indices.append(positions[key])
    return {"dictionary": dictionary, "indices": indices}


def compact_choices(answer: dict[str, Any]) -> dict[str, Any]:
    paths = answer["paths"]
    members = [p["materialized_realization_id"] for p in paths]
    if len(set(members)) != len(members):
        raise ValueError("Browser cohort requires distinct preparation identities.")
    keys = sorted({key for p in paths for key in p["values"]})
    roles = sorted({key for p in paths for key in p.get("material_roles", {})})
    return {
        "schema": "hop.inspection-cohort/v1",
        "choices": {k: v for k, v in answer.items() if k != "paths"},
        "members": members,
        "matches": [p["matches"] for p in paths],
        "values": {key: _column(p["values"].get(key) for p in paths) for key in keys},
        "methods": _column(p.get("methods", []) for p in paths),
        "roles": {
            key: _column(p.get("material_roles", {}).get(key) for p in paths) for key in roles
        },
    }
