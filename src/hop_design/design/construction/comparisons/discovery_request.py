"""Compile comparison obligations into an explicit, replayable discovery request."""

from typing import Any

from hop_design.models.construction.comparisons.request import (
    ComparisonRequest,
    StageComparisonBrief,
)
from hop_design.models.construction.discovery.request import ScaffoldDiscoveryRequest
from hop_design.serialization import canonical_json_bytes

from .material_policies import bind_prior_materials


def comparison_discovery(
    brief: ComparisonRequest, references: dict[str, Any] | None = None
) -> ScaffoldDiscoveryRequest:
    if not isinstance(brief, StageComparisonBrief):
        return brief.discovery
    discovery = brief.discovery
    if brief.reuse_prior_materials is not None:
        if references is None or "@prior_materials" not in references:
            raise ValueError("Prior materials must be verified before request compilation.")
        discovery, _ = bind_prior_materials(discovery, references["@prior_materials"])
    value = discovery.model_dump(mode="json", by_alias=True)
    if value["schema"] != "hop.scaffold-discovery/v4":
        value["schema"] = "hop.scaffold-discovery/v3"
    targets = {
        canonical_json_bytes(member.model_dump(mode="json", exclude={"name"})): member.model_dump(
            mode="json", exclude={"name"}
        )
        for member in brief.required_members
    }
    targets.update(
        {
            canonical_json_bytes(target): target.model_dump(mode="json")
            for target in discovery.required_targets
        }
    )
    value["required_targets"] = [targets[k] for k in sorted(targets)]
    return ScaffoldDiscoveryRequest.model_validate_json(canonical_json_bytes(value))
