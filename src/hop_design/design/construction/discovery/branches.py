"""Compile permitted preparation branches without file I/O or packet presentation."""

import json
from itertools import product
from typing import Any

from hop_design.models.construction.discovery.request import ScaffoldDiscoveryRequest
from hop_design.models.construction.product_request import ProductRequest
from hop_design.serialization import canonical_json_bytes, sha256_digest

from .constraints import effective_scaffold
from .methods import apply_method, method_conflicts
from .parameter_restrictions import restrict_parameter_branches
from .placements import placement_requests
from .terminals import TerminalSetting, terminal_settings


def expand_request(
    request: ScaffoldDiscoveryRequest,
    scaffold: dict[str, Any],
    terminals: list[TerminalSetting] | None = None,
) -> list[dict[str, Any]]:
    base = request.product.model_dump(mode="json", by_alias=True)
    if scaffold:
        base["whole_route_constraints"]["hairpin_scaffold"] = scaffold
    open_side = scaffold.get("open_side_paired_positions")
    settings: list[tuple[int | None, int | None]] = [(None, None)]
    if (
        terminals is None
        and open_side is not None
        and request.preparation_changes.adapter_redesign == "allow"
    ):
        if request.product.basal is None:
            raise ValueError("Adapter redesign requires a PCR-bearing product with basal geometry.")
        geometry = request.product.basal.geometry
        count = (open_side["maximum"] - open_side["minimum"] + 1) * len(geometry.nick_offsets_nt)
        if count > 256:
            raise ValueError("Preparation expansion exceeds 256 branches; narrow scaffold ranges.")
        # For this route's forward source, the nick-to-stem span also contributes
        # open-side positions. This is a candidate setting, not achieved geometry:
        # proximal pairing can impose a larger span; complete admission still checks it.
        settings = list(
            dict.fromkeys(
                (nick, max(1, desired - nick))
                for nick, desired in product(
                    geometry.nick_offsets_nt, range(open_side["minimum"], open_side["maximum"] + 1)
                )
            )
        )
    methods: tuple[str | None, ...]
    if request.preparation_changes.release_enzyme_ids is None:
        request.product.construction_source()
        methods = (
            (None,)
            if request.product.release is None
            else tuple(request.product.release.enzymes.allowed_enzyme_ids)
        )
    else:
        methods = request.preparation_changes.release_enzyme_ids
    candidates = (
        [(s.nick, s.annealing, s.tail) for s in terminals]
        if terminals is not None
        else [(nick, annealing, None) for nick, annealing in settings]
    )
    if len(candidates) * len(methods) > 256:
        raise ValueError(
            "Preparation expansion exceeds 256 branches; narrow dimensions or methods."
        )
    branches = []
    for (nick, annealing, tail), enzyme in product(candidates, methods):
        value = json.loads(json.dumps(base))
        changes = []
        if annealing is not None:
            geometry = value["basal"]["geometry"]
            changes.append(
                {
                    "field": "product.basal.geometry.minimum_adapter_annealing_nt",
                    "before": geometry["minimum_adapter_annealing_nt"],
                    "after": annealing,
                    "permission": "preparation_changes.adapter_redesign",
                }
            )
            geometry["minimum_adapter_annealing_nt"] = annealing
            geometry["nick_offsets_nt"] = [nick]
        if tail is not None:
            adapter = value["materialization"]["adapter_ligation"]
            updated = {
                key: v
                for key, v in adapter.items()
                if key not in ("mode", "three_prime_handle_sequence")
            }
            updated["mode"] = "constrain" if tail else "derive"
            if tail:
                updated["three_prime_handle_sequence"] = tail
            if adapter != updated:
                changes.append(
                    {
                        "field": "product.materialization.adapter_ligation",
                        "before": adapter,
                        "after": updated,
                        "permission": "preparation_changes.adapter_redesign",
                        "sequence_policy": "declared_exact_tails"
                        if request.preparation_changes.three_prime_tail_sequences is not None
                        else "prefix_of_existing_tail",
                    }
                )
            value["materialization"]["adapter_ligation"] = updated
        if request.preparation_changes.release_enzyme_ids is not None:
            changes.extend(apply_method(value, enzyme))
        compiled = ProductRequest.model_validate_json(json.dumps(value))
        compiled.construction_source()
        branches.append(
            {
                "branch_id": sha256_digest(canonical_json_bytes(value)),
                "request": value,
                "changes": changes,
                "release_enzyme_id": enzyme,
            }
        )
    return branches


def compile_branch_plan(
    request: ScaffoldDiscoveryRequest,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    scaffold, conflicts = effective_scaffold(request)
    conflicts.extend(method_conflicts(request))
    variants, issues = placement_requests(request)
    conflicts.extend(issues)
    branches = []
    if not conflicts:
        for variant, changes in variants:
            terminals, issues = terminal_settings(variant, scaffold)
            conflicts.extend(issues)
            if not issues:
                for branch in expand_request(variant, scaffold, terminals):
                    branch["changes"] = changes + branch["changes"]
                    branches.append(branch)
            if len(branches) > 256:
                raise ValueError("Preparation expansion exceeds 256 branches; narrow permissions.")
    if request.parameters and not conflicts:
        branches = restrict_parameter_branches(
            branches, request.parameters, request.comparison_stage
        )
        if not branches:
            conflicts.append(
                {
                    "code": "parameter_domain_intersection_empty",
                    "scope": "declared_permissions_only",
                    "requested_field": "parameters",
                    "requested_value": [
                        p.model_dump(mode="json", exclude_none=True) for p in request.parameters
                    ],
                    "inherited_value": "no overlapping declared branch",
                    "inherited_field": "product and preparation permissions",
                    "explicit_edit": (
                        "Revise the selected constraints explicitly; "
                        "no new joint combinations were authorized."
                    ),
                }
            )
    return branches, conflicts
