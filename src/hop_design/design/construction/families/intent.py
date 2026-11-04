"""Explain the effective family request in product and material-policy vocabulary."""

from hop_design.export.construction.labels import endpoint_label
from hop_design.models.construction.family.request import ConstructionFamilyRequest


def comparison_intent(family: ConstructionFamilyRequest) -> dict[str, object]:
    base = family.base_request
    return {
        "endpoint": base.endpoint.value,
        "authored_dimensions": sorted(
            {
                d
                for m in family.members
                for d in ("loop_nt", "loop_side_paired_bp")
                if getattr(m, d) is not None
            }
        ),
        "shared_properties": list(family.shared_properties),
        "materials": base.materialization.model_dump(mode="json", by_alias=True),
        "requirements": base.whole_route_constraints.hairpin_scaffold.model_dump(mode="json")
        if base.whole_route_constraints.hairpin_scaffold
        else None,
        "editable_dimensions": ["loop_nt", "loop_side_paired_bp"],
        "open_side_extent": (
            "achieved/shared property; not an independently editable family dimension"
        ),
    }


def render_comparison_intent(family: ConstructionFamilyRequest) -> list[str]:
    intent = comparison_intent(family)
    rows = [
        "Product: " + endpoint_label(family.base_request.endpoint) + ".",
        "Shared requirements: " + ", ".join(family.shared_properties) + ".",
        "",
        "Material changes permitted by the authored policies:",
    ]
    materials = family.base_request.materialization.model_dump(mode="json", by_alias=True)
    for group, policies in materials.items():
        if not isinstance(policies, dict):
            continue
        for role, policy in policies.items():
            if not isinstance(policy, dict) or "mode" not in policy:
                continue
            mode = policy["mode"]
            meaning = {
                "fixed": "exact supplied sequence and chemistry retained",
                "constrain": "changes only within supplied constraints",
                "derive": "derive from each member's construction",
            }[mode]
            rows.append(f"- {group.replace('_', ' ')} / {role.replace('_', ' ')}: {meaning}.")
    rows += ["", "Open-side extent: " + str(intent["open_side_extent"]) + ".", ""]
    return rows
