"""Shared domain browsing with whole-witness explanations for conditional exclusions."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

from hop_design.design.source_documents import load_source_mapping
from hop_design.models.construction.variants.domain import ParameterDomainQuery
from hop_design.models.construction.variants.parameters import ParameterSelection
from hop_design.serialization import canonical_json_bytes

from ..packets.publication import SourceBoundConstructionPacket
from .parameters.browse import domain_values
from .public import ScaffoldExploration, ScaffoldVariantChoices, query_scaffold_variants


@dataclass(frozen=True, init=False, repr=False)
class ScaffoldParameterDomain(SourceBoundConstructionPacket):
    _packet_schema: ClassVar[str] = "hop.scaffold-parameter-domain-packet/v1"


def query_scaffold_parameter_domain(
    pool: ScaffoldExploration,
    choices: ScaffoldVariantChoices,
    request: str | Path | dict[str, Any],
) -> ScaffoldParameterDomain:
    summary = json.loads(choices.json_bytes)
    query = summary["query"]
    if query_scaffold_variants(pool, query).json_bytes != choices.json_bytes:
        raise ValueError("Parameter domain browsing requires the current verified choices.")
    mapping = load_source_mapping(request) if isinstance(request, str | Path) else request
    page_request = ParameterDomainQuery.model_validate_json(canonical_json_bytes(mapping))
    metadata = json.loads(pool.json_bytes)
    page = domain_values(metadata["parameter_domains"], **page_request.model_dump())
    space = summary["choice_space"]
    selections = [
        ParameterSelection.model_validate_json(canonical_json_bytes(p))
        for p in query.get("parameters", [])
        if p["key"] != page_request.key
    ]
    excluded = {o["label"]: o["reasons"] for o in summary["excluded_options"]}
    entries = []
    for value in page["values"]:
        paths = [p for p in space["paths"] if p["values"].get(page_request.key) == value]
        matching = [
            p
            for p in paths
            if p["eligible_under_preserved_controls"]
            and all(s.accepts(p["values"].get(s.key)) for s in selections)
        ]
        alternatives = [
            {
                "option_label": p["option_label"],
                "different_selections": [
                    s.key for s in selections if not s.accepts(p["values"].get(s.key))
                ],
                "preservation_conflicts": [
                    reason
                    for reason in excluded.get(p["option_label"], [])
                    if reason["kind"] != "parameter_constraint"
                ],
            }
            for p in paths
        ]
        entries.append(
            {
                "value": value,
                "label": metadata.get("parameter_names", {}).get(value, str(value)),
                "status": "supported"
                if matching
                else "blocked_by_selections"
                if paths
                else "no_complete_preparation_recorded",
                "matching_preparations": len(matching),
                "complete_preparations": len(paths),
                "recorded_alternatives": alternatives,
            }
        )
    result = {
        "schema": "hop.scaffold-parameter-domain/v1",
        "query_digest": summary["query_digest"],
        "request": page_request.model_dump(),
        **page,
        "values": entries,
        # A large sequence cardinality must survive JSON/JavaScript without float rounding.
        "total": str(page["total"]),
        "coverage": "No recorded preparation is not a proof of impossibility. "
        "Inspect branch coverage or explicitly evaluate this value.",
    }
    packet = ScaffoldParameterDomain._create(
        {"query.json": canonical_json_bytes(query), "request.json": canonical_json_bytes(mapping)},
        result,
        "# Permitted parameter values\n\n" + result["coverage"] + "\n",
    )
    object.__setattr__(packet, "_roots", (pool._root,))
    return packet
