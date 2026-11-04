"""Translate approved molecular edits into context declarations and explicit dependencies."""

from copy import deepcopy
from typing import Any

from hop_design.models.construction.intents.revision import (
    CONTEXT_PARAMETER_FIELDS,
    DesignPermissionRevision,
)
from hop_design.models.enzymes import CharacterizedEnzymeCatalog, EnzymeProvisioningPolicy
from hop_design.serialization import canonical_json_bytes

from .methods import METHOD_ROLES, resolve_method_ids


def revise_context(
    context: dict[str, Any], revision: DesignPermissionRevision
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, str]]]:
    revised = deepcopy(context)
    changes: list[dict[str, Any]] = []
    conflicts: list[dict[str, str]] = []

    def change(path: str, value: Any, label: str) -> None:
        parent = revised
        for key in path.split(".")[:-1]:
            if not isinstance(parent.get(key), dict):
                conflicts.append(
                    {"field": path, "message": f"{label} does not apply to this product."}
                )
                return
            parent = parent[key]
        key = path.split(".")[-1]
        if parent.get(key) != value:
            changes.append(
                {"path": path, "label": label, "before": deepcopy(parent.get(key)), "after": value}
            )
            parent[key] = value

    for parameter in revision.parameters:
        key = "foldback_arm_bp" if parameter.key == "loop_side_paired_bp" else parameter.key
        field = CONTEXT_PARAMETER_FIELDS[key]
        values: list[int | str]
        if parameter.values is not None:
            values = list(parameter.values)
        else:
            assert parameter.minimum is not None and parameter.maximum is not None
            values = list(range(parameter.minimum, parameter.maximum + 1))
        value: Any
        if field.kind == "choice":
            if len(values) != 1:
                conflicts.append(
                    {
                        "field": field.path,
                        "message": "Choose one strand permission, including 'any' where supported.",
                    }
                )
                continue
            value = values[0]
        else:
            value = values
        change(field.path.removeprefix("product."), value, field.label)
    if revision.end_placements is not None:
        if revised["product"] != "released_insert":
            conflicts.append(
                {"field": "end_placements", "message": "End placements require a released insert."}
            )
        else:
            change(
                "placements",
                [p.model_dump(mode="json") for p in revision.end_placements],
                "Joint end-to-stem placements",
            )
    for region, value in revision.retained_limits_nt.model_dump(exclude_none=True).items():
        change(
            f"{region}.max_retained_overhead_nt",
            value,
            f"{region.title()} retained-construction limit (nt)",
        )
    entries = {entry["enzyme_id"]: entry for entry in revised["enzyme_catalog"]["enzymes"]}
    for enzyme in revision.add_enzymes:
        entry = enzyme.model_dump(mode="json", by_alias=True)
        if enzyme.enzyme_id in entries and entries[enzyme.enzyme_id] != entry:
            conflicts.append(
                {
                    "field": "add_enzymes",
                    "message": (
                        f"Characterization identity {enzyme.enzyme_id} "
                        "already has another definition."
                    ),
                }
            )
        else:
            entries[enzyme.enzyme_id] = entry
    change("enzyme_catalog.enzymes", list(entries.values()), "Characterized enzyme definitions")
    catalog = CharacterizedEnzymeCatalog.model_validate_json(
        canonical_json_bytes(revised["enzyme_catalog"])
    )
    for role, purpose in METHOD_ROLES.items():
        names = getattr(revision.methods, role)
        if names is None:
            continue
        job = revised.get(role)
        if not isinstance(job, dict):
            conflicts.append(
                {"field": f"methods.{role}", "message": f"This product has no {role} method."}
            )
            continue
        # Name resolution is shared with ordinary intent. This lookup policy
        # consults characterized definitions; applying permissions happens below.
        lookup = EnzymeProvisioningPolicy(
            catalog=catalog,
            allowed_enzyme_ids=(),
            forbidden_enzyme_ids=(),
            reserved_enzyme_ids=(),
            role_restrictions=(),
        )
        try:
            selected = list(resolve_method_ids(names, role=role, policy=lookup))
        except ValueError as error:
            conflicts.append(
                {
                    "field": f"methods.{role}",
                    "message": (
                        f"Provide an unambiguous characterized enzyme in add_enzymes. {error}"
                    ),
                }
            )
            continue
        for owner in ("basal", "release") if role == "release" else (role,):
            policy = revised[owner]["enzymes"]
            prohibited = set(policy["forbidden_enzyme_ids"]) | set(policy["reserved_enzyme_ids"])
            if prohibited.intersection(selected):
                conflicts.append(
                    {
                        "field": f"{owner}.enzymes",
                        "message": (
                            "Requested method remains forbidden or reserved; "
                            "revise that policy explicitly."
                        ),
                    }
                )
                continue
            if policy["allowed_enzyme_ids"]:
                change(
                    f"{owner}.enzymes.allowed_enzyme_ids",
                    sorted(set(policy["allowed_enzyme_ids"]) | set(selected)),
                    f"{owner.title()} available enzymes",
                )
            roles = [r for r in policy["role_restrictions"] if r["role"] != purpose.value]
            roles.append({"role": purpose.value, "allowed_enzyme_ids": selected})
            change(f"{owner}.enzymes.role_restrictions", roles, f"{owner.title()} enzyme roles")
    return revised, changes, conflicts
