"""Find complete and incomplete comparative groups within an evaluated options pool."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

from hop_design.serialization import canonical_json_bytes, sha256_digest

from ..families.properties import shared_values
from ..packets.publication import SourceBoundConstructionPacket
from ..public import project_hairpin_portrait
from .admission import captured_options
from .intent import read_comparison


@dataclass(frozen=True, init=False, repr=False)
class ConstructionOptionSets(SourceBoundConstructionPacket):
    """Group candidates by exact declared controls; no membership is selected."""

    _packet_schema: ClassVar[str] = "hop.construction-option-sets-packet/v1"


def find_construction_option_sets(
    path: str | Path, comparison: str | Path
) -> ConstructionOptionSets:
    """Find compatible backgrounds without changing requests or launching more search."""
    request, request_root = read_comparison(comparison)
    groups: dict[str, dict[str, Any]] = {}
    with captured_options(path) as (_, pool, receipts, protected):
        for option in pool["options"]:
            matches = [
                m.name
                for m in request.members
                if all(option["geometry"][k] == v for k, v in m.dimensions.items())
            ]
            if not matches:
                continue
            portrait = project_hairpin_portrait(
                receipts[option["label"]],
                materialized_realization_id=option["materialized_realization_id"],
            )
            data = json.loads(portrait.json_bytes)
            values = shared_values(data, request.shared_properties)
            shared = {k: values[k] for k in request.shared_properties}
            # Stage and endpoint are unconditional: unlike products never form one set.
            key = sha256_digest(
                canonical_json_bytes([data["state"]["phase"], data["endpoint"], shared])
            )
            group = groups.setdefault(
                key,
                {
                    "group_id": key,
                    "shared_values": shared,
                    "members": [
                        {"name": m.name, "dimensions": m.dimensions, "option_labels": []}
                        for m in request.members
                    ],
                },
            )
            for member in group["members"]:
                if member["name"] in matches:
                    member["option_labels"].append(option["label"])
        for group in groups.values():
            group["missing_members"] = [
                m["name"] for m in group["members"] if not m["option_labels"]
            ]
            group["comparison_available"] = not group["missing_members"]
        summary = {
            "schema": "hop.construction-option-sets/v1",
            "request": request.model_dump(mode="json", by_alias=True),
            "options_request_digest": pool["request_digest"],
            "coverage": pool["coverage"],
            "local_coverage": pool["local_coverage"],
            "groups": list(groups.values()),
            "selected_options": [],
            "complete_group_count": sum(g["comparison_available"] for g in groups.values()),
            "scope": "evaluated_options_only",
        }
    lines = [
        "# Find a controlled scaffold set",
        "",
        f"{summary['complete_group_count']} complete shared backgrounds in the evaluated pool.",
        "No group or preparation has been selected.",
        "",
        "Choose one option label per member; use select-options with these controls.",
        "",
    ]
    for index, group in enumerate(groups.values(), start=1):
        lines += [
            f"## Background {index}",
            "",
            "All requested members available."
            if group["comparison_available"]
            else "Missing in this background: " + ", ".join(group["missing_members"]),
            "",
        ]
        values = group["shared_values"]
        for key, label in (
            ("loop_side_paired_bp", "Loop-side extension (bp)"),
            ("open_side_paired_positions", "Open-side paired positions"),
        ):
            if key in values:
                lines.append(f"{label}: {values[key]}")
        for member in group["members"]:
            lines.append(
                f"- {member['name']}: " + (", ".join(member["option_labels"]) or "not obtained")
            )
        lines.append("")
    lines += [
        "Missing members are absent from this evaluated pool, not proven impossible.",
        "Retained coverage includes unexamined pairs and local search limits.",
        "",
    ]
    packet = ConstructionOptionSets._create(
        {"comparison.json": canonical_json_bytes(request)}, summary, "\n".join(lines)
    )
    object.__setattr__(packet, "_roots", (protected, request_root))
    return packet
