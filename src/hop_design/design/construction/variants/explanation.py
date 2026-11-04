"""Explain admitted choices without selecting a molecule or starting a search."""

from typing import Any

from hop_design.models.construction.intents.explanation import (
    AvailableDesign,
    DesignAction,
    DesignExplanation,
    DesignParameter,
    DesignStatus,
)
from hop_design.models.construction.variants.applicability import inapplicable_reason
from hop_design.models.construction.variants.parameters import PARAMETERS, parameter_definition

PRODUCT_LABELS = {
    "released_insert": "released duplex insert",
    "hairpin": "direct hairpin",
    "adapter_ligated_hairpin": "adapter-ligated hairpin",
    "hairpin_pcr_duplex": "hairpin-PCR duplex",
}


def explain_choices(
    resolution: dict[str, Any],
    result: dict[str, Any],
    *,
    interface_excluded: bool = False,
    can_continue: bool | None = None,
) -> dict[str, Any]:
    product = resolution["intent"]["product"]
    matches = result["matching_preparations"]
    distinct = {p["materialized_realization_id"]: p for p in result["paths"] if p["matches"]}
    coverage = result["coverage"]
    excluded = interface_excluded or _excluded(result)
    actions: list[DesignAction] = []
    status: DesignStatus
    if matches:
        status = "choices_available"
        noun = "preparation" if matches == 1 else "preparations"
        headline = f"{matches} complete {noun} available for your {PRODUCT_LABELS[product]}."
        guidance = "Choose a preparation to inspect its complete route and retrieve its oligos."
        actions.append("select")
    elif excluded:
        status = "excluded_within_scope"
        headline = "No construction satisfies this request within the saved context."
        guidance = (
            "Inspect the saved permissions and revise the request explicitly; "
            "continuing unchanged cannot resolve this exclusion."
        )
        actions.extend(("inspect_permissions", "revise_request"))
    else:
        status = "no_recorded_match"
        headline = f"No recorded preparation matches your {PRODUCT_LABELS[product]} query."
        guidance = (
            "Refine the filter to inspect other recorded choices. "
            "Unobserved alternatives remain unresolved."
        )
        actions.extend(("refine_query", "inspect_permissions"))
    remaining = coverage.get("unresolved_pairs", 0) if can_continue is None else can_continue
    if result["query"].get("membership") is not None:
        remaining = False
        guidance += (
            " This query has an exact membership filter; "
            "clear or revise it to explore another group."
        )
    if not excluded and remaining and (product == "released_insert" or can_continue is True):
        actions.append("continue_search")
    surroundings = result["query"].get("surroundings") or []
    # Native variant queries may preserve several stages; intent refinement has
    # one control. Normalize this presentation input without changing either query.
    controls = [surroundings] if isinstance(surroundings, dict) else surroundings
    guidance = (
        "".join(
            (
                f"The {control['except_neighborhood'].replace('_', ' ')} may vary; "
                "other neighborhoods remain unchanged at the "
                f"{'hairpin' if control['stage'] == 'hairpin' else PRODUCT_LABELS[product]}. "
            )
            for control in controls
        )
        + guidance
    )
    answer = DesignExplanation(
        product=product,
        context_id=resolution["context"]["id"],
        status=status,
        headline=headline,
        guidance=guidance,
        matching_preparations=matches,
        matching_products={
            stage: len({p["molecular_identity"][stage] for p in distinct.values()})
            for stage in ("hairpin", "endpoint")
        },
        choices=tuple(
            AvailableDesign(
                materialized_realization_id=identity,
                values=path["values"],
                methods=tuple(m["name"] for m in path["methods"]),
            )
            for identity, path in list(distinct.items())[:5]
        ),
        actions=tuple(actions),
        coverage=coverage,
        parameters=parameter_capabilities(product, result),
    )
    return answer.model_dump(mode="json", by_alias=True)


def _excluded(result: dict[str, Any]) -> bool:
    """Use recorded exclusion evidence, never absence of a matching witness."""
    coverage = result["coverage"]
    if (
        coverage.get("target_pairs", 0)
        and coverage.get("excluded_pairs") == coverage["target_pairs"]
    ):
        return True
    axes = {axis["key"]: axis for axis in result["axes"]}
    for selection in result["query"].get("parameters", []):
        if selection["key"] not in {"left_end_word", "right_end_word"} and not result.get(
            "all_preparations_enumerated"
        ):
            continue
        values = selection.get("values")
        nodes = {n["value"]: n["state"] for n in axes.get(selection["key"], {}).get("nodes", [])}
        if values and all(nodes.get(value) == "excluded_in_scope" for value in values):
            return True
    return False


def parameter_capabilities(product: str, result: dict[str, Any]) -> tuple[DesignParameter, ...]:
    axes = {axis["key"]: axis for axis in result["axes"]}
    keys = dict.fromkeys([*(p.key for p in PARAMETERS), *axes])
    parameters = []
    for key in keys:
        definition = parameter_definition(key)
        reason = inapplicable_reason(definition, product)
        values = {p["values"][key] for p in result["paths"] if p["values"].get(key) is not None}
        parameters.append(
            DesignParameter(
                **definition.model_dump(),
                applicable=reason is None,
                reason=reason,
                declared_domain=axes.get(key, {}).get("domain", {"basis": "not_projected"}),
                observed_values=tuple(sorted(values)),
            )
        )
    return tuple(parameters)


def explain_variants(
    metadata: dict[str, Any], options: list[dict[str, Any]], summary: dict[str, Any]
) -> dict[str, Any]:
    by_label = {o["label"]: o for o in options}
    eligible = set(summary["compatible_options"])
    result = {
        "query": summary["query"],
        "coverage": summary["coverage"],
        "matching_preparations": len(eligible),
        "axes": [{**a, "domain": a["declared"]} for a in summary["choice_space"]["axes"]],
        "paths": [
            {
                **path,
                **{
                    key: by_label[path["option_label"]][key]
                    for key in ("materialized_realization_id", "molecular_identity", "methods")
                },
                "matches": path["option_label"] in eligible,
            }
            for path in summary["choice_space"]["paths"]
        ],
    }
    return explain_choices(
        {
            "intent": {
                "product": {
                    "ssdna_hairpin": "hairpin",
                    "clone_ready_duplex": "released_insert",
                    "adapter_ligated_hairpin": "adapter_ligated_hairpin",
                    "hairpin_pcr_duplex": "hairpin_pcr_duplex",
                }[metadata["endpoint"]]
            },
            "context": {"id": metadata["request_digest"]},
        },
        result,
    )
