"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/execution/context.py

Projects prepared request context and validates execution identities for shared consumers.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import json
from typing import Any, NotRequired, TypedDict

from pydantic import TypeAdapter, ValidationError

from hop_design.design.runtime import producer_identity
from hop_design.export.construction.request_execution import render_request_context
from hop_design.models.spec import ExactJunctionDesignSpec

from ..local_public import LocalNeighborhoodDiscovery
from ..product_request import PreparedConstructionRequest

_DESIGN_ID = TypeAdapter(ExactJunctionDesignSpec.model_fields["design_id"].rebuild_annotation())


class LocalSelection(TypedDict):
    foldback: LocalNeighborhoodDiscovery
    foldback_realization_id: str
    basal: NotRequired[LocalNeighborhoodDiscovery]
    basal_realization_id: NotRequired[str]


def validate_design_id(design_id: str) -> None:
    try:
        _DESIGN_ID.validate_python(design_id, strict=True)
    except ValidationError as error:
        raise ValueError(f"Invalid design_id: {error}") from error


def describe_request_context(
    prepared: PreparedConstructionRequest, *, continuation: str
) -> tuple[dict[str, Any], dict[str, str] | None, dict[str, object], str]:
    authored = json.loads(prepared.request_json_bytes)
    source = json.loads(prepared.source_json_bytes)
    component = authored.get("hairpin_basal_component")
    if source["composition"]["endpoint"] == "ssdna_hairpin" and component is None:
        raise ValueError("Hairpin execution requires an explicit hairpin_basal_component.")
    summary: dict[str, object] = {
        "schema": "hop.request-execution-report/v1",
        "continuation": continuation,
        "producer": producer_identity(),
        "endpoint": source["composition"]["endpoint"],
        "payload_nt": len(source["foldback"]["payload"]["payload"]["sequence"]),
        "requested_ends": authored["ends"],
        "local_coverage": {},
    }
    context = render_request_context(
        endpoint=source["composition"]["endpoint"],
        payload_nt=len(source["foldback"]["payload"]["payload"]["sequence"]),
        ends=authored["ends"],
    )
    return source, component, summary, context
