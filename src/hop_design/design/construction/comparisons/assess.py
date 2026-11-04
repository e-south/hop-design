"""Assess declared comparisons using semantically replayed complete preparations."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

from hop_design.export.construction.comparisons.reports import assessment_report
from hop_design.export.construction.comparisons.sheets import comparison_files
from hop_design.export.publication import ProtectedRoot
from hop_design.models.construction.comparisons.request import (
    ComparisonRequest,
    resolved_stage_controls,
)
from hop_design.models.construction.discovery.request import ScaffoldDiscoveryRequest
from hop_design.models.construction.projections.materials import external_material_uses
from hop_design.serialization import canonical_json_bytes

from ..discovery.admission import captured_discovery
from ..families.properties import shared_values
from ..packets.publication import SourceBoundConstructionPacket
from ..public import VerifiedConstructionBundle
from .controls import stage_facts
from .discovery_request import comparison_discovery
from .grouping import evaluate_groups
from .material_policies import bind_prior_materials
from .prepare import load_brief, preview_brief
from .prior_materials import material_facts, prior_material_changes
from .references import capture_references, reference_summary
from .relationships import group_declarations


@dataclass(frozen=True, init=False, repr=False)
class ScaffoldComparison(SourceBoundConstructionPacket):
    _packet_schema: ClassVar[str] = "hop.scaffold-comparison-packet/v1"


def require_matching_discovery(
    brief: ComparisonRequest, root: Path, references: dict[str, Any] | None = None
) -> None:
    actual = ScaffoldDiscoveryRequest.model_validate_json(
        (root / "intent/request.json").read_bytes()
    )
    # Comparison stage is a projection choice, not a molecular search permission.
    expected = comparison_discovery(brief, references).model_dump(
        mode="json", by_alias=True, exclude={"comparison_stage"}
    )
    original = brief.discovery.model_dump(mode="json", by_alias=True, exclude={"comparison_stage"})
    observed = actual.model_dump(mode="json", by_alias=True, exclude={"comparison_stage"})
    # An externally assessed pool can retain the original permitted-domain search;
    # only execution promises required-first scheduling. Both permissions are exact.
    permitted = (
        (expected,) if references and "@prior_materials" in references else (expected, original)
    )
    if observed not in permitted:
        raise ValueError(
            "Discovery request does not match this comparison's preparation permissions and bounds."
        )


def assessment_summary(
    brief: ComparisonRequest,
    root: Path,
    pool: dict[str, Any],
    receipts: dict[str, VerifiedConstructionBundle],
    references: dict[str, Any] | None = None,
) -> dict[str, Any]:
    require_matching_discovery(brief, root, references)
    preview, _ = preview_brief(brief, references)
    methods = {b["branch_id"]: b["release_enzyme_id"] for b in pool["branches"]}
    method_names = {b["branch_id"]: b["release_method"] for b in pool["branches"]}
    options = []
    for option in pool["options"]:
        # captured_discovery has replayed each option and its stored projection.
        portrait = json.loads((root / Path(option["portrait"]).with_suffix(".json")).read_bytes())
        route = next(
            r
            for r in receipts[option["label"]]._verified_source().result.realizations
            if r.materialized_realization_id == option["materialized_realization_id"]
        )
        options.append(
            {
                **option,
                "release_enzyme_id": methods[option["branch_id"]],
                "release_method": method_names[option["branch_id"]],
                **(
                    {
                        "loop_sequence": portrait["state"]["molecules"][0]["sequence"][
                            portrait["loop_span"]["start"]["offset"] : portrait["loop_span"]["end"][
                                "offset"
                            ]
                        ]
                    }
                    if brief.schema_id != "hop.comparison-brief/v1"
                    else {}
                ),
                "shared_values": shared_values(portrait, brief.shared_properties),
                **({"stage_facts": stage_facts(route)} if resolved_stage_controls(brief) else {}),
                "materials": {
                    use.role.value: material.model_dump(mode="json")
                    for material, use in external_material_uses(route)
                },
            }
        )
        if references and "@prior_materials" in references:
            prior = references["@prior_materials"]
            actual_materials = material_facts(route)
            _, conflicts = bind_prior_materials(
                brief.discovery,
                {
                    **actual_materials,
                    "required_roles": prior["required_roles"],
                },
            )
            options[-1]["prior_material_conflicts"] = conflicts
            options[-1]["prior_material_changes"] = prior_material_changes(
                prior, actual_materials["materials"]
            )
    evaluated = evaluate_groups(brief, options, references)
    if preview["conflicts"]:
        status = "conflicting_requirements"
        evaluated["sets"] = []
    elif not brief.required_members:
        status = "no_required_members"
    elif evaluated["sets"]:
        status = "comparison_available"
    elif evaluated["group_coverage"]["unexamined_assignments"]:
        status = "group_evaluation_incomplete"
    else:
        status = "no_compatible_set_in_evaluated_pool"
    return {
        "schema": "hop.scaffold-comparison-result/v1",
        "status": status,
        "request_digest": preview["request_digest"],
        "purpose": brief.purpose,
        **group_declarations(brief),
        **(
            {
                "release_methods": {
                    b["release_enzyme_id"]: b["release_method"]
                    for b in pool["branches"]
                    if b["release_enzyme_id"] is not None
                }
            }
            if brief.schema_id != "hop.comparison-brief/v1"
            else {}
        ),
        **reference_summary(references),
        "comparison_stage": brief.discovery.comparison_stage,
        "endpoint": pool["endpoint"],
        "shared_properties": list(brief.shared_properties),
        **(
            {"stage_controls": [c.model_dump(mode="json") for c in resolved_stage_controls(brief)]}
            if resolved_stage_controls(brief)
            else {}
        ),
        "preserve_material_roles": list(brief.preserve_material_roles),
        "conflicts": preview["conflicts"],
        "options": options,
        **evaluated,
        "distinct_molecules": {
            stage: len(pool["stage_groups"][stage]) for stage in ("hairpin", "endpoint")
        },
        "coverage": pool["coverage"],
        **({"search_schedule": pool["search_schedule"]} if "search_schedule" in pool else {}),
        "local_coverage": [
            {"branch": b["label"], "coverage": b["local_coverage"]} for b in pool["branches"]
        ],
        "examined_failures": [
            {"branch": b["label"], **failure} for b in pool["branches"] for failure in b["failures"]
        ],
        "selected_set": None,
        "scope": "evaluated_options_only",
        "producer": pool["producer"],
    }


def assess_scaffold_comparison(
    brief_path: str | Path, discovery_path: str | Path
) -> ScaffoldComparison:
    protected = ProtectedRoot.capture(brief_path)
    brief = load_brief(brief_path)
    brief, references, reference_files, roots = capture_references(brief, Path(brief_path).parent)
    with captured_discovery(discovery_path) as (root, pool, receipts, discovery_root):
        summary = assessment_summary(brief, root, pool, receipts, references)
        drawings = {
            p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()
        }
        files = {f"discovery/{name}": content for name, content in drawings.items()}
        files.update(comparison_files(summary, drawings))
    files["request.json"] = canonical_json_bytes(brief)
    files.update(reference_files)
    packet = ScaffoldComparison._create(files, summary, assessment_report(summary))
    object.__setattr__(packet, "_roots", (protected, discovery_root, *roots))
    return packet
