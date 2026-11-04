"""Public comparison lifecycle delegated to the admitted variant/comparison owners."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from hop_design.design.source_documents import load_source_mapping
from hop_design.models.construction.intents.comparison import (
    DesignComparisonRequest,
    DesignSetSelection,
)
from hop_design.serialization import canonical_json_bytes, sha256_digest

from ..families.selection import ConstructionSet
from ..variants.comparison import ScaffoldVariantComparison, compare_scaffold_variants
from ..variants.comparison_selection import select_scaffold_variant_comparison
from .base import Source

if TYPE_CHECKING:
    from .hairpin_choices import HairpinDesignChoices


def source_value(source: Source) -> dict[str, Any]:
    return load_source_mapping(source) if isinstance(source, str | Path) else source


def _native_comparison(
    choices: HairpinDesignChoices, request: DesignComparisonRequest, query: Source | None
) -> ScaffoldVariantComparison:
    if any(member.release_enzyme_id is not None for member in request.required_members):
        raise ValueError("A release method does not apply to a hairpin endpoint.")
    native = choices._native(query, stage=request.stage)
    value = request.model_dump(mode="json", by_alias=True)
    value.pop("schema")
    value.pop("stage")
    return compare_scaffold_variants(
        choices._pool,
        native,
        {
            **value,
            "result_digest": choices._pool.result_digest,
            "query_digest": json.loads(native.json_bytes)["query_digest"],
        },
    )


def compare_choices(
    choices: HairpinDesignChoices, request: Source, query: Source | None
) -> dict[str, Any]:
    intent = DesignComparisonRequest.model_validate_json(
        canonical_json_bytes(source_value(request))
    )
    resolved = choices._resolved_query(query)
    native = _native_comparison(choices, intent, query)
    summary = json.loads(native.json_bytes)
    canonical_request = intent.model_dump(mode="json", by_alias=True)
    canonical_request["required_members"] = summary["request"]["required_members"]
    summary.pop("result_digest")
    return {
        **summary,
        "schema": "hop.design-comparison/v1",
        "request_digest": sha256_digest(
            canonical_json_bytes(choices.resolution["effective_request"])
        ),
        "snapshot_digest": choices._pool.result_digest,
        "query": resolved.model_dump(mode="json", by_alias=True),
        "query_digest": sha256_digest(canonical_json_bytes(resolved)),
        "request": canonical_request,
    }


def _selection(
    choices: HairpinDesignChoices, comparison: dict[str, Any], *, set_label: str, baseline: str
) -> dict[str, Any]:
    chosen = next((s for s in comparison["sets"] if s["label"] == set_label), None)
    if chosen is None:
        raise ValueError(f"Unknown comparison set: {set_label}.")
    options = {o["label"]: o for o in json.loads(choices._pool._options)}
    selected = DesignSetSelection.model_validate_json(
        canonical_json_bytes(
            {
                **{
                    k: comparison[k]
                    for k in (
                        "request_digest",
                        "snapshot_digest",
                        "query_digest",
                        "request",
                        "query",
                    )
                },
                "comparison_digest": sha256_digest(canonical_json_bytes(comparison)),
                "set_label": set_label,
                "set_id": chosen["set_id"],
                "baseline": baseline,
                "members": {
                    name: choices.select(
                        {
                            "option_label": label,
                            "materialized_realization_id": options[label][
                                "materialized_realization_id"
                            ],
                        },
                        query=comparison["query"],
                    )
                    for name, label in sorted(chosen["members"].items())
                },
            }
        )
    )
    return selected.model_dump(mode="json", by_alias=True)


def select_comparison(
    choices: HairpinDesignChoices, comparison: Source, *, set_label: str, baseline: str
) -> dict[str, Any]:
    value = source_value(comparison)
    if (
        value.get("schema") != "hop.design-comparison/v1"
        or not isinstance(value.get("request"), dict)
        or not isinstance(value.get("query"), dict)
    ):
        raise ValueError("Expected a saved design comparison from these choices.")
    refreshed = compare_choices(choices, value["request"], value["query"])
    if value != refreshed:
        raise ValueError("Saved comparison disagrees with this discovery, query or assessment.")
    return _selection(choices, refreshed, set_label=set_label, baseline=baseline)


def retrieve_comparison(
    choices: HairpinDesignChoices, selection: Source, destination: str | Path
) -> tuple[str, ...]:
    selected = DesignSetSelection.model_validate_json(canonical_json_bytes(source_value(selection)))
    comparison = compare_choices(
        choices,
        selected.request.model_dump(mode="json", by_alias=True),
        selected.query.model_dump(mode="json", by_alias=True),
    )
    refreshed = _selection(
        choices, comparison, set_label=selected.set_label, baseline=selected.baseline
    )
    if refreshed != selected.model_dump(mode="json", by_alias=True):
        raise ValueError(
            "Selected comparison identity, membership or query disagrees with this discovery."
        )
    native = _native_comparison(choices, selected.request, comparison["query"])
    packet = select_scaffold_variant_comparison(
        choices.inspection_source,
        native,
        set_label=selected.set_label,
        baseline=selected.baseline,
    )
    public_packet = ConstructionSet._create(
        {**dict(packet._files), "design-selection.json": canonical_json_bytes(selected)},
        json.loads(packet.json_bytes),
        packet.report_text,
    )
    object.__setattr__(public_packet, "_roots", packet._roots)
    choices._protect(public_packet).write(choices._output(destination))
    return tuple(s.materialized_realization_id for _, s in sorted(selected.members.items()))
