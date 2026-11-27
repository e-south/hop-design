"""
--------------------------------------------------------------------------------
HOP Design
hop-design/src/hop_design/export/construction/survey/comparison_trace.py

Project the saved X columns into read-only parallel coordinates.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from collections import Counter
from typing import Any

from hop_design.serialization import canonical_json_bytes, sha256_digest


def comparison_trace_choices(choices: dict[str, Any], packet: dict[str, Any]) -> dict[str, Any]:
    """Use the same ordered fields and dictionaries as X, without changing query inputs."""
    columns = {c["key"]: c for c in packet["columns"] if c["active"]}
    if not columns:
        return choices
    order = packet.get("presentation", {}).get("display_order", list(columns))
    if len(set(order)) != len(order) or set(order) != set(columns):
        raise ValueError("Comparison trace order must name every active X field once.")
    paths = choices["paths"]
    axes: list[dict[str, Any]] = []
    values = [dict(p["values"]) for p in paths]
    definitions = {a["key"]: a for a in choices["axes"]}
    for key in order:
        column = columns[key]
        indices, dictionary = column["indices"], column["dictionary"]
        if len(indices) != len(paths) or any(
            type(i) is not int or not 0 <= i < len(dictionary) for i in indices
        ):
            raise ValueError("Comparison trace dictionary disagrees with its members.")
        numeric = key.startswith("shape.")
        parameters = column.get("parameters", [])
        original: dict[str, Any] = next(
            (definitions[p] for p in parameters if p in definitions), {}
        )
        names = {n["value"]: n["label"] for n in original.get("nodes", [])}
        counts = Counter(indices)
        matching = Counter(i for p, i in zip(paths, indices, strict=True) if p["matches"])
        nodes = []
        for index, value in enumerate(dictionary):
            if not counts[index]:
                continue
            lines = None
            if key in {"sequences.basal_pairs", "sequences.foldback_pairs"}:
                contacts = (
                    [packet["contacts"][i] for i in value]
                    if column.get("encoding") == "contacts"
                    else value
                )
                lines = ["".join(c[i] for c in contacts) or "∅" for i in (0, 1)]
                label = ", ".join(":".join(c) for c in contacts) or "No contacts"
            elif key.startswith("processing.") and isinstance(value, list):
                label = " + ".join(str(names.get(v, v)) for v in value)
            elif isinstance(value, list):
                label = "".join(value) or "∅"
            else:
                label = str(names.get(value, value))
            nodes.append(
                {
                    "value": value if numeric else index,
                    "label": label,
                    **({"display_lines": lines} if lines else {}),
                    "state": "supported",
                    "supported_preparations": counts[index],
                    "conditional_preparations": matching[index],
                }
            )
        for member, index in enumerate(indices):
            values[member][key] = dictionary[index] if numeric else index
        axes.append(
            {
                "key": key,
                "canonical_key": key,
                "label": column["label"],
                "heading_label": column["label"],
                "unit": column.get("unit", ""),
                "kind": "numeric" if numeric else "categorical",
                "representation": "span" if numeric else "sequence",
                "measurement": column.get("definition", column["label"]),
                "symbol": f"x{len(axes) + 1}",
                "design_role": "product",
                "neighborhood": original.get("neighborhood", "whole"),
                "parameters": parameters,
                "read_only": True,
                "domain": {"basis": "observed_only"},
                "nodes": nodes,
            }
        )
    return {
        **choices,
        "axes": axes,
        "comparison_trace": sha256_digest(canonical_json_bytes(packet)),
        "paths": [{**p, "values": v} for p, v in zip(paths, values, strict=True)],
    }
