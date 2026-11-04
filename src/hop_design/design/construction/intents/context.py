"""Load one authored intention and its context before intersecting requirements."""

from importlib.resources import files
from pathlib import Path
from typing import Any

from hop_design.design.source_documents import load_source_mapping
from hop_design.export.publication import ProtectedRoot
from hop_design.models.construction.intents.request import (
    ConstructionContext,
    ConstructionIntent,
    HairpinConstructionContext,
)
from hop_design.models.construction.source import _contains_internal_schema_name
from hop_design.serialization import canonical_json_bytes


def load_intent_context(
    request: str | Path | dict[str, Any],
) -> tuple[
    ConstructionIntent,
    ConstructionContext | HairpinConstructionContext,
    str,
    tuple[ProtectedRoot, ...],
]:
    roots: tuple[ProtectedRoot, ...] = ()
    base = Path.cwd()
    if isinstance(request, (str, Path)):
        base = Path(request).parent
        roots = (ProtectedRoot.capture(request),)
        mapping = load_source_mapping(request)
    else:
        mapping = request
    if _contains_internal_schema_name(mapping):
        raise ValueError("Use the public schema field, not schema_id.")
    intent = ConstructionIntent.model_validate_json(canonical_json_bytes(mapping))
    context_model = (
        ConstructionContext if intent.product == "released_insert" else HairpinConstructionContext
    )
    defaults = {
        "released_insert": ("linear-source/v2", "linear-source-insert-v2.json"),
        "hairpin": ("direct-hairpin/v1", "direct-hairpin-v1.json"),
        "adapter_ligated_hairpin": ("adapter-hairpin/v1", "adapter-hairpin-v1.json"),
    }
    default_name, default_file = defaults[intent.product]
    packaged = {default_name: default_file}
    if intent.product == "released_insert":
        # An explicit older context retains its scientific domain. Saved requests
        # also embed their context and never inherit today's default on resume.
        packaged["linear-source/v1"] = "linear-source-insert-v1.json"
    if isinstance(intent.context, (ConstructionContext, HairpinConstructionContext)):
        context, origin = intent.context, "user"
    elif intent.context is None or intent.context in packaged:
        context_file = packaged[default_name if intent.context is None else intent.context]
        content = (
            files("hop_design").joinpath("assets/construction_contexts", context_file).read_bytes()
        )
        context, origin = context_model.model_validate_json(content), "packaged"
    else:
        path = base / intent.context
        context = context_model.model_validate_json(canonical_json_bytes(load_source_mapping(path)))
        roots += (ProtectedRoot.capture(path),)
        origin = "user"
    if context.product != intent.product:
        raise ValueError("Construction context must permit the intended product.")
    return intent, context, origin, roots
