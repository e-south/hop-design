"""Locate contradictory declarations before narrowing a family member's request."""

from typing import Any

from hop_design.models.construction.family.request import (
    ConstructionFamilyRequest,
    ScaffoldFamilyMember,
)

DIMENSIONS = (("loop_nt", "loop_lengths_nt"), ("loop_side_paired_bp", "annealing_arm_lengths_bp"))


def member_conflicts(
    family: ConstructionFamilyRequest, member: ScaffoldFamilyMember
) -> list[dict[str, Any]]:
    conflicts = []
    for dimension, local in DIMENSIONS:
        value = getattr(member, dimension)
        if value is None:
            continue
        domain = getattr(family.base_request.foldback.geometry, local)
        required = getattr(
            family.base_request.whole_route_constraints.hairpin_scaffold, dimension, None
        )
        declarations = []
        if domain and value not in domain:
            declarations.append(
                (
                    f"base_request.foldback.geometry.{local}",
                    list(domain),
                    f"{dimension}={value} does not intersect authored {local}={list(domain)}.",
                    f"Explicitly include {value} in geometry_permissions.{dimension}.",
                )
            )
        if required is not None and not required.contains(value):
            declarations.append(
                (
                    f"base_request.whole_route_constraints.hairpin_scaffold.{dimension}",
                    required.model_dump(mode="json"),
                    f"{dimension}={value} conflicts with the base hard requirement.",
                    f"Explicitly revise requirements.{dimension}; preserve other requirements.",
                )
            )
        for path, declared, message, edit in declarations:
            conflicts.append(
                {
                    "dimension": dimension,
                    "requested": value,
                    "declared": declared,
                    "declaration_path": path,
                    "member_path": f"members[{member.name}].{dimension}",
                    "message": message,
                    "edit_options": [
                        f"Retain the declaration and revise member {member.name}'s {dimension}.",
                        edit,
                    ],
                }
            )
    return conflicts
