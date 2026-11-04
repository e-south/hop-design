"""Explain declared joint interface branches without claiming an unrestricted minimum."""

import json
from pathlib import Path
from typing import Any

from ..projections.interfaces import requested_interface


def interface_branch_facts(root: Path, native: dict[str, Any]) -> list[dict[str, Any]]:
    planned = json.loads((root / "intent/summary.json").read_bytes())["branches"]
    examined = {b["branch_id"]: b for b in native["branches"]}
    facts = []
    for branch in planned:
        request = branch["request"]
        interface = requested_interface(request)
        if interface is None:
            continue
        observed = examined.get(branch["branch_id"])
        states = []
        if observed is None:
            states.append("unexamined")
        else:
            if observed["complete_preparations"]:
                states.append("complete_preparations_observed")
            if observed["failures"]:
                states.append("continuation_rejected")
            local = observed["local_coverage"]
            if any(
                v["completion"] == "complete" and v["realization_count"] == 0
                for v in local.values()
                if v is not None
            ):
                states.append("absent_in_examined_local_domain")
            if observed["coverage"]["unexamined_pairs"] or any(
                v["completion"] != "complete" for v in local.values() if v is not None
            ):
                states.append("unexamined")
        facts.append(
            {
                "branch_id": branch["branch_id"],
                **interface,
                "observations": states,
                "option_labels": [
                    o["label"] for o in native["options"] if o["branch_id"] == branch["branch_id"]
                ],
                "local_coverage": observed["local_coverage"] if observed else None,
                "failures": observed["failures"] if observed else [],
            }
        )
    return facts


def conditional_interface_coverage(metadata: dict[str, Any], eligible: list[str]) -> dict[str, Any]:
    branches = []
    for branch in metadata.get("interface_branches", []):
        compatible = [label for label in branch["option_labels"] if label in eligible]
        excluded = [label for label in branch["option_labels"] if label not in eligible]
        branches.append(
            {
                **branch,
                "compatible_options": compatible,
                "excluded_options": excluded,
                "observations": [
                    *branch["observations"],
                    *(["excluded_by_query"] if excluded else []),
                ],
            }
        )
    return {
        "branches": branches,
        "global_minimum": "not_assessed",
        "scope": "declared_joint_branches_only",
    }
