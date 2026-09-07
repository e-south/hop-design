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
    project_foldback_feasibility,
    project_retained_overhead_frontier,
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
    BasalEndpointProjection,
    BasalMaterialRecord,
    BasalMaterialRole,
)
from hop_design.models.construction.basal.states import assert_material_partition
from hop_design.models.construction.projections import (
    BasalFeasibilityProjection,
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
        ConstructionEndpoint.CLONE_READY_DUPLEX,
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

    with pytest.raises(ValidationError, match="exact hairpin PCR intermediate"):
        BasalFeasibilityProjection.model_validate(content)


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


def test_basal_endpoint_projection_requires_exact_complement_and_endpoint_minimality() -> None:
    pcr = (
        discover_basal_neighborhood(basal_request(ConstructionEndpoint.HAIRPIN_PCR_DUPLEX))
        .realizations[0]
        .projection
    )
    content = pcr.model_dump(mode="python")
    assert pcr.pcr_reference_sequence is not None
    content["pcr_complement_sequence"] = pcr.pcr_reference_sequence
    assert content["pcr_complement_sequence"] != reverse_complement_iupac(
        pcr.pcr_reference_sequence
    )
    with pytest.raises(ValidationError, match="must derive from the complete reference"):
        BasalEndpointProjection.model_validate(content)

    direct = pcr.model_dump(mode="python")
    direct["endpoint"] = ConstructionEndpoint.SSDNA_HAIRPIN
    with pytest.raises(ValidationError):
        BasalEndpointProjection.model_validate(direct)


def test_material_partition_requires_exact_endpoint_state_and_singular_partition() -> None:
    record = discover_basal_neighborhood(
        basal_request(ConstructionEndpoint.HAIRPIN_PCR_DUPLEX)
    ).realizations[0]
    retained = BasalMaterialRecord(
        material_id="retained-product",
        role=BasalMaterialRole.RETAINED,
        sequence_5prime=record.hairpin_pcr_duplex.top_strand.sequence,
    )
    duplicate = retained.model_copy(update={"material_id": "retained-copy"})
    with pytest.raises(ValueError, match="must be singular"):
        assert_material_partition(
            pcr_duplex=record.hairpin_pcr_duplex,
            materials=(retained, duplicate),
        )
    with pytest.raises(ValueError, match="must replay"):
        assert_material_partition(
            pcr_duplex=record.hairpin_pcr_duplex,
            materials=(retained.model_copy(update={"sequence_5prime": "ACTG"}),),
        )
