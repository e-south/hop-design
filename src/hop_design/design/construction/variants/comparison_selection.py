"""Re-admit source and re-assess required membership before retrieving a named set."""

import json
from pathlib import Path

from hop_design.models.construction.comparisons.request import resolved_stage_controls
from hop_design.models.construction.variants.comparison import VariantComparisonRequest
from hop_design.serialization import canonical_json_bytes

from ..discovery.selection import _select_captured_scaffold_options
from ..families.selection import ConstructionSet
from ..packets.capture import capture_packet
from .admission import captured_variant_source
from .comparison import ScaffoldVariantComparison, compare_scaffold_variants, comparison_brief
from .public import _admitted_exploration, query_scaffold_variants


def select_scaffold_variant_comparison(
    source: str | Path,
    comparison: ScaffoldVariantComparison | str | Path,
    *,
    set_label: str,
    baseline: str,
) -> ConstructionSet:
    if isinstance(comparison, ScaffoldVariantComparison):
        files, roots = dict(comparison._files), comparison._roots
    else:
        protected, files = capture_packet(
            comparison, schema=ScaffoldVariantComparison._packet_schema
        )
        roots = (protected,)
    with captured_variant_source(source) as admitted:
        pool = _admitted_exploration(admitted)
        choices = query_scaffold_variants(pool, json.loads(files["query.json"]))
        refreshed = compare_scaffold_variants(pool, choices, json.loads(files["request.json"]))
        if refreshed.json_bytes != files["summary.json"]:
            raise ValueError("Saved required comparison disagrees with verified preparations.")
        summary = json.loads(refreshed.json_bytes)
        matching = [s for s in summary["sets"] if s["label"] == set_label]
        if len(matching) != 1:
            raise ValueError(f"Unknown comparison set: {set_label}.")
        chosen = matching[0]
        intent = VariantComparisonRequest.model_validate_json(files["request.json"])
        brief = comparison_brief(pool, intent, summary["comparison_stage"])
        selected = _select_captured_scaffold_options(
            *admitted[0],
            members=chosen["members"],
            baseline=baseline,
            shared_properties=brief.shared_properties,
            stage_controls=resolved_stage_controls(brief),
        )
        output = dict(selected._files)
        output.update({f"variant-comparison/{name}": content for name, content in files.items()})
        output["variant-comparison-selection.json"] = canonical_json_bytes(
            {
                "result_digest": pool.result_digest,
                "query_digest": summary["query_digest"],
                "request_digest": summary["request_digest"],
                "set_id": chosen["set_id"],
                "members": chosen["members"],
                "baseline": baseline,
                "preserve_material_roles": list(brief.preserve_material_roles),
            }
        )
        if admitted[1] is not None:
            output["molecular-edit.json"] = admitted[1]["intent/edit.json"]
        packet = ConstructionSet._create(
            output, json.loads(selected.json_bytes), selected.report_text
        )
        object.__setattr__(packet, "_roots", (admitted[2], *roots))
        return packet
