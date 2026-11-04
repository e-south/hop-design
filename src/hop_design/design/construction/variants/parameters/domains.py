"""Project requested domains, without mistaking their marginal values for valid products."""

from collections.abc import Iterable
from typing import Any

from hop_design.models.construction.complete.source_preparation.policy import primer_required_length
from hop_design.models.construction.discovery.request import ScaffoldDiscoveryRequest
from hop_design.models.enzymes import EnzymeProvisioningPolicy, EnzymeRole

from ...discovery.constraints import effective_scaffold


def parameter_domains(request: ScaffoldDiscoveryRequest) -> dict[str, dict[str, Any]]:
    p = request.product
    f = p.foldback.geometry
    result: dict[str, dict[str, Any]] = {}

    def discrete(key: str, values: Iterable[int | str]) -> None:
        result[key] = {"values": sorted(set(values)), "basis": "declared_permissions"}

    def extent(key: str, values: tuple[int, ...] | None, minimum: int, maximum: int) -> None:
        if values:
            discrete(key, values)
        elif minimum <= maximum:
            result[key] = {
                "minimum": minimum,
                "maximum": maximum,
                "step": 1,
                "basis": "declared_bounds",
            }

    max_overhead = p.foldback.search.max_retained_overhead_nt
    for direction in ("forward", "reverse"):
        policy = getattr(p.materialization.source_preparation, f"{direction}_primer")
        discrete(f"source_{direction}_primer_required_nt", (primer_required_length(policy),))
    extent(
        "foldback_arm_bp",
        f.annealing_arm_lengths_bp,
        f.minimum_annealing_arm_length_bp,
        (max_overhead - f.minimum_loop_length_nt) // 2,
    )
    extent(
        "loop_nt",
        f.loop_lengths_nt,
        f.minimum_loop_length_nt,
        max_overhead - 2 * f.minimum_annealing_arm_length_bp,
    )
    discrete("join_offset_nt", f.junction_offsets_nt)
    arms = result.get("foldback_arm_bp", {})
    if arms.get("values"):
        discrete(
            "self_paired_arm_bp",
            [a - d for a in arms["values"] for d in f.junction_offsets_nt if a >= d],
        )
    elif arms:
        # Union of integer intervals retains holes; do not fill unsupported A/D ranges.
        result["self_paired_arm_bp"] = {
            "intervals": [
                {"minimum": max(0, arms["minimum"] - d), "maximum": arms["maximum"] - d}
                for d in f.junction_offsets_nt
                if d <= arms["maximum"]
            ],
            "basis": "derived_from_declared_arms_and_displacements",
        }
    discrete(
        "foldback_strand",
        ("top", "bottom") if f.nick_strand.value == "any" else (f.nick_strand.value,),
    )
    if f.loop_sequences is not None:
        discrete("loop_word", f.loop_sequences)
    else:
        result["loop_word"] = {
            "alphabet": "ACGT",
            "length_parameter": "loop_nt",
            "basis": "unfixed_sequence_domain",
        }
    if p.basal:
        b = p.basal.geometry
        discrete("basal_nick_offset_nt", b.nick_offsets_nt)
        discrete(
            "basal_strand",
            ("top", "bottom") if b.nick_strand.value == "any" else (b.nick_strand.value,),
        )
        if b.minimum_adapter_annealing_nt is not None:
            discrete("adapter_annealing_min_nt", (b.minimum_adapter_annealing_nt,))
        for pair in b.pairing_constraints:
            i = pair.position_from_ligation
            discrete(f"basal_source_base_{i}", pair.allowed_source_bases)
            discrete(f"basal_adapter_base_{i}", pair.allowed_adapter_bases)
            discrete(
                f"basal_pair_class_{i}",
                ("match", "wobble", "mismatch")
                if pair.allowed_class.value == "any"
                else (pair.allowed_class.value,),
            )
    for role, job, permission_role in (
        ("foldback", p.foldback, EnzymeRole.FOLDBACK_NICK),
        ("basal", p.basal, EnzymeRole.BASAL_NICK),
        ("release", p.release, EnzymeRole.END_GENERATION),
    ):
        if job:
            policy = EnzymeProvisioningPolicy(catalog=p.enzyme_catalog, **job.enzymes.model_dump())
            overrides = (
                request.preparation_changes.basal_nick_enzyme_ids
                if role == "basal"
                else request.preparation_changes.release_enzyme_ids
                if role == "release"
                else None
            )
            discrete(
                f"{role}_method",
                overrides
                or [
                    e.enzyme_id
                    for e in p.enzyme_catalog.enzymes
                    if policy.permits(e.enzyme_id, role=permission_role)
                ],
            )
    if p.ends:
        for side in ("left", "right"):
            end = getattr(p.ends, side)
            alternatives = [getattr(pair, side) for pair in request.receiving_end_pairs or ()]
            discrete(
                f"{side}_gap",
                [getattr(v, f"{side}_bp") for v in request.end_placements]
                if request.end_placements
                else [e.payload_end_offset_bp for e in alternatives or [end]],
            )
            discrete(f"{side}_end_word", [e.cohesive_end_sequence for e in alternatives or [end]])
            discrete(f"{side}_end_polarity", [e.overhang_end.value for e in alternatives or [end]])
    scaffold, conflicts = effective_scaffold(request)
    for key, value in scaffold.items():
        original = result.get(key)
        if original and "values" in original:
            result[key] = {
                **original,
                "values": [
                    v for v in original["values"] if value["minimum"] <= v <= value["maximum"]
                ],
                "scaffold_requirement": value,
            }
        elif original and "minimum" in original:
            result[key] = {
                **original,
                "minimum": max(original["minimum"], value["minimum"]),
                "maximum": min(original["maximum"], value["maximum"]),
                "scaffold_requirement": value,
            }
        else:
            result[key] = {**value, "step": 1, "basis": "effective_scaffold_requirement"}
    # A request can contain a contradiction, but it must not become a fictitious domain.
    for conflict in conflicts:
        key = str(conflict["requested_field"]).split(".")[-1]
        if key in result:
            result[key] = {"values": [], "basis": "conflicting_requirements", "conflict": conflict}
    return result
