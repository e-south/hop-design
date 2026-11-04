"""Expand explicit method permissions without weakening the executable release contract."""

from typing import Any

from hop_design.models.construction.discovery.request import ScaffoldDiscoveryRequest


def method_conflicts(request: ScaffoldDiscoveryRequest) -> list[dict[str, Any]]:
    methods = request.preparation_changes.release_enzyme_ids
    if methods is None:
        return []
    product = request.product
    if product.release is None or product.basal is None:
        return [
            {
                "requested_field": "preparation_changes.release_enzyme_ids",
                "requested_value": list(methods),
                "inherited_field": "product.endpoint",
                "inherited_value": product.endpoint.value,
                "explicit_edit": "Omit release alternatives for an endpoint without release.",
            }
        ]
    known = {e.enzyme_id for e in product.enzyme_catalog.enzymes}
    conflicts = []
    for enzyme in methods:
        if enzyme not in known:
            conflicts.append(
                {
                    "requested_field": "preparation_changes.release_enzyme_ids",
                    "requested_value": enzyme,
                    "inherited_field": "product.enzyme_catalog",
                    "inherited_value": sorted(known),
                    "explicit_edit": "Supply a characterized definition or remove this method.",
                }
            )
        for role, policy in (
            ("basal", product.basal.enzymes),
            ("release", product.release.enzymes),
        ):
            for field in ("forbidden_enzyme_ids", "reserved_enzyme_ids"):
                values = getattr(policy, field)
                if enzyme in values:
                    conflicts.append(
                        {
                            "requested_field": "preparation_changes.release_enzyme_ids",
                            "requested_value": enzyme,
                            "inherited_field": f"product.{role}.enzymes.{field}",
                            "inherited_value": list(values),
                            "explicit_edit": "Remove this method or explicitly revise "
                            "its conflicting permission.",
                        }
                    )
    return conflicts


def apply_method(value: dict[str, Any], enzyme: str | None) -> list[dict[str, Any]]:
    if enzyme is None:
        return []
    original = value["release"]["enzymes"]["allowed_enzyme_ids"]
    for local in ("basal", "release"):
        policy = value[local]["enzymes"]
        roles = policy["role_restrictions"]
        other_roles = {
            e for r in roles if r["role"] != "end_generation" for e in r["allowed_enzyme_ids"]
        }
        old_ends = {
            e for r in roles if r["role"] == "end_generation" for e in r["allowed_enzyme_ids"]
        }
        remaining = [
            e for e in policy["allowed_enzyme_ids"] if e not in old_ends or e in other_roles
        ]
        policy["allowed_enzyme_ids"] = (
            [enzyme] if local == "release" else list(dict.fromkeys([*remaining, enzyme]))
        )
        policy["role_restrictions"] = [r for r in roles if r["role"] != "end_generation"] + [
            {"role": "end_generation", "allowed_enzyme_ids": [enzyme]}
        ]
    return (
        []
        if original == [enzyme]
        else [
            {
                "field": "product.release.enzymes + product.basal.enzymes.end_generation",
                "before": original,
                "after": [enzyme],
                "permission": "preparation_changes.release_enzyme_ids",
            }
        ]
    )
