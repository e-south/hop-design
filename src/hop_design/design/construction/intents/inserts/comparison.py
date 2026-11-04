"""Public insert comparisons reuse the bounded molecular assessment engine."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from hop_design.models.construction.intents.comparison import (
    DesignComparisonRequest,
    InsertDesignSetSelection,
)
from hop_design.serialization import canonical_json_bytes, sha256_digest

from ...families.properties import shared_values
from ...variants.comparison import assess_options
from ..base import Source
from ..comparisons import source_value
from .admission import admitted_options
from .selection import native_selection

if TYPE_CHECKING:
    from ..results import InsertDesignChoices


def compare(choices: InsertDesignChoices, source: Source, query: Source | None) -> dict[str, Any]:
    request = DesignComparisonRequest.model_validate_json(
        canonical_json_bytes(source_value(source))
    )
    if any(g.product_reference is not None for g in request.groups):
        raise ValueError(
            "External product references require the verified comparison-brief workflow."
        )
    answer = choices.query(query)
    surroundings = answer["query"].get("surroundings")
    if surroundings is not None and surroundings["stage"] != request.stage:
        raise ValueError("Comparison stage conflicts with the preserved surroundings stage.")
    options = [
        {**o, "shared_values": shared_values(o["portrait_data"], request.shared_properties)}
        for o in admitted_options(choices)
    ]
    matched = {p["materialized_realization_id"] for p in answer["paths"] if p["matches"]}
    assessed = assess_options(request, options, [o for o in options if o["label"] in matched])
    canonical = request.model_dump(mode="json", by_alias=True)
    canonical["required_members"] = sorted(canonical["required_members"], key=lambda m: m["name"])
    return {
        "schema": "hop.design-comparison/v1",
        **assessed,
        **{
            k: answer[k]
            for k in ("request_digest", "snapshot_digest", "query", "query_digest", "coverage")
        },
        "request": canonical,
        "comparison_stage": request.stage,
        "selected_set": None,
        "scope": "evaluated_complete_options_within_active_query",
    }


def select_set(
    choices: InsertDesignChoices, source: Source, *, set_label: str, baseline: str
) -> dict[str, Any]:
    value = source_value(source)
    if value.get("schema") != "hop.design-comparison/v1" or not isinstance(
        value.get("request"), dict
    ):
        raise ValueError("Expected a saved design comparison from these choices.")
    refreshed = compare(choices, value["request"], value.get("query"))
    if refreshed != value:
        raise ValueError("Saved comparison disagrees with this discovery, query or assessment.")
    chosen = next((s for s in refreshed["sets"] if s["label"] == set_label), None)
    if chosen is None:
        raise ValueError(f"Unknown comparison set: {set_label}.")
    value = {
        **{
            k: refreshed[k]
            for k in (
                "request_digest",
                "snapshot_digest",
                "query_digest",
                "query",
                "request",
            )
        },
        "comparison_digest": sha256_digest(canonical_json_bytes(refreshed)),
        "set_label": set_label,
        "set_id": chosen["set_id"],
        "baseline": baseline,
        "members": {
            name: choices.select(identity, query=refreshed["query"])
            for name, identity in sorted(chosen["members"].items())
        },
    }
    value["schema"] = "hop.design-set-selection/v2"
    value["selection_digest"] = sha256_digest(canonical_json_bytes(value))
    selected = InsertDesignSetSelection.model_validate_json(canonical_json_bytes(value))
    return selected.model_dump(mode="json", by_alias=True)


def admit_set(choices: InsertDesignChoices, source: Source) -> InsertDesignSetSelection:
    """Reassess exact membership, so appending unrelated choices cannot invalidate a set."""
    value = source_value(source)
    selected = InsertDesignSetSelection.model_validate_json(canonical_json_bytes(value))
    if (
        selected.selection_digest
        != sha256_digest(
            canonical_json_bytes(
                selected.model_dump(mode="json", by_alias=True, exclude={"selection_digest"})
            )
        )
        or selected.query_digest != sha256_digest(canonical_json_bytes(selected.query))
        or selected.request_digest != sha256_digest(canonical_json_bytes(choices._pool._request))
    ):
        raise ValueError(
            "Selected comparison selection digest or request disagrees with its contents."
        )
    if set(selected.members) != {m.name for m in selected.request.required_members}:
        raise ValueError("Selected comparison membership must contain every required member.")
    membership = {
        name: member.materialized_realization_id for name, member in selected.members.items()
    }
    if selected.set_id != sha256_digest(canonical_json_bytes(membership)):
        raise ValueError("Selected comparison membership disagrees with its set identity.")
    for member in selected.members.values():
        if (
            canonical_json_bytes(member.query) != canonical_json_bytes(selected.query)
            or member.request_digest != selected.request_digest
            or member.snapshot_digest != selected.snapshot_digest
        ):
            raise ValueError("Selected comparison members disagree with its query or snapshot.")
        native_selection(choices, member.model_dump(mode="json", by_alias=True))
    options = [
        {
            **o,
            "shared_values": shared_values(o["portrait_data"], selected.request.shared_properties),
        }
        for o in admitted_options(choices)
        if o["label"] in membership.values()
    ]
    assessed = assess_options(selected.request, options, options)
    if not any(s["members"] == membership for s in assessed["sets"]):
        raise ValueError(
            "Selected comparison membership does not satisfy its declared requirements."
        )
    return selected
