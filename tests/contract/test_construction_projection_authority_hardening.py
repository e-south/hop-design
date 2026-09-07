"""
--------------------------------------------------------------------------------
HOP Design
tests/contract/test_construction_projection_authority_hardening.py

Tests local construction projections against endpoint and membership drift.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from hop_design.design.construction.basal import discover_basal_neighborhood
from hop_design.design.construction.foldback import discover_foldback_neighborhood
from hop_design.design.construction.projections import (
    project_basal_feasibility,
    project_basal_minimum_overhead_matrix,
    project_foldback_feasibility,
    project_retained_overhead_frontier,
    verify_local_projection,
)
from hop_design.models.construction import (
    ConstructionEndpoint,
    FoldbackGeometryDomain,
    NickStrandSelection,
    ProjectionReference,
    SearchCompletionStatus,
    SearchDisposition,
    SearchFeasibilityStatus,
    SearchTerminationReason,
)
from hop_design.models.construction.basal import (
    BasalBoundaryProjection,
)
from hop_design.models.construction.projections import (
    BasalFeasibilityProjection,
    BasalMinimumOverheadCell,
    BasalMinimumOverheadMatrixProjection,
    FoldbackFeasibilityProjection,
    RetainedOverheadFrontierProjection,
)
from hop_design.models.sequence import reverse_complement_iupac
from tests.contract.test_basal_construction_discovery import _request as basal_request
from tests.contract.test_foldback_construction_discovery import _nickase as foldback_nickase
from tests.contract.test_foldback_construction_discovery import _request as foldback_request
from tests.contract.test_foldback_construction_discovery import (
    _terminus_enzyme as foldback_terminus_enzyme,
)


@pytest.mark.parametrize(
    "changed_endpoint",
    [
        ConstructionEndpoint.SSDNA_HAIRPIN,
    ],
)
def test_basal_projection_rejects_endpoint_evidence_leakage(
    changed_endpoint: ConstructionEndpoint,
) -> None:
    source = project_basal_feasibility(
        discover_basal_neighborhood(basal_request(ConstructionEndpoint.HAIRPIN_PCR_DUPLEX))
    )
    content = source.model_dump(by_alias=True)
    content["endpoint"] = changed_endpoint

    with pytest.raises(ValidationError, match="PCR-bearing local boundary"):
        BasalFeasibilityProjection.model_validate(content)


def test_clone_basal_projection_exposes_future_release_as_an_obligation() -> None:
    projection = project_basal_feasibility(
        discover_basal_neighborhood(basal_request(ConstructionEndpoint.CLONE_READY_DUPLEX))
    )

    assert projection.endpoint is ConstructionEndpoint.CLONE_READY_DUPLEX
    assert projection.realizations
    assert all(row.future_release_action_id for row in projection.realizations)
    assert all(row.future_release_enzyme_id for row in projection.realizations)
    assert all(row.required_annealing_nt == 15 for row in projection.realizations)


def test_basal_matrix_replay_rejects_a_resealed_minimum() -> None:
    result = discover_basal_neighborhood(basal_request(ConstructionEndpoint.CLONE_READY_DUPLEX))
    projection = project_basal_minimum_overhead_matrix(result)
    cell = projection.cells[0]
    changed = projection.model_copy(
        update={
            "cells": (
                cell.model_copy(
                    update={"minimum_retained_overhead_nt": (cell.minimum_retained_overhead_nt - 1)}
                ),
            )
        }
    )

    with pytest.raises(ValueError, match="does not replay"):
        verify_local_projection(changed, result)


def test_basal_matrix_cells_reject_forged_membership_and_status() -> None:
    projection = project_basal_minimum_overhead_matrix(
        discover_basal_neighborhood(basal_request(ConstructionEndpoint.CLONE_READY_DUPLEX))
    )
    cell = projection.cells[0]

    for update, message in (
        ({"realization_count": cell.realization_count + 1}, "count must equal exact realization"),
        (
            {
                "realization_count": cell.realization_count + 1,
                "realization_ids": (*cell.realization_ids, cell.realization_ids[0]),
            },
            "must not repeat",
        ),
        ({"minimum_retained_overhead_nt": None}, "minimum requires exact realization"),
        ({"status": "infeasible"}, "without a solution cannot carry"),
    ):
        with pytest.raises(ValidationError, match=message):
            BasalMinimumOverheadCell.model_validate(
                {
                    **cell.model_dump(mode="python"),
                    **update,
                }
            )


def test_basal_matrix_rejects_forged_axes_scope_and_completion() -> None:
    complete = project_basal_minimum_overhead_matrix(
        discover_basal_neighborhood(
            basal_request(ConstructionEndpoint.CLONE_READY_DUPLEX, extra_nickase=True)
        )
    )
    content = complete.model_dump(mode="python", by_alias=True)
    cell = complete.cells[0]
    assert cell.minimum_retained_overhead_nt is not None

    for update, message in (
        ({"nick_enzyme_ids": tuple(reversed(complete.nick_enzyme_ids))}, "unique canonical order"),
        (
            {"release_actions": (*complete.release_actions, complete.release_actions[0])},
            "unique canonical order",
        ),
        (
            {
                "cells": (
                    cell.model_copy(update={"nick_enzyme_id": "example:enzyme/other@1"}),
                    *complete.cells[1:],
                )
            },
            "canonical axis product",
        ),
        ({"realization_ids": ()}, "partition every exact realization"),
        (
            {"max_retained_overhead_nt": cell.minimum_retained_overhead_nt - 1},
            "inside the declared overhead envelope",
        ),
    ):
        with pytest.raises(ValidationError, match=message):
            BasalMinimumOverheadMatrixProjection.model_validate({**content, **update})

    infeasible = project_basal_minimum_overhead_matrix(
        discover_basal_neighborhood(
            basal_request(
                ConstructionEndpoint.CLONE_READY_DUPLEX,
                max_retained_overhead_nt=3,
            )
        )
    )
    with pytest.raises(ValidationError, match="Only complete search coverage"):
        BasalMinimumOverheadMatrixProjection.model_validate(
            {
                **infeasible.model_dump(mode="python", by_alias=True),
                "disposition": infeasible.disposition.model_copy(
                    update={
                        "completion": SearchCompletionStatus.TRUNCATED,
                        "feasibility": SearchFeasibilityStatus.UNKNOWN,
                        "termination_reason": SearchTerminationReason.EVALUATION_CAP,
                    }
                ),
            }
        )

    partial = project_basal_minimum_overhead_matrix(
        discover_basal_neighborhood(
            basal_request(
                ConstructionEndpoint.CLONE_READY_DUPLEX,
                extra_nickase=True,
                max_nodes=1,
            )
        )
    )
    with pytest.raises(ValidationError, match="cannot leave an unknown matrix cell"):
        BasalMinimumOverheadMatrixProjection.model_validate(
            {
                **partial.model_dump(mode="python", by_alias=True),
                "disposition": partial.disposition.model_copy(
                    update={
                        "completion": SearchCompletionStatus.COMPLETE,
                        "termination_reason": SearchTerminationReason.EXHAUSTED_DOMAIN,
                    }
                ),
            }
        )


def test_projection_authorities_reject_duplicate_membership_and_status_drift() -> None:
    foldback = project_foldback_feasibility(
        discover_foldback_neighborhood(
            foldback_request(foldback_nickase(), foldback_terminus_enzyme())
        )
    )
    content = foldback.model_dump(by_alias=True)
    content["realizations"] = (foldback.realizations[0], foldback.realizations[0])
    content["realization_count"] = 2
    with pytest.raises(ValidationError, match="must not repeat"):
        FoldbackFeasibilityProjection.model_validate(content)


def test_local_projection_reference_rejects_the_dead_complete_result_spelling() -> None:
    with pytest.raises(ValidationError, match="result_id"):
        ProjectionReference(
            projection_id=f"hop:projection/{'0' * 64}@1",
            result_id=f"hop:construction-result/{'1' * 64}@1",
            projection_schema="hop.example/v1",
            renderer_version="example/1",
            realization_ids=(),
            groups=(),
        )

    infeasible = project_foldback_feasibility(
        discover_foldback_neighborhood(
            foldback_request(foldback_nickase(motif="GACA", cut_offset=4))
        )
    )
    content = infeasible.model_dump(by_alias=True)
    content["disposition"] = SearchDisposition(
        completion=SearchCompletionStatus.COMPLETE,
        feasibility=SearchFeasibilityStatus.FEASIBLE,
        termination_reason=SearchTerminationReason.EXHAUSTED_DOMAIN,
    )
    with pytest.raises(ValidationError, match="Feasible projections require"):
        FoldbackFeasibilityProjection.model_validate(content)


def test_overhead_projection_rejects_cross_level_membership_and_false_completion() -> None:
    domain = FoldbackGeometryDomain(
        nick_strand=NickStrandSelection.ANY,
        junction_offsets_nt=(0,),
        loop_lengths_nt=(3,),
        annealing_arm_lengths_bp=(3, 4),
    )
    source = project_retained_overhead_frontier(
        discover_foldback_neighborhood(
            foldback_request(
                foldback_nickase(motif="GACATTT"),
                domain=domain,
                max_retained_overhead_nt=11,
            )
        )
    )
    realized_id = source.levels[11].realization_ids[0]
    duplicated_level = source.levels[0].model_copy(
        update={
            "candidate_count": source.levels[0].candidate_count + 1,
            "realization_count": 1,
            "realization_ids": (realized_id,),
        }
    )
    content = source.model_dump(by_alias=True)
    content["levels"] = (duplicated_level, *source.levels[1:])
    with pytest.raises(ValidationError, match="partition exact membership"):
        RetainedOverheadFrontierProjection.model_validate(content)

    truncated = project_retained_overhead_frontier(
        discover_foldback_neighborhood(
            foldback_request(
                foldback_nickase(),
                foldback_terminus_enzyme(),
                max_search_nodes=1,
            )
        )
    )
    content = truncated.model_dump(by_alias=True)
    content["disposition"] = SearchDisposition(
        completion=SearchCompletionStatus.COMPLETE,
        feasibility=SearchFeasibilityStatus.FEASIBLE,
        termination_reason=SearchTerminationReason.EXHAUSTED_DOMAIN,
    )
    with pytest.raises(ValidationError, match="partial level"):
        RetainedOverheadFrontierProjection.model_validate(content)


def test_basal_boundary_projection_requires_exact_complement_and_pcr_endpoint() -> None:
    pcr = (
        discover_basal_neighborhood(basal_request(ConstructionEndpoint.HAIRPIN_PCR_DUPLEX))
        .realizations[0]
        .projection
    )
    content = pcr.model_dump(mode="python")
    content["local_complement_sequence"] = pcr.local_reference_sequence
    assert content["local_complement_sequence"] != reverse_complement_iupac(
        pcr.local_reference_sequence
    )
    with pytest.raises(ValidationError, match="must derive from the local reference"):
        BasalBoundaryProjection.model_validate(content)

    direct = pcr.model_dump(mode="python")
    direct["endpoint"] = ConstructionEndpoint.SSDNA_HAIRPIN
    with pytest.raises(ValidationError):
        BasalBoundaryProjection.model_validate(direct)
