"""Current display names over compatible captured definitions; facts stay unchanged."""

from typing import Any

from hop_design.models.construction.variants.parameters import PARAMETERS, parameter_definition
from hop_design.serialization import canonical_json_bytes, sha256_digest

_CURRENT = {p.key: p.model_dump(mode="json") for p in PARAMETERS}
LABEL_CATALOG_DIGEST = sha256_digest(canonical_json_bytes(_CURRENT))


def parameter_labels(
    definitions: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Rename only when every recorded definition field other than its name agrees.

    Unknown or incompatible definitions retain their own wording, with an explicit
    presentation notice. Nodes, values, units, boundaries and source objects are
    never rewritten. The receipt explains changes in independently rendered views.
    """
    projected, renamed, retained = [], [], []
    for source in definitions:
        key = source["key"]
        current = _CURRENT.get(key)
        if current is None:
            try:
                current = parameter_definition(key).model_dump(mode="json")
            except ValueError:
                projected.append(source)
                retained.append({"key": key, "reason": "unknown_parameter"})
                continue
        differences = [
            field
            for field, value in current.items()
            if field != "label" and source.get(field) != value
        ]
        if differences:
            projected.append(source)
            retained.append({"key": key, "reason": "definition_differs", "fields": differences})
        elif source["label"] != current["label"]:
            projected.append({**source, "label": current["label"]})
            renamed.append(
                {"key": key, "captured_label": source["label"], "label": current["label"]}
            )
        else:
            projected.append(source)
    return projected, {
        "schema": "hop.parameter-display-labels/v1",
        "catalog_digest": LABEL_CATALOG_DIGEST,
        "renamed": renamed,
        "retained": retained,
    }


def display_parameters(answer: dict[str, Any]) -> dict[str, Any]:
    """Project browser metadata without copying the complete preparation rows."""
    axes, receipt = parameter_labels(answer["axes"])
    return {**answer, "axes": axes, "parameter_label_projection": receipt}
