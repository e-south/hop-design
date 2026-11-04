"""Request-only parameter definitions; no selected values or feasibility assertions."""

from typing import Any

from hop_design.models.construction.surveys.request import InterfaceSurveyRequest
from hop_design.models.construction.variants.parameters import parameter_definition
from hop_design.serialization import canonical_json_bytes, sha256_digest

from .domains import survey_domains

AXIS_ORDER = (
    "left_end_word",
    "left_end_polarity",
    "left_gap",
    "right_end_word",
    "right_end_polarity",
    "right_gap",
    "release_method",
    "basal_method",
    "basal_strand",
    "basal_nick_offset_nt",
    "adapter_annealing_min_nt",
    "adapter_annealing_achieved_nt",
    "noncanonical_pairs",
    "open_side_paired_positions",
    "five_prime_unpaired_nt",
    "three_prime_unpaired_nt",
    "source_forward_primer_required_nt",
    "source_forward_primer_available_nt",
    "foldback_method",
    "foldback_strand",
    "foldback_arm_bp",
    "join_offset_nt",
    "self_paired_arm_bp",
    "loop_nt",
    "loop_word",
    "source_reverse_primer_required_nt",
    "source_reverse_primer_available_nt",
)

CONTEXT_KEYS = ("basal_release_product_end", "basal_release_recognition_material")


def survey_context(request: InterfaceSurveyRequest) -> dict[str, Any]:
    return {
        "supplied_stem": request.stem_arm,
        "source_context_objective": request.source_context_objective,
        "joint_placements": [p.model_dump(mode="json") for p in request.placements],
        "basal_release_projections": [
            p.model_dump(mode="json") for p in request.release.basal_projections
        ],
        "relations": ["R = A - D", "C = length(loop word)"],
        "retained_limits_nt": {
            role: getattr(request, role).max_retained_overhead_nt for role in ("foldback", "basal")
        },
        "material_permissions": request.materialization.model_dump(mode="json"),
        "whole_route_requirements": request.whole_route_constraints.model_dump(mode="json"),
    }


def parameter_key(request: InterfaceSurveyRequest) -> dict[str, Any]:
    domains = survey_domains(request)
    return {
        "schema": "hop.parameter-definition-key/v1",
        "request_digest": sha256_digest(canonical_json_bytes(request)),
        "parameters": [
            {
                "definition": parameter_definition(key).model_dump(mode="json"),
                "domain": domains.get(key, {"basis": "observed_only"}),
            }
            for key in (*AXIS_ORDER, *CONTEXT_KEYS)
        ],
        "context": survey_context(request),
    }
