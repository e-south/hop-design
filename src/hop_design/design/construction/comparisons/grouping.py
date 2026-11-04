"""Bounded, reference-free assignment of verified options to required member slots."""

from collections import Counter
from itertools import product
from math import prod
from typing import Any

from hop_design.models.construction.comparisons.request import (
    ComparisonAssessmentRequest,
    RequiredComparisonMember,
    SequenceComparisonMember,
    resolved_stage_controls,
)
from hop_design.serialization import canonical_json_bytes, sha256_digest

from .controls import assess_stage_controls
from .relationships import relationship_rejection


def member_option_labels(
    member: RequiredComparisonMember, options: list[dict[str, Any]]
) -> list[str]:
    """One selector authority for assessment and missing-member explanations."""
    return sorted(
        o["label"]
        for o in options
        if all(o["geometry"][k] == v for k, v in member.dimensions.items())
        and (
            not isinstance(member, SequenceComparisonMember)
            or member.loop_sequence is None
            or member.loop_sequence == o["loop_sequence"]
        )
        and (member.release_enzyme_id is None or o["release_enzyme_id"] == member.release_enzyme_id)
    )


def evaluate_groups(
    brief: ComparisonAssessmentRequest,
    options: list[dict[str, Any]],
    references: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ordered = sorted(brief.required_members, key=lambda member: member.name)
    members: list[dict[str, Any]] = [
        {
            "name": member.name,
            "dimensions": member.dimensions,
            "release_enzyme_id": member.release_enzyme_id,
            **(
                {"loop_sequence": member.loop_sequence}
                if isinstance(member, SequenceComparisonMember) and member.loop_sequence is not None
                else {}
            ),
            "option_labels": member_option_labels(member, options),
        }
        for member in ordered
    ]
    for member in members:
        member["status"] = (
            "options_available" if member["option_labels"] else "missing_from_evaluated_pool"
        )
    by_label = {o["label"]: o for o in options}
    total = prod(len(m["option_labels"]) for m in members) if members else 0
    sets: list[dict[str, Any]] = []
    rejected: Counter[str] = Counter()
    evaluated = 0
    stage = brief.comparison_stage
    controls = resolved_stage_controls(brief)
    control_examples: list[dict[str, Any]] = []
    for labels in product(*(m["option_labels"] for m in members)) if members else ():
        if evaluated >= brief.max_group_evaluations or len(sets) >= brief.max_sets:
            break
        evaluated += 1
        chosen = [by_label[label] for label in labels]
        observations = assess_stage_controls(
            controls,
            {m["name"]: o.get("stage_facts", {}) for m, o in zip(members, chosen, strict=True)},
        )
        reason = None
        if len({o["materialized_realization_id"] for o in chosen}) != len(chosen):
            reason = "repeated_preparation"
        elif any(o.get("prior_material_conflicts") for o in chosen):
            reason = "prior_material_policy_conflict"
        elif any(
            any(o["shared_values"][k] != chosen[0]["shared_values"][k] for o in chosen)
            for k in brief.shared_properties
        ):
            reason = "shared_property_mismatch"
        elif any(
            any(role not in o["material_roles"] for o in chosen)
            for role in brief.preserve_material_roles
        ):
            reason = "required_material_role_absent"
        elif any(
            len({o["material_roles"][role]["material_id"] for o in chosen}) != 1
            for role in brief.preserve_material_roles
        ):
            reason = "preserved_material_changed"
        else:
            reason = relationship_rejection(
                brief, {m["name"]: o for m, o in zip(members, chosen, strict=True)}, references
            )
        if reason is None and any(c["status"] != "shared" for c in observations):
            reason = (
                "stage_control_unassessed"
                if any(c["status"] == "unassessed" for c in observations)
                else "stage_control_mismatch"
            )
        if reason:
            rejected[reason] += 1
            if controls and reason.startswith("stage_control_") and len(control_examples) < 8:
                control_examples.append(
                    {
                        "members": {
                            m["name"]: label for m, label in zip(members, labels, strict=True)
                        },
                        "controls": observations,
                    }
                )
            continue
        membership = {m["name"]: label for m, label in zip(members, labels, strict=True)}
        sets.append(
            {
                "label": f"set-{len(sets) + 1:04d}",
                "set_id": sha256_digest(canonical_json_bytes(membership)),
                "members": membership,
                **({"stage_controls": observations} if controls else {}),
                "shared_values": {
                    k: chosen[0]["shared_values"][k] for k in brief.shared_properties
                },
                "molecular_identities": {
                    m["name"]: o["molecular_identity"][stage]
                    for m, o in zip(members, chosen, strict=True)
                },
            }
        )
    return {
        "members": members,
        "sets": sets,
        **(
            {"stage_control_examples": control_examples, "stage_control_example_limit": 8}
            if controls
            else {}
        ),
        "group_coverage": {
            "possible_assignments": total,
            "evaluated_assignments": evaluated,
            "unexamined_assignments": total - evaluated,
            "max_group_evaluations": brief.max_group_evaluations,
            "max_sets": brief.max_sets,
            "completion": "evaluated_pool_exhausted" if evaluated == total else "stopped_by_bound",
            "rejections": dict(sorted(rejected.items())),
        },
    }
