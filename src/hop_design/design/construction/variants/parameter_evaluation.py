"""Explicit bounded evaluation adds immutable evidence without replacing a prior pool."""

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

from hop_design.models.construction.discovery.request import ScaffoldDiscoveryRequest
from hop_design.models.construction.variants.parameters import ParameterSelection
from hop_design.serialization import canonical_json_bytes, sha256_digest

from ..discovery.explore import discover_scaffolds
from ..discovery.prepare import prepare_scaffold_discovery
from ..options.limits import require_inventory_size
from ..packets.publication import SourceBoundConstructionPacket
from .public import ScaffoldExploration, ScaffoldVariantChoices
from .source_capture import capture_exploration


@dataclass(frozen=True, init=False, repr=False)
class ScaffoldParameterEvaluation(SourceBoundConstructionPacket):
    _packet_schema: ClassVar[str] = "hop.scaffold-parameter-evaluation-packet/v1"


class InheritedParameterConflict(ValueError):
    def __init__(self, key: str):
        self.key = key
        super().__init__(f"Selected {key} conflicts with the inherited restriction.")


def _intersection(left: ParameterSelection, right: ParameterSelection) -> ParameterSelection:
    if left.values is not None or right.values is not None:
        values = left.values if left.values is not None else right.values
        assert values is not None
        shared = tuple(v for v in values if left.accepts(v) and right.accepts(v))
        if not shared:
            raise InheritedParameterConflict(left.key)
        return ParameterSelection(key=left.key, values=shared)
    assert left.minimum is not None and left.maximum is not None
    assert right.minimum is not None and right.maximum is not None
    if max(left.minimum, right.minimum) > min(left.maximum, right.maximum):
        raise InheritedParameterConflict(left.key)
    return ParameterSelection(
        key=left.key,
        minimum=max(left.minimum, right.minimum),
        maximum=min(left.maximum, right.maximum),
    )


def evaluation_request(
    pool: "ScaffoldExploration",
    choices: "ScaffoldVariantChoices",
    max_branches: int,
    max_continuations_per_branch: int,
) -> dict[str, Any]:
    from .public import query_scaffold_variants

    summary = json.loads(choices.json_bytes)
    if query_scaffold_variants(pool, summary["query"]).json_bytes != choices.json_bytes:
        raise ValueError("Further evaluation requires the current verified choices.")
    if not summary["query"].get("parameters"):
        raise ValueError("Select at least one molecular parameter before targeted evaluation.")
    return selected_evaluation_request(
        json.loads(pool._request), summary["query"], max_branches, max_continuations_per_branch
    )


def selected_evaluation_request(
    envelope: dict[str, Any],
    query: dict[str, Any],
    max_branches: int,
    max_continuations_per_branch: int,
) -> dict[str, Any]:
    """Intersect evaluation targets with an explicitly supplied generating envelope."""
    value = dict(envelope)
    selections = {
        p["key"]: ParameterSelection.model_validate_json(canonical_json_bytes(p))
        for p in value.get("parameters", [])
    }
    for content in query.get("parameters", []):
        selected = ParameterSelection.model_validate_json(canonical_json_bytes(content))
        if selected.key in selections:
            selected = _intersection(selections[selected.key], selected)
        selections[selected.key] = selected
    value.update(
        schema="hop.scaffold-discovery/v6"
        if value.get("receiving_end_pairs")
        else "hop.scaffold-discovery/v5",
        parameters=[
            p.model_dump(mode="json", exclude_none=True) for _, p in sorted(selections.items())
        ],
        max_branches=max_branches,
        max_continuations_per_branch=max_continuations_per_branch,
    )
    return ScaffoldDiscoveryRequest.model_validate_json(canonical_json_bytes(value)).model_dump(
        mode="json", by_alias=True
    )


def evaluation_summary(
    parent_digest: str, query: dict[str, Any], request: dict[str, Any], additional: dict[str, Any]
) -> dict[str, Any]:
    return {
        "schema": "hop.scaffold-parameter-evaluation/v1",
        "parent_result_digest": parent_digest,
        "query": query,
        "evaluation_request_digest": sha256_digest(canonical_json_bytes(request)),
        "additional_request_digest": additional["request_digest"],
        "additional_complete_preparations": len(additional["options"]),
        "additional_coverage": additional["coverage"],
        "preservation": (
            "Original choices, reference and requirements retained; query reapplied to the union."
        ),
    }


def evaluate_scaffold_parameters(
    pool: "ScaffoldExploration",
    choices: "ScaffoldVariantChoices",
    *,
    max_branches: int,
    max_continuations_per_branch: int,
) -> ScaffoldParameterEvaluation:
    request = evaluation_request(pool, choices, max_branches, max_continuations_per_branch)
    protected, parent_files = capture_exploration(pool)
    with tempfile.TemporaryDirectory(prefix="hop-parameter-evaluation-") as temporary:
        source = Path(temporary) / "request.json"
        source.write_bytes(canonical_json_bytes(request))
        preview = prepare_scaffold_discovery(source)
        if json.loads(preview.json_bytes)["status"] != "ready":
            raise ValueError(preview.report_text)
        additional = discover_scaffolds(source)
    summary = evaluation_summary(
        pool.result_digest,
        json.loads(choices.json_bytes)["query"],
        request,
        json.loads(additional.json_bytes),
    )
    files = {f"previous/{name}": data for name, data in parent_files.items()}
    files.update({f"additional/{name}": data for name, data in additional._files})
    files["evaluation-request.json"] = canonical_json_bytes(request)
    require_inventory_size(len(files), sum(map(len, files.values())))
    packet = ScaffoldParameterEvaluation._create(
        files,
        summary,
        "# Additional parameter evaluation\n\nThe previous pool is retained unchanged. "
        "Additional complete preparations must satisfy the selected parameter constraints. "
        "Reload this packet and reapply the saved query using its new result digest. "
        "Coverage remains bounded; no search limit or molecular requirement "
        "was silently relaxed.\n",
    )
    object.__setattr__(packet, "_roots", (protected,))
    return packet
