"""Intersect product requirements while identifying the declarations that conflict."""

from typing import Any

from hop_design.models.construction.discovery.request import ScaffoldDiscoveryRequest


def effective_scaffold(
    request: ScaffoldDiscoveryRequest,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    inherited = request.product.whole_route_constraints.hairpin_scaffold
    requirements = {} if inherited is None else inherited.model_dump(mode="json", exclude_none=True)
    desired = (
        {}
        if request.scaffold is None
        else request.scaffold.model_dump(mode="json", exclude_none=True)
    )
    conflicts = []
    for dimension, interval in desired.items():
        previous = requirements.get(dimension)
        if previous is None:
            requirements[dimension] = interval
            continue
        lower, upper = (
            max(previous["minimum"], interval["minimum"]),
            min(previous["maximum"], interval["maximum"]),
        )
        if lower > upper:
            conflicts.append(
                {
                    "requested_field": f"scaffold.{dimension}",
                    "requested_value": interval,
                    "inherited_field": (
                        f"product.whole_route_constraints.hairpin_scaffold.{dimension}"
                    ),
                    "inherited_value": previous,
                    "explicit_edit": "Change one of these declared hard ranges so they intersect.",
                }
            )
        else:
            requirements[dimension] = {"minimum": lower, "maximum": upper}
    geometry = request.product.foldback.geometry
    for dimension, domain, floor in (
        ("loop_nt", "loop_lengths_nt", geometry.minimum_loop_length_nt),
        (
            "loop_side_paired_bp",
            "annealing_arm_lengths_bp",
            geometry.minimum_annealing_arm_length_bp,
        ),
    ):
        interval = requirements.get(dimension)
        if interval is None:
            continue
        values = getattr(geometry, domain)
        if (
            values
            and not any(interval["minimum"] <= value <= interval["maximum"] for value in values)
        ) or interval["maximum"] < floor:
            conflicts.append(
                {
                    "requested_field": f"scaffold.{dimension}"
                    if dimension in desired
                    else f"product.whole_route_constraints.hairpin_scaffold.{dimension}",
                    "requested_value": interval,
                    "inherited_field": f"product.foldback.geometry.{domain}",
                    "inherited_value": list(values),
                    "minimum_permitted_value": floor,
                    "explicit_edit": "Explicitly include the desired values in the geometry domain "
                    "or change the scaffold requirement; preserve the declared minimum.",
                }
            )
    auxiliaries = request.product.materialization.endpoint_auxiliaries
    adapter = request.product.materialization.adapter_ligation
    adapter_field = "product.materialization.adapter_ligation"
    if auxiliaries is not None:
        adapter = auxiliaries.adapter
        adapter_field = "product.materialization.endpoint_auxiliaries.adapter"
    if request.preparation_changes.adapter_redesign == "allow":
        if request.product.basal is None:
            conflicts.append(
                {
                    "requested_field": "preparation_changes.adapter_redesign",
                    "requested_value": "allow",
                    "inherited_field": "product.endpoint",
                    "inherited_value": request.product.endpoint.value,
                    "explicit_edit": "Preserve preparation settings for a direct hairpin; "
                    "this endpoint has no downstream adapter-redesign step.",
                }
            )
        elif adapter is not None and adapter.mode.value == "fixed":
            conflicts.append(
                {
                    "requested_field": "preparation_changes.adapter_redesign",
                    "requested_value": "allow",
                    "inherited_field": adapter_field,
                    "inherited_value": adapter.model_dump(mode="json"),
                    "explicit_edit": "Preserve the fixed adapter, or explicitly replace its fixed "
                    "material declaration with a derived or constrained adapter policy.",
                }
            )
    return requirements, conflicts
