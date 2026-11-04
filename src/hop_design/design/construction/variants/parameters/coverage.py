"""Keep planned branch domains and scoped observations separate from complete paths."""

import json
from pathlib import Path
from typing import Any

from hop_design.models.construction.discovery.request import ScaffoldDiscoveryRequest
from hop_design.models.construction.product_request import ProductRequest

from ...projections.primer_boundary import primer_boundaries
from .domains import parameter_domains
from .local_support import local_support


def parameter_metadata(root: Path, native: dict[str, Any]) -> dict[str, Any]:
    request = ScaffoldDiscoveryRequest.model_validate_json(
        (root / "intent/request.json").read_bytes()
    )
    plan = json.loads((root / "intent/summary.json").read_bytes())
    examined = {
        branch.get("coverage_record_id", branch["branch_id"]): branch
        for branch in native["branches"]
    }
    branches = []
    primer_failures: list[dict[str, Any]] = []
    for branch in plan["branches"]:
        record_id = branch.get("coverage_record_id", branch["branch_id"])
        observed = examined.get(record_id)
        product = ProductRequest.model_validate_json(json.dumps(branch["request"]))
        exact = request.model_copy(
            update={
                "product": product,
                "end_placements": None,
                "receiving_end_pairs": None,
                "preparation_changes": request.preparation_changes.model_copy(
                    update={"basal_nick_enzyme_ids": None, "release_enzyme_ids": None}
                ),
            }
        )
        branches.append(
            {
                "branch_id": branch["branch_id"],
                **(
                    {"receiving_end_pair": product.ends.model_dump(mode="json")}
                    if request.receiving_end_pairs is not None and product.ends is not None
                    else {}
                ),
                "coverage_record_id": record_id,
                "domains": parameter_domains(exact),
                "status": "evaluated" if observed else "unexamined",
                "option_labels": [
                    o["label"]
                    for o in native["options"]
                    if o.get("coverage_record_id", o["branch_id"]) == record_id
                ],
                "local_coverage": observed["local_coverage"] if observed else None,
                "continuation_coverage": observed["coverage"] if observed else None,
                "failures": observed["failures"] if observed else [],
                "parameter_exclusions": observed.get("parameter_exclusions", [])
                if observed
                else [],
                "scope": "this_declared_branch_only",
            }
        )
        for failure in observed["failures"] if observed else ():
            if not any(
                d["code"] == "primer-annealing-span-exceeded"
                for d in failure.get("preparation_constraints", [])
            ):
                continue
            outcome = (root / failure["outcome"]).parent
            record = json.loads((outcome / "construction/construction-result.json").read_bytes())
            primer_failures.extend(
                {
                    **row,
                    "branch_id": branch["branch_id"],
                    "outcome": failure["outcome"],
                    "complete_alternative_labels": branches[-1]["option_labels"],
                }
                for row in primer_boundaries(record)
            )
    return {
        "parameter_domains": parameter_domains(request),
        "local_parameter_support": local_support(root, native),
        "parameter_names": {
            e.enzyme_id: e.canonical_name for e in request.product.enzyme_catalog.enzymes
        },
        "parameter_branch_coverage": branches,
        "primer_boundaries": primer_failures,
        "joint_permissions": {
            **(
                {
                    "receiving_end_pairs": [
                        p.model_dump(mode="json") for p in request.receiving_end_pairs
                    ]
                }
                if request.receiving_end_pairs is not None
                else {}
            ),
            "end_placements": [v.model_dump(mode="json") for v in request.end_placements or ()],
            "foldback": "R = A - D; D <= A; 2*A + C <= retained-overhead budget",
            "independent_recombination": False,
        },
    }
