"""Present declared permissions beside achieved molecular dimensions; never expand them."""

import json
from typing import Any

from hop_design.models.construction.complete.realization import MaterializedConstructionRealization
from hop_design.models.construction.discovery.request import ScaffoldDiscoveryRequest
from hop_design.models.construction.hairpin_geometry import describe_hairpin
from hop_design.models.enzymes import EnzymePermissions, EnzymeProvisioningPolicy, EnzymeRole

from ..discovery.constraints import effective_scaffold
from .public import ScaffoldExploration


def atlas_envelope(
    pool: ScaffoldExploration,
    summary: dict[str, Any],
    route: MaterializedConstructionRealization,
) -> dict[str, Any]:
    request = ScaffoldDiscoveryRequest.model_validate_json(pool._request)
    scaffold, conflicts = effective_scaffold(request)
    hairpin = describe_hairpin(route)
    p = request.product
    names = {e.enzyme_id: e.canonical_name for e in p.enzyme_catalog.enzymes}
    geometry = {
        "foldback": p.foldback.geometry.model_dump(mode="json"),
        "basal": p.basal.geometry.model_dump(mode="json") if p.basal else None,
    }

    def permitted(local: EnzymePermissions | None, role: EnzymeRole) -> tuple[str, ...]:
        if local is None:
            return ()
        policy = EnzymeProvisioningPolicy(catalog=p.enzyme_catalog, **local.model_dump())
        return tuple(i for i in names if policy.permits(i, role=role))

    permissions = {}
    for role, ids in (
        ("foldback", permitted(p.foldback.enzymes, EnzymeRole.FOLDBACK_NICK)),
        (
            "basal_nick",
            request.preparation_changes.basal_nick_enzyme_ids
            or permitted(p.basal.enzymes if p.basal else None, EnzymeRole.BASAL_NICK),
        ),
        (
            "release",
            request.preparation_changes.release_enzyme_ids
            or permitted(p.release.enzymes if p.release else None, EnzymeRole.END_GENERATION),
        ),
    ):
        permissions[role] = [{"enzyme_id": i, "name": names[i]} for i in ids]
    return {
        "schema": "hop.scaffold-envelope/v1",
        "request_digest": json.loads(pool.json_bytes)["request_digest"],
        "requested_scaffold": json.loads(pool._request).get("scaffold"),
        "effective_scaffold": scaffold,
        "conflicts": conflicts,
        "generating_domains": geometry,
        "end_placements": [v.model_dump(mode="json") for v in request.end_placements or ()],
        **(
            {
                "receiving_end_pairs": [
                    p.model_dump(mode="json") for p in request.receiving_end_pairs
                ]
            }
            if request.receiving_end_pairs is not None
            else {}
        ),
        "method_permissions": permissions,
        "observed_stage_id": hairpin.state.state_id,
        "observed_stage_role": hairpin.stage_role,
        "observed": {
            key: getattr(hairpin, key)
            for key in (
                "stem_bp",
                "loop_nt",
                "loop_side_paired_bp",
                "open_side_paired_positions",
                "noncanonical_open_side_contacts",
            )
        },
        "boundaries": {
            key: getattr(hairpin, key).model_dump(mode="json")
            for key in (
                "stem_primary_span",
                "stem_return_span",
                "paired_primary_span",
                "paired_return_span",
                "loop_span",
            )
        },
        "preserved": {
            key: summary["query"][key] for key in ("reference", "controls", "surroundings", "pins")
        },
        "coverage": json.loads(pool.json_bytes)["coverage"],
        "readiness": "Modeled preparation; recovery, reaction performance and "
        "receiving-construct compatibility remain unassessed.",
        "revision": "Export request.json; author and preview an explicit request revision "
        "through CLI/API. Evaluation is a separate operation.",
    }
