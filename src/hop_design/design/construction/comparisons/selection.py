"""Choose a displayed complete set and retrieve its named exact preparations."""

import json
import tempfile
from pathlib import Path

from hop_design.export.construction.comparisons.sheets import comparison_files
from hop_design.models.construction.comparisons.materials import PriorMaterialReuse
from hop_design.models.construction.comparisons.request import (
    StageComparisonBrief,
    resolved_stage_controls,
)
from hop_design.serialization import canonical_json_bytes

from ..discovery.admission import captured_discovery
from ..discovery.selection import _select_captured_scaffold_options
from ..families.selection import ConstructionSet
from ..packets.capture import capture_packet, write_snapshot
from .assess import assessment_summary
from .prepare import load_brief
from .references import capture_references


def select_scaffold_comparison(
    path: str | Path,
    *,
    set_label: str,
    baseline: str,
) -> ConstructionSet:
    protected, files = capture_packet(path, schema="hop.scaffold-comparison-packet/v1")
    with tempfile.TemporaryDirectory(prefix="hop-comparison-selection-") as folder:
        root = Path(folder)
        write_snapshot(files, root)
        brief = load_brief(root / "request.json")
        brief, references, reference_files, _ = capture_references(brief, root)
        if not (root / "discovery").is_dir():
            raise ValueError(
                "Comparison has no executed discovery; resolve the declarations first."
            )
        with captured_discovery(root / "discovery") as captured:
            discovery, pool, receipts, _ = captured
            summary = assessment_summary(brief, discovery, pool, receipts, references)
            drawings = {
                p.relative_to(discovery).as_posix(): p.read_bytes()
                for p in discovery.rglob("*")
                if p.is_file()
            }
            if canonical_json_bytes(summary) != files["summary.json"]:
                raise ValueError(
                    "Saved comparison assessment disagrees with verified preparations."
                )
            matches = [item for item in summary["sets"] if item["label"] == set_label]
            if len(matches) != 1:
                raise ValueError(f"Unknown comparison set: {set_label}.")
            chosen = matches[0]
            dimensions = {key for member in brief.required_members for key in member.dimensions}
            varied = tuple(
                sorted(
                    k
                    for k in dimensions
                    if len({member.dimensions.get(k) for member in brief.required_members}) > 1
                    and k not in brief.shared_properties
                )
            )
            prior = None
            if isinstance(brief, StageComparisonBrief) and brief.reuse_prior_materials is not None:
                value = brief.reuse_prior_materials.model_dump(mode="json")
                for key in ("bundle_path", "selection_path"):
                    value["reference"][key] = str(root / value["reference"][key])
                prior = PriorMaterialReuse.model_validate_json(canonical_json_bytes(value))
            selected = _select_captured_scaffold_options(
                *captured,
                members=chosen["members"],
                baseline=baseline,
                shared_properties=brief.shared_properties,
                compared_properties=varied,
                stage_controls=resolved_stage_controls(brief),
                reuse_prior_materials=prior,
            )
        selected_files = dict(selected._files)
        if reference_files:
            selected_files.update(
                {f"comparison/{name}": data for name, data in reference_files.items()}
            )
            selected_files["comparison/request.json"] = canonical_json_bytes(brief)
        selected_summary = {
            **summary,
            "sets": [chosen],
            "selected_set": set_label,
            "presentation_baseline": baseline,
        }
        selected_files.update(
            {
                f"comparison/{name}": content
                for name, content in comparison_files(selected_summary, drawings).items()
            }
        )
        if isinstance(brief, StageComparisonBrief):
            selected_files.update(
                comparison_files({**selected_summary, "report_at_root": True}, drawings)
            )
        selected_request = brief.model_dump(mode="json", by_alias=True)
        for group in selected_request.get("groups", []):
            if reference := group.get("product_reference"):
                for key in ("bundle_path", "selection_path"):
                    reference[key] = f"comparison/{reference[key]}"
        if reuse := selected_request.get("reuse_prior_materials"):
            for key in ("bundle_path", "selection_path"):
                reuse["reference"][key] = f"comparison/{reuse['reference'][key]}"
        selected_files["comparison-selection.json"] = canonical_json_bytes(
            {
                "schema": "hop.comparison-selection/v1",
                "request": selected_request,
                "selected_set": chosen,
                "baseline": baseline,
                "group_coverage": summary["group_coverage"],
                "coverage": summary["coverage"],
                "examined_failures": summary["examined_failures"],
            }
        )
        packet = ConstructionSet._create(
            selected_files, json.loads(selected.json_bytes), selected.report_text
        )
    object.__setattr__(packet, "_roots", (protected,))
    return packet
