"""Preview permitted preparation changes without discovering molecular witnesses."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

from hop_design.design.source_documents import load_source_mapping
from hop_design.export.construction.scaffold.discovery_preview import preview_report
from hop_design.export.publication import ProtectedRoot
from hop_design.models.construction.discovery.request import ScaffoldDiscoveryRequest
from hop_design.models.construction.source import _contains_internal_schema_name
from hop_design.serialization import canonical_json_bytes, sha256_digest

from ..options.order import validate_options_objective
from ..packets.publication import SourceBoundConstructionPacket
from .branches import compile_branch_plan
from .constraints import effective_scaffold
from .targets import target_plan


@dataclass(frozen=True, init=False, repr=False)
class PreparedScaffoldDiscovery(SourceBoundConstructionPacket):
    """Authored intention and unevaluated finite preparation branches."""

    _packet_schema: ClassVar[str] = "hop.scaffold-discovery-preview-packet/v1"


def prepare_scaffold_discovery(path: str | Path) -> PreparedScaffoldDiscovery:
    """Expose bounded preparation alternatives before any molecular search."""
    protected = ProtectedRoot.capture(path)
    mapping = load_source_mapping(path)
    if _contains_internal_schema_name(mapping):
        raise ValueError("Discovery requests must use external 'schema' fields.")
    request = ScaffoldDiscoveryRequest.model_validate_json(json.dumps(mapping))
    validate_options_objective(request.product, request.objective)
    scaffold, _ = effective_scaffold(request)
    targets: list[dict[str, Any]] = []
    if request.schema_id in (
        "hop.scaffold-discovery/v3",
        "hop.scaffold-discovery/v4",
        "hop.scaffold-discovery/v5",
        "hop.scaffold-discovery/v6",
        "hop.scaffold-discovery/v7",
    ):
        branches, conflicts, targets = target_plan(request, compile_branch_plan)
    else:
        branches, conflicts = compile_branch_plan(request)
    policies = {
        (
            f"{'source' if group_name == 'source_preparation' else 'endpoint'}_{role}"
            if role in ("forward_primer", "reverse_primer")
            else role
        ): value["mode"]
        for group_name, group in request.product.materialization.model_dump(mode="json").items()
        if isinstance(group, dict)
        for role, value in group.items()
        if isinstance(value, dict) and "mode" in value
    }
    if request.product.materialization.adapter_ligation is not None:
        policies["ligation_adapter"] = request.product.materialization.adapter_ligation.mode.value
    summary: dict[str, Any] = {
        "schema": "hop.scaffold-discovery-preview/v1",
        "status": "conflicting_requirements" if conflicts else "ready",
        "request_digest": sha256_digest(canonical_json_bytes(mapping)),
        "endpoint": request.product.endpoint.value,
        "comparison_stage": request.comparison_stage,
        "scaffold": scaffold,
        "requested_scaffold": mapping.get("scaffold"),
        "inherited_scaffold": mapping["product"]
        .get("whole_route_constraints", {})
        .get("hairpin_scaffold"),
        "material_policies": policies,
        "conflicts": conflicts,
        "preparation_changes": request.preparation_changes.model_dump(mode="json"),
        "branches": branches,
        **(
            {"search_targets": targets}
            if request.schema_id
            in (
                "hop.scaffold-discovery/v3",
                "hop.scaffold-discovery/v4",
                "hop.scaffold-discovery/v5",
                "hop.scaffold-discovery/v6",
                "hop.scaffold-discovery/v7",
            )
            else {}
        ),
        "bounds": {
            "max_branches": request.max_branches,
            "max_continuations_per_branch": request.max_continuations_per_branch,
            "permitted_branches": len(branches),
        },
    }
    if request.objective is not None:
        summary["search_objective"] = request.objective.model_dump(mode="json")
    packet = PreparedScaffoldDiscovery._create(
        {"request.json": canonical_json_bytes(mapping)}, summary, preview_report(summary)
    )
    object.__setattr__(packet, "_roots", (protected,))
    return packet
