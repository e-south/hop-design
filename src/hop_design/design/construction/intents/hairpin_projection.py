"""Project native eligibility into the common choice plot without re-solving controls."""

import json
from typing import Any


def project_hairpin_choices(native: dict[str, Any], option_bytes: bytes) -> dict[str, Any]:
    options = {o["label"]: o for o in json.loads(option_bytes)}
    paths = [
        {
            **path,
            **{
                key: options[path["option_label"]][key]
                for key in ("materialized_realization_id", "molecular_identity", "methods")
            },
            "matches": path["option_label"] in native["compatible_options"],
        }
        for path in native["choice_space"]["paths"]
    ]
    axes = []
    for axis in native["choice_space"]["axes"]:
        # A release-only coordinate is absent for a hairpin, never a fabricated zero.
        if paths and any(p["values"].get(axis["key"]) is None for p in paths):
            continue
        nodes = []
        for value in axis["values"]:
            if value["value"] is None:
                continue
            witnesses = [p for p in paths if p["values"].get(axis["key"]) == value["value"]]
            count = native["choice_space"]["availability"][axis["key"]][str(value["value"])]
            nodes.append(
                {
                    **value,
                    "supported_preparations": len(witnesses),
                    "conditional_preparations": count,
                    "state": "supported"
                    if count
                    else "supported_elsewhere"
                    if witnesses
                    else "unresolved",
                }
            )
        if nodes:
            axes.append({**axis, "nodes": nodes, "domain": axis["declared"]})
    return {"axes": axes, "paths": paths, "matching_preparations": sum(p["matches"] for p in paths)}
