"""Expose authored permissions and their intersection without asserting feasibility."""

from typing import Any

from hop_design.models.construction.comparisons.request import (
    ComparisonRequest,
    SequenceComparisonMember,
)


def _excluded(interval: dict[str, int] | None, values: list[int]) -> list[dict[str, int]]:
    if interval is None:
        return []
    result = []
    start = interval["minimum"]
    for value in values:
        if value > start:
            result.append({"minimum": start, "maximum": value - 1})
        start = value + 1
    if start <= interval["maximum"]:
        result.append({"minimum": start, "maximum": interval["maximum"]})
    return result


def dimension_permissions(brief: ComparisonRequest, preview: dict[str, Any]) -> dict[str, Any]:
    product = brief.discovery.product
    geometry = product.foldback.geometry
    dimensions = {}
    for dimension, field, floor in (
        ("loop_nt", "loop_lengths_nt", geometry.minimum_loop_length_nt),
        (
            "loop_side_paired_bp",
            "annealing_arm_lengths_bp",
            geometry.minimum_annealing_arm_length_bp,
        ),
    ):
        declared = list(getattr(geometry, field))
        interval = preview["scaffold"].get(dimension)
        # Empty geometry domains are expanded by the existing local search envelope.
        upper = product.foldback.search.max_retained_overhead_nt
        if not declared and upper - floor > 100_000:
            raise ValueError("Comparison preview exceeds 100000 values; bound geometry explicitly.")
        permitted = declared or list(range(floor, upper + 1))
        if dimension == "loop_nt" and geometry.loop_sequences is not None:
            permitted = [v for v in permitted if v in {len(w) for w in geometry.loop_sequences}]
        values = sorted(
            {
                v
                for v in permitted
                if v >= floor
                and (interval is None or interval["minimum"] <= v <= interval["maximum"])
            }
        )
        dimensions[dimension] = {
            "effective_values": values,
            "requested_interval": interval,
            "excluded_intervals": _excluded(interval, values),
            "declaration": f"discovery.product.foldback.geometry.{field}",
            "declared_values": declared,
            "minimum_permitted_value": floor,
            "search_overhead_bound_nt": upper,
            "meaning": "permitted geometry; complete construction remains unevaluated",
        }
    arms = product.hairpin_basal_component
    dimensions["open_side_paired_positions"] = {
        "requested_interval": preview["scaffold"].get("open_side_paired_positions"),
        "effective_values": None if arms is None else [len(arms.left_arm)],
        "declaration": "discovery.product.hairpin_basal_component"
        if arms
        else "discovery.product.basal.geometry",
        "fixed_arms": None if arms is None else arms.model_dump(mode="json"),
        "meaning": "achieved pairing is checked on each complete construction",
    }
    for dimension in ("five_prime_unpaired_nt", "three_prime_unpaired_nt"):
        dimensions[dimension] = {
            "requested_interval": preview["scaffold"].get(dimension),
            "effective_values": None,
            "declaration": f"discovery.scaffold.{dimension}",
            "meaning": "achieved unpaired terminal tract; complete construction is checked",
        }
    return dimensions


def member_conflicts(brief: ComparisonRequest, dimensions: dict[str, Any]) -> list[dict[str, Any]]:
    conflicts: list[dict[str, Any]] = []
    endpoint = brief.discovery.product.endpoint.value
    absent_roles: set[str] = set()
    if endpoint in ("ssdna_hairpin", "adapter_ligated_hairpin"):
        absent_roles.update(("endpoint_forward_primer", "endpoint_reverse_primer"))
    if endpoint == "ssdna_hairpin":
        absent_roles.add("ligation_adapter")
    for role in brief.preserve_material_roles:
        if role in absent_roles:
            conflicts.append(
                {
                    "member": None,
                    "requested_field": "preserve_material_roles",
                    "requested_value": role,
                    "inherited_field": "discovery.product.endpoint",
                    "inherited_value": endpoint,
                    "explicit_edit": f"The {endpoint} endpoint has no {role}. Remove this "
                    "preservation requirement or explicitly request an endpoint using that role.",
                }
            )
    release = brief.discovery.product.release
    methods = brief.discovery.preparation_changes.release_enzyme_ids
    if methods is None:
        methods = () if release is None else release.enzymes.allowed_enzyme_ids
    for member in brief.required_members:
        if isinstance(member, SequenceComparisonMember) and member.loop_sequence is not None:
            word = member.loop_sequence
            geometry = brief.discovery.product.foldback.geometry
            lengths = dimensions["loop_nt"]["effective_values"]
            if len(word) not in lengths or (
                geometry.loop_sequences is not None and word not in geometry.loop_sequences
            ):
                conflicts.append(
                    {
                        "member": member.name,
                        "requested_field": f"required_members.{member.name}.loop_sequence",
                        "requested_value": word,
                        "inherited_field": "discovery.product.foldback.geometry",
                        "inherited_value": geometry.model_dump(mode="json"),
                        "explicit_edit": "Explicitly revise the exact loop word or its permitted "
                        "sequence/length domain; no member has been removed.",
                    }
                )
        if member.release_enzyme_id is not None and member.release_enzyme_id not in methods:
            conflicts.append(
                {
                    "member": member.name,
                    "requested_field": f"required_members.{member.name}.release_enzyme_id",
                    "requested_value": member.release_enzyme_id,
                    "inherited_field": "discovery.preparation_changes.release_enzyme_ids"
                    if brief.discovery.preparation_changes.release_enzyme_ids is not None
                    else "discovery.product.release.enzymes.allowed_enzyme_ids",
                    "inherited_value": list(methods),
                    "explicit_edit": "Explicitly permit this release method "
                    "in the discovery request "
                    "or revise the required method; catalog and role checks still apply.",
                }
            )
        for dimension, value in member.dimensions.items():
            domain = dimensions[dimension]
            interval = domain["requested_interval"]
            values = domain["effective_values"]
            excluded = (values is not None and value not in values) or (
                interval is not None and not interval["minimum"] <= value <= interval["maximum"]
            )
            if excluded:
                conflicts.append(
                    {
                        "member": member.name,
                        "requested_field": f"required_members.{member.name}.dimensions.{dimension}",
                        "requested_value": value,
                        "inherited_field": domain["declaration"],
                        "inherited_value": domain,
                        "explicit_edit": "Explicitly revise this member "
                        "or its inherited permissions; "
                        "the required member has not been removed.",
                    }
                )
        for shared_property in brief.shared_properties:
            declared = {
                value
                for m in brief.required_members
                for key, value in m.dimensions.items()
                if key == shared_property
            }
            if shared_property in member.dimensions and len(declared) > 1:
                conflicts.append(
                    {
                        "member": member.name,
                        "requested_field": "shared_properties",
                        "requested_value": shared_property,
                        "inherited_field": "required_members",
                        "inherited_value": sorted(declared),
                        "explicit_edit": "Remove the shared requirement "
                        "or stop varying this dimension.",
                    }
                )
    return conflicts
