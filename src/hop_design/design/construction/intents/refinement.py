"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/intents/refinement.py

Admit public query mappings and bind preservation to verified variant references.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

import json
from pathlib import Path
from typing import Any

from hop_design.design.source_documents import load_source_mapping
from hop_design.models.construction.intents.refinement import DesignRefinementQuery
from hop_design.models.construction.surveys.query import InterfaceSurveyQuery
from hop_design.serialization import canonical_json_bytes, sha256_digest


def load_design_query(
    source: str | Path | dict[str, Any] | None,
) -> InterfaceSurveyQuery | DesignRefinementQuery:
    value = (
        load_source_mapping(source)
        if isinstance(source, str | Path)
        else {}
        if source is None
        else source
    )
    if not isinstance(value, dict):
        raise ValueError("Design query must be a mapping.")
    model = (
        DesignRefinementQuery
        if value.get("schema") == "hop.design-refinement/v1"
        else InterfaceSurveyQuery
    )
    return model.model_validate_json(canonical_json_bytes(value))


def reference_label(
    query: DesignRefinementQuery,
    *,
    effective_request: dict[str, Any],
    snapshot_digest: str,
    options: bytes,
) -> str:
    reference = query.reference
    if (
        reference.request_digest != sha256_digest(canonical_json_bytes(effective_request))
        or reference.snapshot_digest != snapshot_digest
    ):
        raise ValueError("Preservation reference belongs to a different discovery or snapshot.")
    matches = [
        o["label"]
        for o in json.loads(options)
        if o["materialized_realization_id"] == reference.materialized_realization_id
    ]
    if len(matches) != 1:
        raise ValueError("Preservation reference is not one exact preparation in this snapshot.")
    return str(matches[0])
