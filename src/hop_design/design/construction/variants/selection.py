"""Recheck saved exploration intent before retrieving explicitly named preparations."""

import json
from pathlib import Path

from hop_design.models.construction.stage_controls import ResolvedStageControl
from hop_design.serialization import canonical_json_bytes

from ..discovery.selection import _require_members, _select_captured_scaffold_options
from ..families.selection import ConstructionSet
from ..packets.capture import capture_packet
from .admission import captured_variant_source
from .public import ScaffoldVariantChoices, _admitted_exploration, query_scaffold_variants


def select_scaffold_variants(
    path: str | Path,
    choices: ScaffoldVariantChoices | str | Path,
    *,
    members: dict[str, str],
    baseline: str,
) -> ConstructionSet:
    """Valid labels alone cannot bypass the query's fixed reference, pins, or controls."""
    _require_members(members, baseline)
    if isinstance(choices, ScaffoldVariantChoices):
        choice_files = dict(choices._files)
        choice_roots = choices._roots
    else:
        protected, choice_files = capture_packet(
            choices, schema=ScaffoldVariantChoices._packet_schema
        )
        choice_roots = (protected,)
    with captured_variant_source(path) as admitted:
        pool = _admitted_exploration(admitted)
        query = json.loads(choice_files["query.json"])
        refreshed = query_scaffold_variants(pool, query)
        if refreshed.json_bytes != choice_files["summary.json"]:
            raise ValueError(
                "Saved exploration choices disagree with the admitted result and query."
            )
        summary = json.loads(refreshed.json_bytes)
        incompatible = set(members.values()) - set(summary["compatible_options"])
        if incompatible:
            raise ValueError(
                f"Selected options are outside the active exploration: {sorted(incompatible)}."
            )
        controls = tuple(
            ResolvedStageControl(
                stage=c["stage"], property=c["property"], scope="set", members=tuple(members)
            )
            for c in query.get("controls", [])
            if c["property"] != "product_identity" and len(members) > 1
        )
        selected = _select_captured_scaffold_options(
            *admitted[0], members=members, baseline=baseline, stage_controls=controls
        )
        files = dict(selected._files)
        files["exploration-query.json"] = dict(refreshed._files)["query.json"]
        files["exploration-selection.json"] = canonical_json_bytes(
            {
                "result_digest": pool.result_digest,
                "query_digest": summary["query_digest"],
                "reference": query.get("reference"),
                "stage": query["stage"],
                "members": members,
                "baseline": baseline,
            }
        )
        if admitted[1] is not None:
            files["molecular-edit.json"] = admitted[1]["intent/edit.json"]
        packet = ConstructionSet._create(
            files, json.loads(selected.json_bytes), selected.report_text
        )
        object.__setattr__(packet, "_roots", (admitted[2], *choice_roots))
        return packet
