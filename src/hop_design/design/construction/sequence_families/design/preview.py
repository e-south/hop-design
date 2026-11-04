"""Resolve a bounded family once without forcing receiving-end words."""

import json
from pathlib import Path
from typing import Any, cast

from hop_design.design.source_documents import load_source_mapping
from hop_design.export.publication import ProtectedRoot
from hop_design.models.construction.intents.family import ConstructionFamilyIntent
from hop_design.models.construction.source import _contains_internal_schema_name
from hop_design.serialization import canonical_json_bytes, sha256_digest

from ...intents.resolve import ResolvedDesignRequest, resolve_design_request
from ...packets.capture import capture_packet
from ..prepare import exact_members


def family_mapping(source: str | Path | dict[str, Any]) -> dict[str, Any] | None:
    value = load_source_mapping(source) if isinstance(source, (str, Path)) else source
    if value.get("schema") != "hop.construction-family-intent/v1":
        return None
    if _contains_internal_schema_name(value):
        raise ValueError("Use external schema fields for a design family.")
    return value


def resolve_family(source: str | Path | dict[str, Any]) -> ResolvedDesignRequest:
    value = family_mapping(source)
    request = ConstructionFamilyIntent.model_validate_json(canonical_json_bytes(value))
    roots: tuple[ProtectedRoot, ...] = (
        () if isinstance(source, dict) else (ProtectedRoot.capture(source),)
    )
    if isinstance(request.context, str) and isinstance(source, (str, Path)):
        path = Path(source).parent / request.context
        if path.is_file():
            value = {
                **request.model_dump(mode="json", by_alias=True),
                "context": load_source_mapping(path),
            }
            request = ConstructionFamilyIntent.model_validate_json(canonical_json_bytes(value))
            roots += (ProtectedRoot.capture(path),)
    members = []
    permissions = None
    for name, stem in exact_members(request.stem_arm):
        resolved = resolve_design_request(request.exact_intent(stem))
        summary = json.loads(resolved.json_bytes)
        permissions = summary["permissions"]
        members.append(
            {
                "name": name,
                "stem_arm": stem,
                "request": {
                    **summary["intent"],
                    "context": permissions,
                },
            }
        )
        roots += resolved._roots
    captured = {**request.model_dump(mode="json", by_alias=True), "context": permissions}
    data = canonical_json_bytes(captured)
    summary = {
        "schema": "hop.design-family-preview/v1",
        "intent": captured,
        "request_digest": sha256_digest(data),
        "required_members": len(members),
        "members": members,
        "execution": "not_started",
        "shared_properties": list(request.shared_properties),
        "shared_material_roles": list(request.shared_material_roles),
        "max_total_evaluations": request.max_total_evaluations,
        "pooled_library": "not_assessed",
    }
    packet = ResolvedDesignRequest._create(
        {"family-request.json": data},
        summary,
        f"# Required stem family\n\n{len(members)} required exact stems; no search performed.\n\n"
        "Each member uses the same optional requirements and construction permissions. "
        "Shared flanks and materials are verified on explicit selection. "
        "This requests separate exact preparations; pooled processing is not assessed.\n",
    )
    object.__setattr__(packet, "_roots", roots)
    return packet


def admit_preview(root: Path) -> dict[str, Any]:
    capture_packet(root / "family", schema="hop.resolved-design-request-packet/v1")
    _, files = capture_packet(
        root / "family/intent", schema="hop.resolved-design-request-packet/v1"
    )
    rebuilt = resolve_family(json.loads(files["family-request.json"]))
    if dict(rebuilt._files) != files:
        raise ValueError("Saved family preview disagrees with its required exact stems.")
    return cast(dict[str, Any], json.loads(rebuilt.json_bytes))
