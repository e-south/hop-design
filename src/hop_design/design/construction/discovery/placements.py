"""Finite product placements and explicitly permitted basal nick methods."""

import json
from itertools import product
from typing import Any

from hop_design.models.construction.discovery.request import ScaffoldDiscoveryRequest


def placement_requests(
    request: ScaffoldDiscoveryRequest,
) -> tuple[list[tuple[ScaffoldDiscoveryRequest, list[dict[str, Any]]]], list[dict[str, Any]]]:
    placements = request.end_placements
    pairs = request.receiving_end_pairs
    nicks = request.preparation_changes.basal_nick_enzyme_ids
    if placements is None and pairs is None and nicks is None:
        return [(request, [])], []
    p = request.product
    issues = []
    if p.basal is None or (placements is not None and p.ends is None):
        issues.append(
            {
                "requested_field": "end_placements / preparation_changes.basal_nick_enzyme_ids",
                "inherited_field": "product.endpoint",
                "explicit_edit": (
                    "Use an endpoint with the required basal/release stage, "
                    "or omit these alternatives."
                ),
            }
        )
    else:
        known = {e.enzyme_id: e for e in p.enzyme_catalog.enzymes}
        for enzyme in nicks or ():
            if enzyme not in known or known[enzyme].enzyme_class.value != "nickase":
                issues.append(
                    {
                        "requested_field": "preparation_changes.basal_nick_enzyme_ids",
                        "inherited_field": "product.enzyme_catalog",
                        "explicit_edit": (
                            f"Supply a characterized nickase definition or remove {enzyme}."
                        ),
                    }
                )
            for field in ("forbidden_enzyme_ids", "reserved_enzyme_ids"):
                if enzyme in getattr(p.basal.enzymes, field):
                    issues.append(
                        {
                            "requested_field": "preparation_changes.basal_nick_enzyme_ids",
                            "inherited_field": f"product.basal.enzymes.{field}",
                            "explicit_edit": (
                                f"Remove {enzyme} or explicitly revise the conflicting permission."
                            ),
                        }
                    )
    if issues:
        return [], issues
    alternatives = pairs or placements or (None,)
    if len(alternatives) * len(nicks or (None,)) > 256:
        raise ValueError("Placement/method expansion exceeds 256 branches; narrow the request.")
    result = []
    for alternative, nick in product(alternatives, nicks or (None,)):
        value = request.model_dump(mode="json", by_alias=True)
        value.pop("end_placements", None)
        value.pop("receiving_end_pairs", None)
        value["preparation_changes"].pop("basal_nick_enzyme_ids", None)
        changes = []
        if pairs is not None:
            assert alternative is not None
            ends = alternative.model_dump(mode="json")
            changes.append(
                {
                    "field": "product.ends",
                    "before": value["product"]["ends"],
                    "after": ends,
                    "permission": "receiving_end_pairs",
                }
            )
            value["product"]["ends"] = ends
        elif alternative is not None:
            for side in ("left", "right"):
                requirement = value["product"]["ends"][side]
                number = getattr(alternative, f"{side}_bp")
                changes.append(
                    {
                        "field": f"product.ends.{side}.payload_end_offset_bp",
                        "before": requirement["payload_end_offset_bp"],
                        "after": number,
                        "permission": "end_placements",
                    }
                )
                requirement["payload_end_offset_bp"] = number
        if nick is not None:
            policy = value["product"]["basal"]["enzymes"]
            roles = policy["role_restrictions"]
            old = {e for r in roles if r["role"] == "basal_nick" for e in r["allowed_enzyme_ids"]}
            other = {e for r in roles if r["role"] != "basal_nick" for e in r["allowed_enzyme_ids"]}
            policy["allowed_enzyme_ids"] = list(
                dict.fromkeys(
                    [e for e in policy["allowed_enzyme_ids"] if e not in old or e in other] + [nick]
                )
            )
            policy["role_restrictions"] = [r for r in roles if r["role"] != "basal_nick"] + [
                {"role": "basal_nick", "allowed_enzyme_ids": [nick]}
            ]
            changes.append(
                {
                    "field": "product.basal.enzymes.basal_nick",
                    "before": sorted(old),
                    "after": [nick],
                    "permission": "preparation_changes.basal_nick_enzyme_ids",
                }
            )
        result.append((ScaffoldDiscoveryRequest.model_validate_json(json.dumps(value)), changes))
    return result, []
