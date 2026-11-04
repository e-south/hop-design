"""Assess required members with the existing bounded comparison engine after admission."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

from hop_design.design.source_documents import load_source_mapping
from hop_design.models.construction.comparisons.request import (
    ComparisonAssessmentRequest,
    StageComparisonBrief,
)
from hop_design.models.construction.variants.comparison import VariantComparisonRequest
from hop_design.serialization import canonical_json_bytes, sha256_digest

from ..comparisons.grouping import evaluate_groups, member_option_labels
from ..families.properties import shared_values
from ..packets.publication import SourceBoundConstructionPacket
from .public import ScaffoldExploration, ScaffoldVariantChoices, query_scaffold_variants


@dataclass(frozen=True, init=False, repr=False)
class ScaffoldVariantComparison(SourceBoundConstructionPacket):
    _packet_schema: ClassVar[str] = "hop.variant-comparison-packet/v1"


def comparison_brief(
    pool: ScaffoldExploration, request: VariantComparisonRequest, stage: str
) -> StageComparisonBrief:
    value = request.model_dump(mode="json", by_alias=True)
    for key in ("schema", "result_digest", "query_digest"):
        value.pop(key)
    # Admission retains the exact search envelope. Only the assessment stage changes.
    discovery = {**json.loads(pool._request), "comparison_stage": stage}
    brief = StageComparisonBrief.model_validate_json(
        canonical_json_bytes({"schema": "hop.comparison-brief/v3", "discovery": discovery, **value})
    )
    if any(group.product_reference is not None for group in brief.groups):
        raise ValueError(
            "External product references require the verified comparison-brief workflow."
        )
    return brief


def compare_scaffold_variants(
    pool: ScaffoldExploration,
    choices: ScaffoldVariantChoices,
    request: str | Path | dict[str, Any],
) -> ScaffoldVariantComparison:
    value = load_source_mapping(request) if isinstance(request, str | Path) else request
    intent = VariantComparisonRequest.model_validate_json(canonical_json_bytes(value))
    query = json.loads(choices.json_bytes)
    if intent.result_digest != pool.result_digest or intent.query_digest != query["query_digest"]:
        raise ValueError("Stale comparison result or query digest.")
    if query_scaffold_variants(pool, query["query"]).json_bytes != choices.json_bytes:
        raise ValueError("Choices disagree with the admitted exploration.")
    brief = comparison_brief(pool, intent, query["query"]["stage"])
    options = [
        {**o, "shared_values": shared_values(o["portrait_data"], brief.shared_properties)}
        for o in json.loads(pool._options)
    ]
    eligible = [o for o in options if o["label"] in query["compatible_options"]]
    assessed = assess_options(brief, options, eligible)
    canonical = intent.model_dump(mode="json", by_alias=True)
    canonical["required_members"] = sorted(canonical["required_members"], key=lambda m: m["name"])
    summary = {
        "schema": "hop.variant-comparison/v1",
        **assessed,
        "result_digest": pool.result_digest,
        "query_digest": intent.query_digest,
        "request": canonical,
        "request_digest": sha256_digest(canonical_json_bytes(canonical)),
        "comparison_stage": query["query"]["stage"],
        "selected_set": None,
        "coverage": query["coverage"],
        "examined_failures": query["examined_failures"],
        "scope": "evaluated_complete_options_within_active_query",
    }
    packet = ScaffoldVariantComparison._create(
        {
            "request.json": canonical_json_bytes(canonical),
            "query.json": canonical_json_bytes(query["query"]),
        },
        summary,
        "# Required scaffold comparison\n\n"
        f"{len(assessed['sets'])} compatible sets; "
        f"{len(assessed['missing_members'])} required members missing from current choices. "
        "No set is selected. Query alternatives are permissions; required members are obligations. "
        "An absent set in this bounded pool is not global impossibility.\n",
    )
    object.__setattr__(packet, "_roots", choices._roots)
    return packet


def assess_options(
    brief: ComparisonAssessmentRequest,
    options: list[dict[str, Any]],
    eligible: list[dict[str, Any]],
) -> dict[str, Any]:
    """Use one bounded comparison engine and missing-member explanation for every source."""
    evaluated = evaluate_groups(brief, eligible)
    missing = []
    for member in evaluated["members"]:
        if member["option_labels"]:
            continue
        # No second search: assess the same selector against the admitted witnesses.
        declared = next(m for m in brief.required_members if m.name == member["name"])
        unrestricted = member_option_labels(declared, options)
        missing.append(
            {
                "name": member["name"],
                "reason": "excluded_by_query" if unrestricted else "not_observed_in_evaluated_pool",
                "excluded_options": unrestricted,
            }
        )
    status = (
        "comparison_available"
        if evaluated["sets"]
        else (
            "group_evaluation_incomplete"
            if evaluated["group_coverage"]["unexamined_assignments"]
            else "no_compatible_set_in_evaluated_pool"
        )
    )
    return {**evaluated, "status": status, "missing_members": missing}
