"""Declared marginal domains retain their joint constraints and molecular frames."""

from typing import Any

from hop_design.models.construction.complete.source_preparation.policy import primer_required_length
from hop_design.models.construction.surveys.request import InterfaceSurveyRequest
from hop_design.models.construction.surveys.targets import FOUR_BASE_WORDS
from hop_design.models.enzymes import EnzymeClass, EnzymeProvisioningPolicy, EnzymeRole

from .branches import SurveyBranches


def survey_domains(request: InterfaceSurveyRequest) -> dict[str, dict[str, Any]]:
    cases = SurveyBranches(request).foldback_cases
    domains: dict[str, dict[str, Any]] = {}

    def declared(key: str, values: Any, basis: str = "declared_permissions") -> None:
        domains[key] = {"values": sorted(set(values)), "basis": basis}

    for key, attr in (
        ("foldback_arm_bp", "annealing_arm_length_bp"),
        ("join_offset_nt", "junction_offset_nt"),
        ("loop_nt", "loop_length_nt"),
    ):
        declared(key, (getattr(c, attr) for c in cases))
    declared(
        "self_paired_arm_bp",
        (c.annealing_arm_length_bp - c.junction_offset_nt for c in cases),
        "derived_from_joint_geometry",
    )
    declared("foldback_strand", (c.nick_strand.value for c in cases))
    words = request.foldback.geometry.loop_sequences
    if words is not None:
        declared("loop_word", words)
    else:
        domains["loop_word"] = {
            "alphabet": "ACGT",
            "length_parameter": "loop_nt",
            "basis": "unfixed_sequence_domain",
        }
    declared("basal_nick_offset_nt", request.basal.geometry.nick_offsets_nt)
    declared("adapter_annealing_min_nt", request.basal.annealing_lengths_nt)
    strand = request.basal.geometry.nick_strand.value
    declared("basal_strand", ("top", "bottom") if strand == "any" else (strand,))
    for side in ("left", "right"):
        declared(f"{side}_end_word", getattr(request.targets, f"{side}_words") or FOUR_BASE_WORDS)
        declared(f"{side}_gap", (getattr(p, f"{side}_bp") for p in request.placements))
        declared(f"{side}_end_polarity", (getattr(request.interfaces, side).overhang_end.value,))
    for role, permission in (
        ("foldback", EnzymeRole.FOLDBACK_NICK),
        ("basal", EnzymeRole.BASAL_NICK),
    ):
        policy = EnzymeProvisioningPolicy(
            catalog=request.enzyme_catalog, **getattr(request, role).enzymes.model_dump()
        )
        declared(
            f"{role}_method",
            (
                str(e.enzyme_id)
                for e in request.enzyme_catalog.enzymes
                if e.enzyme_class is EnzymeClass.NICKASE
                and policy.permits(e.enzyme_id, role=permission)
            ),
        )
    declared("release_method", SurveyBranches(request).release_methods)
    for field in ("recognition_material", "product_end"):
        declared(
            f"basal_release_{field}", (getattr(p, field) for p in request.release.basal_projections)
        )
    for side in ("forward", "reverse"):
        declared(
            f"source_{side}_primer_required_nt",
            (
                primer_required_length(
                    getattr(request.materialization.source_preparation, f"{side}_primer")
                ),
            ),
        )
    return domains


def excluded_interface_values(
    request: InterfaceSurveyRequest, ended: dict[int, bool], paths: list[dict[str, Any]]
) -> dict[str, list[str]]:
    """A word is excluded only when every declared partner pair has a scoped proof.

    Filters cannot turn unexamined pairs into exclusions. A supported preparation
    remains supported even if a later continuation exhausts that target.
    """
    from collections import Counter

    supported = {p["address"]["target"] for p in paths}
    counts: tuple[Counter[str], Counter[str]] = (Counter(), Counter())
    for target, complete in ended.items():
        if complete and target not in supported:
            for side, word in enumerate(request.targets.pair_at(target)):
                counts[side][word] += 1
    return {
        "left_end_word": sorted(
            w for w, n in counts[0].items() if n == request.targets.right_count
        ),
        "right_end_word": sorted(
            w for w, n in counts[1].items() if n == request.targets.left_count
        ),
    }
