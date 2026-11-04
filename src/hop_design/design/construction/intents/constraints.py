"""Intersect desired molecular properties with one explicit construction context."""

import json
from typing import Any

from hop_design.models.construction.intents.request import (
    ConstructionContext,
    ConstructionIntent,
    HairpinConstructionContext,
)
from hop_design.models.construction.scaffold import (
    HairpinScaffoldRequirements,
    constrain_foldback_geometry,
)
from hop_design.models.enzymes import EnzymeProvisioningPolicy

from .methods import METHOD_ROLES, resolve_method_ids


def apply_constraints(
    intent: ConstructionIntent,
    context: ConstructionContext | HairpinConstructionContext,
    permissions: dict[str, Any],
) -> dict[str, str]:
    """Narrow existing permissions; leave coupled feasibility to the ordinary compiler."""
    provenance = dict.fromkeys(permissions, "context")
    if intent.scaffold is not None:
        existing = context.whole_route_constraints.hairpin_scaffold
        if existing is not None:
            # The same intersection rule applies whether the setting came from a context or user.
            current = existing.model_dump(mode="json", exclude_none=True)
            for dimension, requirement in intent.scaffold.model_dump(
                mode="json", exclude_none=True
            ).items():
                previous = current.get(dimension, requirement)
                minimum = max(previous["minimum"], requirement["minimum"])
                maximum = min(previous["maximum"], requirement["maximum"])
                if minimum > maximum:
                    raise ValueError(
                        f"Requested {dimension} conflicts with context scaffold requirements."
                    )
                current[dimension] = {"minimum": minimum, "maximum": maximum}
        else:
            current = intent.scaffold.model_dump(mode="json", exclude_none=True)
        permissions["whole_route_constraints"]["hairpin_scaffold"] = current
        provenance["whole_route_constraints"] = "user_within_context"
    scaffold = permissions["whole_route_constraints"].get("hairpin_scaffold")
    required = (
        HairpinScaffoldRequirements.model_validate_json(json.dumps(scaffold))
        if scaffold is not None
        else None
    )
    geometry = constrain_foldback_geometry(
        context.foldback.geometry,
        maximum=context.foldback.max_retained_overhead_nt,
        requirements=required,
    ).model_dump(mode="json")
    if intent.loop_words is not None:
        permitted = context.foldback.geometry.loop_sequences
        outside = [
            w
            for w in intent.loop_words
            if (
                (permitted is not None and w not in permitted)
                or len(w) < geometry["minimum_loop_length_nt"]
                or (geometry["loop_lengths_nt"] and len(w) not in geometry["loop_lengths_nt"])
            )
        ]
        if outside:
            raise ValueError(f"Requested loop words conflict with foldback permissions: {outside}.")
        geometry["loop_sequences"] = list(intent.loop_words)
        geometry["loop_lengths_nt"] = sorted({len(w) for w in intent.loop_words})
    permissions["foldback"]["geometry"] = geometry
    if intent.scaffold is not None or intent.loop_words is not None:
        provenance["foldback"] = "user_within_context"
    if intent.end_placements is not None:
        if not isinstance(context, ConstructionContext) or not set(intent.end_placements).issubset(
            context.placements
        ):
            raise ValueError("Requested joint end placements are not permitted by the context.")
        permissions["placements"] = [p.model_dump(mode="json") for p in intent.end_placements]
        provenance["placements"] = "user_within_context"
    _methods(intent, context, permissions, provenance)
    return provenance


def _methods(
    intent: ConstructionIntent,
    context: ConstructionContext | HairpinConstructionContext,
    permissions: dict[str, Any],
    provenance: dict[str, str],
) -> None:
    for role, purpose in METHOD_ROLES.items():
        names = getattr(intent.methods, role)
        if names is None:
            continue
        job = getattr(context, role, None)
        if job is None:
            raise ValueError(f"The {context.product} context does not use a {role} method.")
        policy = EnzymeProvisioningPolicy(
            catalog=context.enzyme_catalog, **job.enzymes.model_dump()
        )
        selected = list(resolve_method_ids(names, role=role, policy=policy))
        permissions[role]["enzymes"]["role_restrictions"] = [
            r
            for r in permissions[role]["enzymes"]["role_restrictions"]
            if r["role"] != purpose.value
        ] + [{"role": purpose.value, "allowed_enzyme_ids": selected}]
        provenance[role] = "user_within_context"
