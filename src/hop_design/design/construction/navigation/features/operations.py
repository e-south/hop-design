"""Describe existing feature operations without searching or testing feasibility."""

from hop_design.models.construction.intents.revision import CONTEXT_PARAMETER_FIELDS
from hop_design.models.construction.variants.applicability import inapplicable_reason
from hop_design.models.construction.variants.objective import DIVERSITY_PARAMETERS
from hop_design.models.construction.variants.parameter_contract import ParameterDefinition

from ...intents.methods import METHOD_ROLES
from ..types import Record


def _operation(available: bool, reason: str, **details: object) -> Record:
    return {"available": available, "reason": reason, **details}


def _revision(definition: ParameterDefinition, *, live: bool, permissions: Record) -> Record:
    if not live:
        return _operation(
            False, "This frozen edition cannot revise permissions; open its discovery."
        )
    key = definition.canonical_key
    if key in CONTEXT_PARAMETER_FIELDS:
        field = CONTEXT_PARAMETER_FIELDS[key]
        region = field.path.split(".")[1]
        if isinstance(permissions.get(region), dict):
            return _operation(
                True,
                "Preview changed permissions; authored product requirements remain fixed.",
                field="parameters",
                parameter=key,
            )
    if key in {"left_gap", "right_gap"}:
        return _operation(
            True,
            "Revise joint left/right end placements, not one independent gap.",
            field="end_placements",
        )
    role = key.removesuffix("_method")
    if key.endswith("_method") and role in METHOD_ROLES and isinstance(permissions.get(role), dict):
        return _operation(
            True,
            "Preview the permitted characterized methods for this role.",
            field=f"methods.{role}",
        )
    if key in {"left_end_word", "right_end_word", "left_end_polarity", "right_end_polarity"}:
        return _operation(
            False,
            "Change receiving ends through product intent or its interface context.",
        )
    return _operation(
        False,
        "This measurement has no independent permission edit; inspect its contributing features.",
    )


def parameter_operations(
    definition: ParameterDefinition, *, product: str, permissions: Record, live: bool
) -> Record:
    """Availability means an operation is supported, never that a solution exists."""
    reason = inapplicable_reason(definition, product)
    if reason:
        return {
            "inspect": _operation(True, reason),
            **{
                name: _operation(False, reason)
                for name in ("filter", "revise", "prefer", "preserve", "diversify")
            },
        }
    stage = (
        "hairpin"
        if definition.stage in {"hairpin", "folded"}
        else "endpoint"
        if definition.stage == "released_insert"
        else None
    )
    preserve = (
        _operation(
            True,
            "Keep other regions' sequence, contacts and chemistry at this stage. "
            "Requires an exact reference and verification.",
            requires_reference=True,
            arguments={"stage": stage, "except_neighborhood": definition.neighborhood},
        )
        if stage is not None
        else _operation(
            False,
            "Preserve surroundings on a product neighborhood, not this processing measurement.",
        )
    )
    return {
        "inspect": _operation(True, "Read the recorded meaning, stage and boundaries."),
        "filter": _operation(
            True, "Filter complete choices; no new search or relaxed requirements."
        ),
        "revise": _revision(definition, live=live, permissions=permissions),
        "prefer": _operation(
            False,
            "Per-feature ranking is not implemented; a filter is a requirement, not a preference.",
        ),
        "preserve": preserve,
        "diversify": _operation(
            live and definition.canonical_key in DIVERSITY_PARAMETERS,
            "Target this dimension in a new search objective; alternatives are not guaranteed."
            if live and definition.canonical_key in DIVERSITY_PARAMETERS
            else "New search belongs to the original discovery."
            if not live
            else "Diversity-directed search does not target this measurement.",
            parameter=definition.canonical_key,
        ),
    }
