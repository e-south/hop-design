"""Filter complete witnesses and project replacement choices without molecular recombination."""

from typing import Any

from hop_design.models.construction.stage_controls import ResolvedStageControl
from hop_design.models.construction.variants.query import (
    PreservedMolecularProperty,
    PreservedSurroundings,
    ScaffoldVariantQuery,
)
from hop_design.serialization import canonical_json_bytes, sha256_digest

from ..comparisons.controls import assess_stage_controls
from .choice_space import choice_space
from .coverage import conditional_interface_coverage
from .parameters.filter import conditional_availability, selection_reasons


def _control_reasons(
    option: dict[str, Any],
    reference: dict[str, Any],
    controls: tuple[PreservedMolecularProperty, ...],
) -> list[dict[str, Any]]:
    reasons = []
    for control in controls:
        if control.property == "product_identity":
            status = (
                "shared"
                if option["molecular_identity"][control.stage]
                == reference["molecular_identity"][control.stage]
                else "different"
            )
        else:
            assessment = assess_stage_controls(
                (
                    ResolvedStageControl(
                        stage=control.stage,
                        property=control.property,
                        scope="set",
                        members=("reference", "candidate"),
                    ),
                ),
                {"reference": reference["stage_facts"], "candidate": option["stage_facts"]},
            )[0]
            status = assessment["status"]
        if status != "shared":
            reasons.append(
                {
                    "kind": "preserved_property",
                    "stage": control.stage,
                    "property": control.property,
                    "status": status,
                }
            )
    return reasons


def _pin_reasons(
    option: dict[str, Any], query: ScaffoldVariantQuery, *, omit_focus: bool = False
) -> list[dict[str, Any]]:
    reasons = []
    for pin in query.pins:
        if omit_focus and pin.neighborhood == query.focus:
            continue
        variant = option["variants"][query.stage][pin.neighborhood]
        if variant is None or variant["variant_id"] not in pin.variant_ids:
            reasons.append(
                {
                    "kind": "neighborhood_pin",
                    "neighborhood": pin.neighborhood,
                    "status": "unassessed" if variant is None else "different",
                }
            )
    return reasons


def surroundings_reasons(
    option: dict[str, Any], reference: dict[str, Any], controls: tuple[PreservedSurroundings, ...]
) -> list[dict[str, str]]:
    reasons = []
    for control in controls:
        for neighborhood, value in option["variants"][control.stage].items():
            if neighborhood == control.except_neighborhood:
                continue
            expected = reference["variants"][control.stage][neighborhood]
            status = (
                "unassessed"
                if value is None or expected is None
                else "shared"
                if value == expected
                else "different"
            )
            if status != "shared":
                reasons.append(
                    {
                        "kind": "preserved_surroundings",
                        "stage": control.stage,
                        "neighborhood": neighborhood,
                        "status": status,
                    }
                )
    return reasons


def molecular_changes(
    option: dict[str, Any], reference: dict[str, Any] | None, stage: str
) -> dict[str, Any]:
    if reference is None:
        return {"status": "no_reference", "molecular_neighborhoods": [], "material_roles": []}
    unassessed = [
        name
        for name, value in option["variants"][stage].items()
        if value is None or reference["variants"][stage][name] is None
    ]
    return {
        "status": "partly_unassessed" if unassessed else "assessed",
        "unassessed_neighborhoods": unassessed,
        "molecular_neighborhoods": [
            name
            for name, value in option["variants"][stage].items()
            if name not in unassessed and value != reference["variants"][stage][name]
        ],
        "material_roles": sorted(
            name
            for name in set(option["material_roles"]) | set(reference["material_roles"])
            if option["material_roles"].get(name) != reference["material_roles"].get(name)
        ),
    }


def query_summary(
    metadata: dict[str, Any], options: list[dict[str, Any]], query: ScaffoldVariantQuery
) -> dict[str, Any]:
    query = query.canonical()
    if query.result_digest != metadata["result_digest"]:
        raise ValueError("Stale exploration result digest; query the admitted result revision.")
    query.validate_membership(
        metadata["result_digest"], (o["materialized_realization_id"] for o in options)
    )
    by_label = {o["label"]: o for o in options}
    if query.reference is not None and query.reference not in by_label:
        raise ValueError("Unknown fixed comparison reference.")
    reference = by_label.get(query.reference)
    for pin in query.pins:
        known = {
            v["variant_id"]
            for o in options
            if (v := o["variants"][query.stage][pin.neighborhood]) is not None
        }
        if set(pin.variant_ids) - known:
            raise ValueError(
                "Unknown or wrong-stage neighborhood variant; "
                "no permission or feasibility is inferred."
            )
    eligible: list[str] = []
    excluded: list[dict[str, Any]] = []
    groups: dict[str, list[str]] = {}
    variants: dict[str, Any] = {}
    consequences: list[dict[str, Any]] = []
    coordinate_eligible: list[str] = []
    all_coordinates = choice_space(options, list(by_label), query.stage, metadata, query.parameters)
    coordinates = {p["option_label"]: p["values"] for p in all_coordinates["paths"]}
    for option in options:
        controls = (
            _control_reasons(option, reference, query.controls)
            if query.controls and reference is not None
            else []
        )
        if reference is not None:
            controls.extend(surroundings_reasons(option, reference, query.surroundings))
        if not query.includes_preparation(option["materialized_realization_id"]):
            controls.append({"kind": "preparation_membership", "status": "outside_group"})
        reasons = controls + _pin_reasons(option, query)
        label = option["label"]
        if not reasons:
            coordinate_eligible.append(label)
        parameter_reasons = selection_reasons(coordinates[label], query.parameters)
        reasons.extend(parameter_reasons)
        identity = option["molecular_identity"][query.stage]
        if reasons:
            excluded.append({"label": label, "reasons": reasons})
        else:
            eligible.append(label)
            groups.setdefault(identity, []).append(label)
        if (
            not controls
            and not parameter_reasons
            and not _pin_reasons(option, query, omit_focus=True)
        ):
            variant = option["variants"][query.stage][query.focus]
            if variant is not None:
                group = variants.setdefault(
                    variant["variant_id"], {**variant, "option_labels": [], "product_ids": []}
                )
                group["option_labels"].append(label)
                if identity not in group["product_ids"]:
                    group["product_ids"].append(identity)
        consequences.append({"label": label, **molecular_changes(option, reference, query.stage)})
    for path in all_coordinates["paths"]:
        path["eligible_under_preserved_controls"] = path["option_label"] in coordinate_eligible
    all_coordinates["scope"] = "admitted_pool_with_explicit_eligibility"
    all_coordinates["availability"] = conditional_availability(
        [p for p in all_coordinates["paths"] if p["eligible_under_preserved_controls"]],
        all_coordinates["axes"],
        query.parameters,
    )
    return {
        "schema": "hop.scaffold-variant-choices/v1",
        "neighborhoods": _neighborhoods(options, eligible, query.stage),
        "query": query.model_dump(mode="json", by_alias=True),
        "query_digest": sha256_digest(canonical_json_bytes(query)),
        "status": "options_available" if eligible else "no_compatible_options_in_evaluated_pool",
        "scope": "evaluated_complete_options_only",
        "compatible_options": eligible,
        "choice_space": all_coordinates,
        "products": [
            {"stage": query.stage, "molecule_id": identity, "option_labels": labels}
            for identity, labels in groups.items()
        ],
        "variants": list(variants.values()),
        "preparations": [
            {k: o[k] for k in ("label", "molecular_identity", "interface", "methods")}
            for o in options
        ],
        "interface_coverage": conditional_interface_coverage(metadata, eligible),
        "excluded_options": excluded,
        "changes": consequences,
        "selected_product": None,
        "coverage": metadata["coverage"],
        "examined_failures": metadata["examined_failures"],
        "local_coverage": metadata["local_coverage"],
        "producer": metadata["producer"],
    }


def _neighborhoods(
    options: list[dict[str, Any]], eligible: list[str], stage: str
) -> dict[str, Any]:
    result = {}
    for name in ("loop", "closing", "assembly", "stem", "interfaces"):
        variants = {
            v["variant_id"]
            for o in options
            if o["label"] in eligible
            and (v := o["variants"][stage][name]) is not None
            and v["sequences"]
        }
        count = len(variants)
        result[name] = {
            "status": "unavailable" if not count else "fixed" if count == 1 else "variable",
            "variant_count": count,
        }
    return result
