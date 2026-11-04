"""Pure edit compilation preserves every unedited declaration and permission."""

import copy
import json
from itertools import product
from typing import Any

from hop_design.models.construction.discovery.request import ScaffoldDiscoveryRequest
from hop_design.models.construction.molecular.edits import LoopSequenceEdit, MolecularEditRequest

from ..discovery.branches import compile_branch_plan
from ..discovery.targets import target_plan


def compile_edit(mapping: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    request = MolecularEditRequest.model_validate_json(json.dumps(mapping))
    compiled = copy.deepcopy(mapping["original_request"])
    if compiled["schema"] != "hop.scaffold-discovery/v4":
        compiled["schema"] = "hop.scaffold-discovery/v3"
    geometry = compiled["product"]["foldback"]["geometry"]
    changes = []
    selectors: list[list[dict[str, Any]]] = []
    for edit in request.edits:

        def replace(
            container: dict[str, Any],
            key: str,
            field: str,
            after: Any,
            stage: str = edit.stage,
            region: str = edit.region,
        ) -> None:
            changes.append(
                {
                    "stage": stage,
                    "region": region,
                    "field": field,
                    "before": container.get(key),
                    "after": after,
                }
            )
            container[key] = after

        if isinstance(edit, LoopSequenceEdit):
            replace(
                geometry,
                "loop_sequences",
                "product.foldback.geometry.loop_sequences",
                list(edit.sequences),
            )
            selectors.append([{"loop_sequence": w} for w in edit.sequences])
        else:
            compiled["schema"] = "hop.scaffold-discovery/v4"
            placements = [p.model_dump(mode="json") for p in edit.placements]
            replace(compiled, "end_placements", "end_placements", placements)
            selectors.append([{"end_placement": p} for p in placements])
            if edit.ends is not None:
                replace(
                    compiled["product"], "ends", "product.ends", edit.ends.model_dump(mode="json")
                )
            for name, values, selector in (
                ("basal_nick_enzyme_ids", edit.basal_nick_enzyme_ids, "basal_nick_enzyme_id"),
                ("release_enzyme_ids", edit.release_enzyme_ids, "release_enzyme_id"),
            ):
                if values is not None:
                    replace(
                        compiled.setdefault("preparation_changes", {}),
                        name,
                        f"preparation_changes.{name}",
                        list(values),
                    )
                    selectors.append([{selector: v} for v in values])
    combinations = 1
    for group in selectors:
        combinations *= len(group)
    if combinations > 64:
        raise ValueError(
            "Molecular edit requires more than 64 target combinations; narrow the edit."
        )
    compiled.setdefault("required_targets", []).extend(
        {k: v for part in combination for k, v in part.items()}
        for combination in product(*selectors)
    )
    try:
        effective = ScaffoldDiscoveryRequest.model_validate_json(json.dumps(compiled))
        branches, conflicts, targets = target_plan(effective, compile_branch_plan)
    except ValueError as error:
        branches, targets = [], []
        conflicts = [
            {
                "requested_field": "edits",
                "inherited_field": "original_request.product.foldback.geometry",
                "explicit_edit": str(error),
            }
        ]
    return compiled, {
        "schema": "hop.molecular-edit-preview/v1",
        "status": "conflicting_requirements" if conflicts else "ready",
        "execution": "not_started",
        "original_request_digest": request.original_request_digest,
        "endpoint": request.original_request.product.endpoint.value,
        "comparison_stage": request.original_request.comparison_stage,
        "changes": changes,
        "conflicts": conflicts,
        "search_targets": targets,
        "bounds": {
            "permitted_tasks": len(branches),
            "max_branches": request.original_request.max_branches,
            "max_continuations_per_branch": request.original_request.max_continuations_per_branch,
        },
    }
