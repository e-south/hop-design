"""Preview comparison obligations without running molecular discovery."""

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

from pydantic import TypeAdapter

from hop_design.design.source_documents import load_source_mapping
from hop_design.export.construction.comparisons.reports import preview_report
from hop_design.export.publication import ProtectedRoot
from hop_design.models.construction.comparisons.request import (
    ComparisonRequest,
    resolved_stage_controls,
)
from hop_design.models.construction.source import _contains_internal_schema_name
from hop_design.serialization import canonical_json_bytes, sha256_digest

from ..discovery.prepare import prepare_scaffold_discovery
from ..packets.publication import SourceBoundConstructionPacket
from .discovery_request import comparison_discovery
from .domains import dimension_permissions, member_conflicts
from .material_policies import bind_prior_materials
from .references import capture_references, reference_summary
from .relationships import group_declarations


@dataclass(frozen=True, init=False, repr=False)
class PreparedScaffoldComparison(SourceBoundConstructionPacket):
    _packet_schema: ClassVar[str] = "hop.comparison-preview-packet/v1"


def load_brief(path: str | Path) -> ComparisonRequest:
    mapping = load_source_mapping(path)
    if _contains_internal_schema_name(mapping):
        raise ValueError("Comparison briefs must use external 'schema' fields.")
    return TypeAdapter(ComparisonRequest).validate_json(json.dumps(mapping))


def preview_brief(
    brief: ComparisonRequest, references: dict[str, Any] | None = None
) -> tuple[dict[str, Any], dict[str, bytes]]:
    with tempfile.TemporaryDirectory(prefix="hop-comparison-preview-") as folder:
        path = Path(folder) / "request.json"
        path.write_bytes(canonical_json_bytes(comparison_discovery(brief, references)))
        discovery = prepare_scaffold_discovery(path)
    preview = json.loads(discovery.json_bytes)
    dimensions = dimension_permissions(brief, preview)
    conflicts = list(preview["conflicts"]) + member_conflicts(brief, dimensions)
    if references and "@prior_materials" in references:
        _, material_conflicts = bind_prior_materials(
            brief.discovery, references["@prior_materials"]
        )
        conflicts.extend(material_conflicts)
    arms = brief.discovery.product.hairpin_basal_component
    interval = dimensions["open_side_paired_positions"]["requested_interval"]
    if (
        arms is not None
        and interval
        and not interval["minimum"] <= len(arms.left_arm) <= interval["maximum"]
    ):
        conflicts.append(
            {
                "member": None,
                "requested_field": "discovery.scaffold.open_side_paired_positions",
                "requested_value": interval,
                "inherited_field": "discovery.product.hairpin_basal_component",
                "inherited_value": arms.model_dump(mode="json"),
                "explicit_edit": "Provide explicit basal arms with the desired length "
                "or revise the "
                "dimension; HOP does not generate replacement direct-hairpin arms.",
            }
        )
    summary = {
        "schema": "hop.comparison-preview/v1",
        "request_digest": sha256_digest(canonical_json_bytes(brief)),
        "status": "conflicting_requirements" if conflicts else "ready",
        "purpose": brief.purpose,
        **group_declarations(brief),
        **reference_summary(references),
        "endpoint": preview["endpoint"],
        "comparison_stage": brief.discovery.comparison_stage,
        "required_members": [m.model_dump(mode="json") for m in brief.required_members],
        "shared_properties": list(brief.shared_properties),
        **(
            {"stage_controls": [c.model_dump(mode="json") for c in resolved_stage_controls(brief)]}
            if resolved_stage_controls(brief)
            else {}
        ),
        "preserve_material_roles": list(brief.preserve_material_roles),
        "max_group_evaluations": brief.max_group_evaluations,
        "dimensions": dimensions,
        "conflicts": conflicts,
        "discovery": preview,
    }
    return summary, {f"discovery/{name}": data for name, data in discovery._files}


def prepare_scaffold_comparison(path: str | Path) -> PreparedScaffoldComparison:
    protected = ProtectedRoot.capture(path)
    brief = load_brief(path)
    brief, references, reference_files, roots = capture_references(brief, Path(path).parent)
    summary, files = preview_brief(brief, references)
    files.update(reference_files)
    files["request.json"] = canonical_json_bytes(brief)
    packet = PreparedScaffoldComparison._create(files, summary, preview_report(summary))
    object.__setattr__(packet, "_roots", (protected, *roots))
    return packet
