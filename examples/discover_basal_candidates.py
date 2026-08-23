"""Run bounded basal-candidate searches and print their epistemic status."""

from __future__ import annotations

import json

import hop_design as hop
import hop_design.discovery as discovery


def constraints() -> hop.BasalConstraintProfile:
    """Return one explicit demonstration policy."""
    return hop.BasalConstraintProfile(
        require_terminal_watson_crick=True,
        allow_active_gt_wobble=True,
        max_active_hard_mismatches=0,
        max_active_non_watson_crick_pairs=1,
        forbid_active_middle_double_hard=True,
        minimum_active_pair_support_index=3.5,
        maximum_active_pair_disruption_index=0.5,
        require_outer_hard_for_active_double=True,
        reject_compact_profiles=(),
        reserve_compact_profiles=(),
    )


def summarize(label: str, result: discovery.BasalCandidateSearchResult) -> dict[str, object]:
    """Project one result without treating an ordinal as a biological score."""
    if result.status == "complete":
        interpretation = "declared space exhausted with compatible candidates"
    elif result.status == "infeasible":
        interpretation = "declared space exhausted without a compatible candidate"
    else:
        interpretation = "bounds stopped the search before a definitive conclusion"
    return {
        "label": label,
        "status": result.status,
        "interpretation": interpretation,
        "candidate_space_size": result.candidate_space_size,
        "search_nodes_examined": result.search_nodes_examined,
        "hit_ids": [hit.candidate_id for hit in result.hits],
        "canonical_ordinals": [hit.canonical_ordinal for hit in result.hits],
        "truncated_by": list(result.truncated_by),
    }


def main() -> None:
    """Run complete, infeasible, and node-truncated examples."""
    shared = constraints()
    compatible = discovery.BasalCandidateSearchRequest(
        left_arm_template="RAAA",
        right_arm_template="TTTT",
        constraints=shared,
        acceptance="active_only",
    )
    infeasible = discovery.BasalCandidateSearchRequest(
        left_arm_template="AAAA",
        right_arm_template="AAAA",
        constraints=shared,
        acceptance="active_only",
    )
    results = (
        (
            "complete",
            discovery.search_basal_candidates(
                compatible,
                limits=discovery.BasalCandidateSearchLimits(max_search_nodes=2, max_hits=2),
            ),
        ),
        (
            "infeasible",
            discovery.search_basal_candidates(
                infeasible,
                limits=discovery.BasalCandidateSearchLimits(max_search_nodes=1, max_hits=1),
            ),
        ),
        (
            "truncated",
            discovery.search_basal_candidates(
                compatible,
                limits=discovery.BasalCandidateSearchLimits(max_search_nodes=1, max_hits=2),
            ),
        ),
    )
    assert tuple(result.status for _label, result in results) == (
        "complete",
        "infeasible",
        "truncated",
    )
    print(json.dumps([summarize(label, result) for label, result in results], indent=2))


if __name__ == "__main__":
    main()
