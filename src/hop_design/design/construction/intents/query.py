"""Context-aware refinement; preserve predicate identity and reject contradictions."""

from typing import Any

from hop_design.models.construction.surveys.query import InterfaceSurveyQuery
from hop_design.models.construction.variants.parameters import (
    ParameterSelection,
    parameter_definition,
)
from hop_design.models.enzymes import EnzymeProvisioningPolicy
from hop_design.serialization import canonical_json_bytes

from .methods import METHOD_ROLES, resolve_method_ids


def parameters_permitted(query: InterfaceSurveyQuery, axes: list[dict[str, Any]]) -> bool:
    """Only a declared domain can rule out further matching preparations."""
    domains = {axis["key"]: axis["domain"] for axis in axes}
    return all(
        "values" not in domains.get(p.key, {})
        or any(p.accepts(value) for value in domains[p.key]["values"])
        for p in query.parameters
    )


def resolve_query(query: InterfaceSurveyQuery, permissions: dict[str, Any]) -> InterfaceSurveyQuery:
    selections = []
    for selection in query.parameters:
        role = selection.key.removesuffix("_method")
        if selection.key.endswith("_method") and role in METHOD_ROLES:
            policy = EnzymeProvisioningPolicy.model_validate_json(
                canonical_json_bytes(
                    {
                        "catalog": permissions["enzyme_catalog"],
                        **permissions[role]["enzymes"],
                    }
                )
            )
            assert selection.values is not None
            names = tuple(str(value) for value in selection.values)
            selection = selection.model_copy(
                update={
                    "values": resolve_method_ids(names, role=role, policy=policy),
                }
            )
        selections.append(selection)
    resolved = query.model_copy(update={"parameters": tuple(selections)})
    _validate_equivalents(resolved.parameters)
    return resolved


def _validate_equivalents(selections: tuple[ParameterSelection, ...]) -> None:
    """Intersect equivalent predicates without rewriting historical selection bytes.

    Both predicates remain explicit and are evaluated conjunctively. Keeping their
    keys and bounds preserves valid saved queries, including lone alias keys.
    """
    by_key = {selection.key: selection for selection in selections}
    checked: set[frozenset[str]] = set()
    for selection in selections:
        definition = parameter_definition(selection.key)
        keys = frozenset({selection.key, *definition.equivalent_measurements})
        if keys in checked:
            continue
        checked.add(keys)
        group = [by_key[key] for key in sorted(keys) if key in by_key]
        if len(group) < 2:
            continue
        exact = next((p.values for p in group if p.values is not None), None)
        if exact is not None:
            compatible = any(all(p.accepts(value) for p in group) for value in exact)
        else:
            minimum = max(p.minimum for p in group if p.minimum is not None)
            maximum = min(p.maximum for p in group if p.maximum is not None)
            compatible = minimum <= maximum
        if not compatible:
            declarations = "; ".join(
                f"{p.key}={p.values if p.values is not None else (p.minimum, p.maximum)}"
                for p in group
            )
            raise ValueError(
                f"Equivalent {definition.stage} measurements {declarations} conflict. "
                "Edit these predicates to overlap; further search cannot reconcile them."
            )
