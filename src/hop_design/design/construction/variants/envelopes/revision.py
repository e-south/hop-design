"""Apply explicit permission changes without changing molecular or preservation intent."""

from typing import Any

from hop_design.models.construction.discovery.request import ScaffoldDiscoveryRequest
from hop_design.models.construction.variants.envelope import (
    ENVELOPE_FIELDS,
    ScaffoldEnvelopeRevision,
)
from hop_design.serialization import canonical_json_bytes


def _parent(value: dict[str, Any], path: str) -> tuple[dict[str, Any], str]:
    keys = path.split(".")
    for key in keys[:-1]:
        nested = value.get(key)
        if not isinstance(nested, dict):
            raise ValueError(f"Envelope field {path} is unavailable for this product.")
        value = nested
    return value, keys[-1]


def editable_envelope(request: ScaffoldDiscoveryRequest) -> list[dict[str, Any]]:
    """Expose current permissions; null means a bounded free domain where supported."""
    value = request.model_dump(mode="json", by_alias=True)
    result = []
    for field in ENVELOPE_FIELDS:
        try:
            parent, key = _parent(value, field.path)
        except ValueError:
            continue
        result.append({**field.model_dump(mode="json"), "value": parent.get(key)})
    return result


def revise_request(
    request: ScaffoldDiscoveryRequest, revision: dict[str, Any]
) -> tuple[ScaffoldDiscoveryRequest, list[dict[str, Any]]]:
    specification = ScaffoldEnvelopeRevision.model_validate_json(canonical_json_bytes(revision))
    value = request.model_dump(mode="json", by_alias=True)
    labels = {f.path: f.label for f in ENVELOPE_FIELDS}
    changes: list[dict[str, Any]] = []
    for change in specification.changes:
        parent, key = _parent(value, change.path)
        changes.append(
            {
                "path": change.path,
                "label": labels[change.path],
                "before": parent.get(key),
                "after": change.value,
            }
        )
        parent[key] = change.value
    # Re-run the complete source contract, including cross-field constraints.
    value["schema"] = (
        "hop.scaffold-discovery/v6"
        if value.get("receiving_end_pairs")
        else "hop.scaffold-discovery/v5"
    )
    revised = ScaffoldDiscoveryRequest.model_validate_json(canonical_json_bytes(value))
    normalized = revised.model_dump(mode="json", by_alias=True)
    for record in changes:
        parent, key = _parent(normalized, record["path"])
        record["after"] = parent.get(key)
    return revised, changes
