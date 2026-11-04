"""Compile named molecular obligations into deterministic, permission-bounded tasks."""

import json
from collections.abc import Callable
from typing import Any

from hop_design.models.construction.discovery.request import ScaffoldDiscoveryRequest
from hop_design.models.construction.discovery.targets import ScaffoldSearchTarget
from hop_design.serialization import canonical_json_bytes, sha256_digest

type BranchCompiler = Callable[
    [ScaffoldDiscoveryRequest], tuple[list[dict[str, Any]], list[dict[str, Any]]]
]


def canonical_targets(request: ScaffoldDiscoveryRequest) -> list[dict[str, Any]]:
    unique = {canonical_json_bytes(t): t.model_dump(mode="json") for t in request.required_targets}
    return [
        {"target_id": sha256_digest(key), **value}
        for key, value in sorted(
            unique.items(),
            key=lambda item: (
                -(
                    len(item[1]["dimensions"])
                    + (item[1]["loop_sequence"] is not None)
                    + (item[1]["release_enzyme_id"] is not None)
                    + (item[1].get("end_placement") is not None)
                    + (item[1].get("basal_nick_enzyme_id") is not None)
                ),
                item[0],
            ),
        )
    ]


def narrow_target(
    request: ScaffoldDiscoveryRequest, target: ScaffoldSearchTarget
) -> ScaffoldDiscoveryRequest:
    value = request.model_dump(mode="json", by_alias=True, exclude={"required_targets"})
    geometry = value["product"]["foldback"]["geometry"]
    scaffold = value["scaffold"] or {}
    inherited = value["product"]["whole_route_constraints"].get("hairpin_scaffold") or {}
    dimensions: dict[str, int] = {str(k): v for k, v in target.dimensions.items()}
    for name, required_number in target.dimensions.items():
        for declarations in (scaffold, inherited):
            interval = declarations.get(name)
            if (
                interval is not None
                and not interval["minimum"] <= required_number <= interval["maximum"]
            ):
                raise ValueError(f"Target {name} lies outside a declared hard range.")
        scaffold[name] = {"minimum": required_number, "maximum": required_number}
    for dimension, field, floor in (
        ("loop_nt", "loop_lengths_nt", geometry["minimum_loop_length_nt"]),
        (
            "loop_side_paired_bp",
            "annealing_arm_lengths_bp",
            geometry["minimum_annealing_arm_length_bp"],
        ),
    ):
        number = dimensions.get(dimension)
        if number is None:
            continue
        if number < floor or (geometry[field] and number not in geometry[field]):
            raise ValueError(f"Target {dimension} lies outside permitted geometry.")
        geometry[field] = [number]
    if target.loop_sequence is not None:
        word = target.loop_sequence
        words, lengths = geometry.get("loop_sequences"), geometry["loop_lengths_nt"]
        if (words is not None and word not in words) or (lengths and len(word) not in lengths):
            raise ValueError("Target loop word lies outside the permitted word/length domain.")
        geometry.update(loop_sequences=[word], loop_lengths_nt=[len(word)])
    elif geometry.get("loop_sequences") is not None:
        geometry["loop_sequences"] = [
            w
            for w in geometry["loop_sequences"]
            if not geometry["loop_lengths_nt"] or len(w) in geometry["loop_lengths_nt"]
        ]
    if target.release_enzyme_id is not None:
        methods = request.preparation_changes.release_enzyme_ids
        if methods is None:
            methods = (
                ()
                if request.product.release is None
                else request.product.release.enzymes.allowed_enzyme_ids
            )
        if target.release_enzyme_id not in methods:
            raise ValueError("Target release method is not permitted.")
        value["preparation_changes"]["release_enzyme_ids"] = [target.release_enzyme_id]
    if target.end_placement is not None:
        if request.end_placements is None or target.end_placement not in request.end_placements:
            raise ValueError("Target end placement is not permitted.")
        value["end_placements"] = [target.end_placement.model_dump(mode="json")]
    if target.basal_nick_enzyme_id is not None:
        if target.basal_nick_enzyme_id not in (
            request.preparation_changes.basal_nick_enzyme_ids or ()
        ):
            raise ValueError("Target basal nickase is not permitted.")
        value["preparation_changes"]["basal_nick_enzyme_ids"] = [target.basal_nick_enzyme_id]
    value["scaffold"] = scaffold or None
    return ScaffoldDiscoveryRequest.model_validate_json(json.dumps(value))


def target_plan(
    request: ScaffoldDiscoveryRequest, compile_branches: BranchCompiler
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    targets = canonical_targets(request)
    tasks: dict[str, dict[str, Any]] = {}
    conflicts = []
    for selector in targets:
        try:
            target = ScaffoldSearchTarget.model_validate_json(
                json.dumps({k: v for k, v in selector.items() if k != "target_id"})
            )
            branches, issues = compile_branches(narrow_target(request, target))
        except ValueError as error:
            branches, issues = (
                [],
                [
                    {
                        "requested_field": f"required_targets.{selector['target_id']}",
                        "requested_value": selector,
                        "inherited_field": "product and scaffold permissions",
                        "inherited_value": None,
                        "explicit_edit": str(error),
                    }
                ],
            )
        if issues and all(i.get("code") == "parameter_domain_intersection_empty" for i in issues):
            # This target remains required by the original panel, but is outside
            # the explicit region evaluated in this round. Never claim it completed.
            selector["parameter_scope"] = "outside_selected_region"
        else:
            conflicts.extend(issues)
        for branch in branches:
            task = tasks.setdefault(
                branch["branch_id"],
                {
                    **branch,
                    "purpose": "required",
                    "target_ids": [],
                },
            )
            task["target_ids"].append(selector["target_id"])
        if len(tasks) > 1024:
            raise ValueError(
                "Required search expands beyond 1024 tasks; narrow the declared domain."
            )
    optional, issues = compile_branches(request)
    conflicts.extend(issues)
    for branch in optional:
        if branch["branch_id"] in tasks:
            tasks[branch["branch_id"]]["covers_original_branch"] = True
        else:
            tasks[branch["branch_id"]] = {
                **branch,
                "purpose": "optional",
                "target_ids": [],
                "covers_original_branch": True,
            }
    return list(tasks.values()), conflicts, targets


def matching_options(target: dict[str, Any], options: list[dict[str, Any]]) -> list[str]:
    return [
        option["label"]
        for option in options
        if all(option["geometry"][k] == v for k, v in target["dimensions"].items())
        and (
            target["loop_sequence"] is None
            or option["target_facts"]["loop_sequence"] == target["loop_sequence"]
        )
        and (
            target["release_enzyme_id"] is None
            or option["target_facts"]["release_enzyme_id"] == target["release_enzyme_id"]
        )
        and (
            target.get("end_placement") is None
            or option["target_facts"].get("end_placement") == target["end_placement"]
        )
        and (
            target.get("basal_nick_enzyme_id") is None
            or option["target_facts"].get("basal_nick_enzyme_id") == target["basal_nick_enzyme_id"]
        )
    ]


def task_decision(
    branch: dict[str, Any],
    targets: list[dict[str, Any]],
    options: list[dict[str, Any]],
    *,
    used: int,
    budget: int,
) -> tuple[str, dict[str, list[str]]]:
    matched = {
        t["target_id"]: matching_options(t, options)
        for t in targets
        if t["target_id"] in branch["target_ids"]
    }
    if matched and all(matched.values()) and not branch.get("covers_original_branch"):
        return "reused", matched
    return ("evaluate" if used < budget else "unexamined"), matched
