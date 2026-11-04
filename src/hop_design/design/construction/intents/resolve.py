"""Resolve optional intent without performing search or weakening exact compilation."""

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

from hop_design.models.construction.product_request import ProductRequest
from hop_design.models.construction.surveys.request import InterfaceSurveyRequest
from hop_design.serialization import canonical_json_bytes, sha256_digest

from ..packets.publication import ConstructionPacket, SourceBoundConstructionPacket
from ..surveys.branches import SurveyBranches
from .constraints import apply_constraints
from .context import load_intent_context
from .hairpin_request import hairpin_request
from .preference import capture_preference


@dataclass(frozen=True, init=False, repr=False)
class ResolvedDesignRequest(SourceBoundConstructionPacket):
    """Authored intent, explicit molecular permissions and their resolved request."""

    _packet_schema: ClassVar[str] = "hop.resolved-design-request-packet/v1"

    def write(self, destination: str | Path) -> Path:
        if self._roots:
            return super().write(destination)
        return ConstructionPacket.write(self, destination)


def resolve_design_request(
    request: str | Path | dict[str, Any],
) -> ResolvedDesignRequest:
    """Resolve an intent mapping or file; return a write-free, inspectable packet."""
    from ..sequence_families.design.preview import family_mapping, resolve_family

    if family_mapping(request) is not None:
        return resolve_family(request)
    intent, context, origin, roots = load_intent_context(request)
    preference = None
    preference_files: dict[str, bytes] = {}
    if intent.prefer_preparation is not None:
        base = Path(request).parent if isinstance(request, (str, Path)) else Path.cwd()
        portable, preference, preference_files, preference_roots = capture_preference(
            intent.prefer_preparation, base
        )
        intent = intent.model_copy(update={"prefer_preparation": portable})
        roots += preference_roots
    context_data = context.model_dump(mode="json", by_alias=True)
    permission_keys = set(context_data) - {"schema", "context_id", "description", "product"}
    permissions = {key: deepcopy(context_data[key]) for key in permission_keys}
    provenance = apply_constraints(intent, context, permissions)
    targets = {
        side + "_words": [word] if isinstance(word, str) else word
        for side in ("left", "right")
        for word in (getattr(intent.ends, side) if intent.ends else None,)
    }
    resolved: InterfaceSurveyRequest | ProductRequest
    if intent.product == "released_insert":
        resolved = InterfaceSurveyRequest.model_validate_json(
            canonical_json_bytes(
                {
                    "schema": "hop.interface-survey/v2",
                    "stem_arm": intent.stem_arm,
                    "targets": targets,
                    **permissions,
                    **(
                        {"preferred_preparation": preference.model_dump(mode="json")}
                        if preference is not None
                        else {}
                    ),
                }
            )
        )
        if not SurveyBranches(resolved).release_methods:
            raise ValueError(
                "Released-insert method permissions conflict: basal.enzymes and "
                "release.enzymes share no end-generation method. Permit the same release "
                "method in both fields, or choose a jointly permitted method."
            )
    else:
        resolved = hairpin_request(intent.stem_arm, intent.product, permissions)
    effective = resolved.model_dump(mode="json", by_alias=True)
    authored = intent.model_dump(mode="json", by_alias=True)
    summary = {
        "schema": "hop.resolved-design-request/v1",
        "intent": authored,
        "context": {
            "id": context.context_id,
            "origin": origin,
            "digest": sha256_digest(canonical_json_bytes(context_data)),
            "description": context.description,
        },
        "permissions": context_data,
        "effective_request": effective,
        "provenance": {
            "stem_arm": "user",
            "product": "user",
            "targets": "user" if intent.ends else "unconstrained",
            **provenance,
        },
        "search_required": True,
    }
    packet = ResolvedDesignRequest._create(
        {
            "intent.json": canonical_json_bytes(authored),
            "context.json": canonical_json_bytes(context_data),
            "request.json": canonical_json_bytes(effective),
            **preference_files,
        },
        summary,
        "# Discover complete designs\n\n"
        f"Product: {intent.product}. Stem: {len(intent.stem_arm)} nt.\n\n"
        "No search has been performed. End constraints apply only to released inserts.\n\n"
        f"Construction context: {context.context_id}. {context.description}\n\n"
        "[Effective request](request.json) · [All permissions](context.json) · "
        "[Authored intent](intent.json)\n",
    )
    object.__setattr__(packet, "_roots", roots)
    return packet
