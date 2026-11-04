"""One comparison intent reused from group discovery through exact membership selection."""

import json
from pathlib import Path
from typing import Any

from hop_design.design.source_documents import load_source_mapping
from hop_design.export.publication import ProtectedRoot
from hop_design.models.construction.options import ScaffoldComparisonRequest
from hop_design.models.construction.source import _contains_internal_schema_name


def read_comparison(path: str | Path) -> tuple[ScaffoldComparisonRequest, ProtectedRoot]:
    root = ProtectedRoot.capture(path)
    mapping = load_source_mapping(path)
    if _contains_internal_schema_name(mapping):
        raise ValueError("Comparison requests must use external 'schema' fields.")
    return ScaffoldComparisonRequest.model_validate_json(json.dumps(mapping)), root


def bind_comparison(
    request: ScaffoldComparisonRequest, choices: list[dict[str, Any]]
) -> dict[str, Any]:
    """Require exactly one explicitly chosen option per requested dimension combination."""
    bindings = []
    for member in request.members:
        matches = [
            o["label"]
            for o in choices
            if all(o["geometry"][k] == v for k, v in member.dimensions.items())
        ]
        if len(matches) != 1:
            raise ValueError(
                f"Comparison member {member.name} requires exactly one selected option."
            )
        bindings.append({"member": member.name, "option_label": matches[0]})
    if len(bindings) != len(choices):
        raise ValueError("Selected options include a molecule outside the requested comparison.")
    return {"comparison": request.model_dump(mode="json", by_alias=True), "membership": bindings}
