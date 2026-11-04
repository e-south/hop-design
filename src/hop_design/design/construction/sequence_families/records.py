"""Required membership and per-member coverage, independent of successful display order."""

from typing import Any


def family_summary(
    preview: dict[str, Any], records: dict[str, dict[str, Any]], producer: dict[str, Any]
) -> dict[str, Any]:
    members, options = [], []
    for member in preview["members"]:
        name = member["name"]
        record = records[name]
        labels = []
        for option in record.get("options", []):
            label = f"{name}-{option['label']}"
            prefix = f"members/{name}/"
            labels.append(label)
            options.append(
                {
                    **option,
                    "label": label,
                    "member": name,
                    "selection": {k: prefix + v for k, v in option["selection"].items()},
                    **{
                        k: prefix + option[k]
                        for k in ("portrait", "closing_drawing", "product_stages", "preparation")
                    },
                    "sequence_view": f"views/{label}.json",
                    "sequence_drawing": f"views/{label}.svg",
                }
            )
        members.append(
            {
                **member,
                "option_labels": labels,
                "status": "complete_options" if labels else "no_complete_option_examined",
                "coverage": record.get("coverage"),
                "conflicts": record.get("conflicts", []),
                "report": f"members/{name}/report.md",
            }
        )
    return {
        "schema": "hop.sequence-family-result/v1",
        "request_digest": preview["request_digest"],
        "producer": producer,
        "members": members,
        "options": options,
        "missing_members": [m["name"] for m in members if not m["option_labels"]],
        "shared_properties": preview["shared_properties"],
        "shared_material_roles": preview["shared_material_roles"],
        "shared_controls_status": "require_explicit_selection",
        "selected_members": [],
        "pooled_library": "not_assessed",
        "global_feasibility": "not_assessed",
    }
