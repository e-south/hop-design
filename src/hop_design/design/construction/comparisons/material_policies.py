"""Translate prior-material intentions through the existing fixed policy contracts."""

from typing import Any

from hop_design.models.construction.complete.composition_domain import validate_source_context
from hop_design.models.construction.complete.source_preparation.policy import (
    ConstrainedSourceSsdnaPolicy,
)
from hop_design.models.construction.discovery.request import ScaffoldDiscoveryRequest
from hop_design.serialization import canonical_json_bytes


def _location(materialization: dict[str, Any], role: str) -> tuple[dict[str, Any] | None, str]:
    if role == "source_ssdna":
        return materialization["source_preparation"], "source_ssdna"
    if role.startswith("source_materialization_"):
        return materialization["source_preparation"], role.removeprefix("source_materialization_")
    if role.startswith("endpoint_"):
        return materialization.get("endpoint_auxiliaries"), role.removeprefix("endpoint_")
    if materialization.get("adapter_ligation") is not None:
        return materialization, "adapter_ligation"
    return materialization.get("endpoint_auxiliaries"), "adapter"


def _policy_conflict(
    old: dict[str, Any], fixed: dict[str, Any], facts: dict[str, Any], role: str
) -> str | None:
    if old["mode"] == "fixed":
        key = "primer" if "primer" in fixed else "material"
        if old[key] != fixed[key]:
            return "The existing fixed material differs from the requested prior material."
    material = fixed.get("material", fixed.get("primer", {}).get("oligo"))
    for end in ("five_prime_end", "three_prime_end"):
        if end in old and old[end] != material[end]:
            return f"The prior material contradicts the declared {end} chemistry."
    if "primer" in fixed:
        primer = fixed["primer"]
        length = primer["annealing_length_nt"]
        if "annealing_length_nt" in old and old["annealing_length_nt"] != length:
            return "The prior primer differs from the declared annealing length."
        if (
            "min_annealing_length_nt" in old
            and not old["min_annealing_length_nt"] <= length <= old["max_annealing_length_nt"]
        ):
            return "The prior primer lies outside the declared annealing-length range."
        handle = material["sequence_5prime"][:-length]
        if old["mode"] != "fixed" and handle != old.get("five_prime_handle_sequence", ""):
            return "The prior primer differs from the declared five-prime handle."
    if "three_prime_handle_sequence" in old and not material["sequence_5prime"].endswith(
        old["three_prime_handle_sequence"]
    ):
        return "The prior adapter does not retain the declared three-prime handle."
    if role == "source_ssdna" and old["mode"] == "constrain":
        policy = ConstrainedSourceSsdnaPolicy.model_validate_json(canonical_json_bytes(old))
        try:
            validate_source_context(policy, facts["source_context"])
        except ValueError as error:
            return str(error)
    return None


def bind_prior_materials(
    request: ScaffoldDiscoveryRequest, facts: dict[str, Any]
) -> tuple[ScaffoldDiscoveryRequest, list[dict[str, Any]]]:
    value = request.model_dump(mode="json", by_alias=True)
    materialization = value["product"]["materialization"]
    conflicts = []
    for role in facts["required_roles"]:
        group, field = _location(materialization, role)
        fixed = facts["fixed_policies"].get(role)
        old = None if group is None else group.get(field)
        issue = (
            "The prior preparation or requested endpoint has no such external material role."
            if old is None or fixed is None
            else _policy_conflict(old, fixed, facts, role)
        )
        if issue is not None:
            conflicts.append(
                {
                    "requested_field": f"reuse_prior_materials.roles.{role}",
                    "requested_value": None if fixed is None else fixed,
                    "inherited_field": f"discovery.product.materialization.{role}",
                    "inherited_value": old,
                    "explicit_edit": issue
                    + " Explicitly reconcile the material requirement or prior reference.",
                }
            )
        if old is not None and fixed is not None:
            assert group is not None
            # Distal pairing constraints remain independent of the material choice.
            group[field] = {
                **fixed,
                **(
                    {"distal_pairing_constraints": old["distal_pairing_constraints"]}
                    if "distal_pairing_constraints" in old
                    else {}
                ),
            }
    return ScaffoldDiscoveryRequest.model_validate_json(canonical_json_bytes(value)), conflicts
