"""Unevaluated, request-bound views of coupled authoring fields."""

from __future__ import annotations

import hashlib
from typing import Any, TypedDict

from hop_design.models.construction.product_request import ProductRequest
from hop_design.serialization import canonical_json_bytes


class _FootprintBase(TypedDict):
    position_from_ligation: int
    source_base: str


class _BasalFacts(TypedDict):
    source_end_footprint: list[_FootprintBase]
    pairing_constraints: list[dict[str, Any]]
    minimum_adapter_annealing_nt: int | None
    max_noncanonical_pairs: int | None


class _PreviewFacts(TypedDict):
    authored_request_sha256: str
    endpoint: str
    ends: dict[str, Any] | None
    basal: _BasalFacts | None
    materialization: dict[str, Any]
    upstream_context_search_supported: bool


def _facts(request: ProductRequest, authored: bytes) -> _PreviewFacts:
    basal = request.basal
    return {
        "authored_request_sha256": hashlib.sha256(authored).hexdigest(),
        "endpoint": request.endpoint.value,
        "ends": None if request.ends is None else request.ends.model_dump(mode="json"),
        "basal": None
        if basal is None
        else {
            "source_end_footprint": [
                {"position_from_ligation": position, "source_base": base}
                for position, base in request.source_end_footprint()
            ],
            "pairing_constraints": [
                contact.model_dump(mode="json")
                for contact in request.expanded_pairing_constraints()
            ],
            "minimum_adapter_annealing_nt": basal.geometry.minimum_adapter_annealing_nt,
            "max_noncanonical_pairs": basal.geometry.max_noncanonical_pairs,
        },
        "materialization": request.materialization.model_dump(mode="json"),
        "upstream_context_search_supported": request.endpoint.value != "ssdna_hairpin",
    }


def _changes(before: object, after: object, field: str = "") -> list[dict[str, object]]:
    if before == after:
        return []
    if isinstance(before, dict) and isinstance(after, dict):
        return [
            change
            for key in sorted(before.keys() | after.keys())
            for change in _changes(before.get(key), after.get(key), f"{field}.{key}".lstrip("."))
        ]
    return [{"field": field, "before": before, "after": after}]


def preview_product_request(
    request: ProductRequest,
    authored: bytes,
    reference: tuple[ProductRequest, bytes] | None,
) -> tuple[bytes, str]:
    """Show explicit permissions and implied coordinates, never predicted success."""
    facts = _facts(request, authored)
    previous = None if reference is None else _facts(*reference)
    changes = (
        []
        if reference is None
        else _changes(reference[0].model_dump(mode="json"), request.model_dump(mode="json"))
    )
    preview = {
        "schema": "hop.construction-request-preview/v1",
        "evaluated": False,
        **facts,
        "reference": previous,
        "changes": changes,
    }
    lines = ["", "## Coupled authoring preview", "", "No discovery or construction has run."]
    basal = facts["basal"]
    if basal is not None:
        footprint = basal["source_end_footprint"]
        positions = [item["position_from_ligation"] for item in footprint]
        lines.append(
            f"Left-end source footprint (positions from ligation): {positions or 'unresolved'}."
        )
        lines.append(
            "Expanded pairing permissions (position: class): "
            + ", ".join(
                f"{c['position_from_ligation']}: {c['allowed_class']}"
                for c in basal["pairing_constraints"]
            )
            + "."
        )
        lines.append(
            f"Authored minimum adapter association: {basal['minimum_adapter_annealing_nt']} nt."
        )
        lines.append(f"Authored noncanonical-pair cap: {basal['max_noncanonical_pairs']}.")
    lines.append("Material modes and exact fixed specifications are retained in preview.json.")
    if not facts["upstream_context_search_supported"]:
        lines.append("Upstream context search is unsupported for the direct hairpin endpoint.")
    if previous is not None:
        lines += ["", "Changes from the explicitly supplied reference request:"]
        lines += [
            f"- {change['field']}: {change['before']} -> {change['after']}" for change in changes
        ]
        if not changes:
            lines.append("No semantic request fields changed.")
        old_basal = previous["basal"]
        if old_basal is not None and basal is not None:
            old = [c["position_from_ligation"] for c in old_basal["source_end_footprint"]]
            new = [c["position_from_ligation"] for c in basal["source_end_footprint"]]
            lines.append(f"Derived source footprint: {old} -> {new}.")
    lines.append("Feasibility and actual molecular contacts require complete-route evaluation.")
    return canonical_json_bytes(preview), "\n".join(lines) + "\n"
