"""
--------------------------------------------------------------------------------
HOP Design
tests/integration/test_complete_construction_source_partition.py

Tests selected source-partition evidence inside complete-route composition.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hop_design.design.construction.complete import discover_constructions
from hop_design.design.construction.complete.bundle import compile_construction_bundle
from hop_design.design.construction.foldback import discover_foldback_neighborhood
from hop_design.design.construction.public import load_verified_construction_bundle
from hop_design.design.construction.verification import (
    verify_foldback_neighborhood_result,
)
from hop_design.models.construction import FinalPayloadReference, FoldbackTarget
from hop_design.models.construction.accounting import FailureReasonCount
from hop_design.models.construction.complete import (
    ConstructionDiscoveryRequest,
    ConstructionSpaceResult,
    SourcePartitionBinding,
)
from hop_design.models.construction.complete.evaluation import CompositionRejectionCode
from hop_design.models.construction.complete.source_partition.result_validation import (
    validate_source_partition_result_contract,
)
from hop_design.models.coordinates import Boundary
from hop_design.models.enzymes import RecognitionOrientationSemantics
from hop_design.models.payload import ExactPayload
from tests.contract.test_complete_source_partition_replay import (
    PAYLOAD,
    _partition_result,
)
from tests.contract.test_foldback_construction_discovery import (
    _nickase,
    _request,
    _terminus_enzyme,
)
from tests.integration.test_complete_construction_discovery import (
    _construction_request,
    _discover_raw,
    _verified_design,
)


def _case(
    tmp_path: Path,
    *,
    truncated_partition: bool = False,
    require_all_combinations_valid: bool = False,
):
    payload = FinalPayloadReference(
        payload=ExactPayload(sequence=PAYLOAD),
        basal_boundary=Boundary(offset=0),
        foldback_boundary=Boundary(offset=len(PAYLOAD)),
    )
    nickase = _nickase(
        motif="TCAGATGCTGA",
        cut_offset=0,
        orientation_semantics=RecognitionOrientationSemantics.DECLARED_ONLY,
    )
    foldback = discover_foldback_neighborhood(
        _request(
            nickase,
            _terminus_enzyme(),
            target=FoldbackTarget(
                nick_offset_within_foldback_nt=0,
                loop_length_nt=3,
                annealing_arm_length_bp=4,
            ),
        ).model_copy(update={"payload": payload})
    )
    design = _verified_design(tmp_path, PAYLOAD)
    baseline_request = _construction_request(
        payload=payload,
        foldback=foldback,
        basal=None,
        design=design,
    )
    baseline = _discover_raw(
        baseline_request,
        foldback=foldback,
        basal=None,
        design=design,
    )
    one_stage = next(
        item
        for item in baseline.realizations
        if len(item.construction_program.reaction_programs[0].stages) == 1
    )
    partition = _partition_result(
        payload,
        nickase,
        one_stage,
        truncated=truncated_partition,
    )
    request_content = baseline_request.model_dump(mode="python", by_alias=True)
    request_content.update(
        {
            "source_partition_result_id": partition.result_id,
            "selected_source_partition_realization_id": (partition.realizations[0].realization_id),
            "whole_route_constraints": (
                baseline_request.whole_route_constraints.model_copy(
                    update={"require_all_combinations_valid": require_all_combinations_valid}
                )
            ),
        }
    )
    request = ConstructionDiscoveryRequest.model_validate(request_content)
    return request, foldback, design, partition, baseline


def test_selected_partition_filters_routes_without_expanding_the_search_space(
    tmp_path: Path,
) -> None:
    request, foldback, design, partition, baseline = _case(tmp_path)

    verified = discover_constructions(
        request,
        foldback=verify_foldback_neighborhood_result(foldback),
        basal=None,
        design=design,
        source_partition=partition,
    )
    result = verified.result

    assert result.source_partition_authority == partition
    assert result.provenance.source_partition_result_id == partition.result_id
    assert result.provenance.source_partition_realization_id == (
        partition.realizations[0].realization_id
    )
    assert result.accounting.nominal_combinations == baseline.accounting.nominal_combinations
    assert result.accounting.valid_realizations == 1
    assert all(item.source_partition_binding is not None for item in result.realizations)
    assert {item.code for item in result.failure_reasons} == {
        CompositionRejectionCode.SOURCE_PARTITION_SOURCE_INCOMPATIBLE
    }
    assert len(result.source_partition_rejection_candidates) == 1


def test_partition_rejection_candidates_survive_portable_bundle_replay(
    tmp_path: Path,
) -> None:
    request, foldback, design, partition, _ = _case(tmp_path)
    verified = discover_constructions(
        request,
        foldback=verify_foldback_neighborhood_result(foldback),
        basal=None,
        design=design,
        source_partition=partition,
    )

    compilation = compile_construction_bundle(verified)
    loaded = load_verified_construction_bundle(compilation.write(tmp_path / "construction"))

    assert loaded.result_id == compilation.result_id
    assert loaded._verified_source().result.source_partition_rejection_candidates == (
        verified.result.source_partition_rejection_candidates
    )


def test_selected_member_from_truncated_partition_remains_a_complete_route(
    tmp_path: Path,
) -> None:
    request, foldback, design, partition, _ = _case(
        tmp_path,
        truncated_partition=True,
    )

    result = discover_constructions(
        request,
        foldback=verify_foldback_neighborhood_result(foldback),
        basal=None,
        design=design,
        source_partition=partition,
    ).result

    assert partition.status == "truncated"
    assert result.status == "complete"
    assert result.accounting.valid_realizations == 1


def test_require_all_combinations_rejects_partition_incompatible_space(
    tmp_path: Path,
) -> None:
    request, foldback, design, partition, _ = _case(
        tmp_path,
        require_all_combinations_valid=True,
    )

    result = discover_constructions(
        request,
        foldback=verify_foldback_neighborhood_result(foldback),
        basal=None,
        design=design,
        source_partition=partition,
    ).result

    assert result.status == "infeasible"
    assert result.realizations == ()
    assert len(result.source_partition_rejection_candidates) == 1
    assert {item.code for item in result.failure_reasons} == {
        CompositionRejectionCode.ALL_COMBINATIONS_VALID_REQUIRED,
        CompositionRejectionCode.SOURCE_PARTITION_SOURCE_INCOMPATIBLE,
    }


def test_selected_partition_binding_replays_exact_route_facts(tmp_path: Path) -> None:
    request, foldback, design, partition, _ = _case(tmp_path)
    result = discover_constructions(
        request,
        foldback=verify_foldback_neighborhood_result(foldback),
        basal=None,
        design=design,
        source_partition=partition,
    ).result
    realization = result.realizations[0]
    binding = realization.source_partition_binding
    assert binding is not None
    forged_binding = SourcePartitionBinding.create(
        **(
            binding.model_dump(mode="python", exclude={"binding_id"})
            | {"selected_state_id": "hop:construction-state/" + "0" * 64 + "@1"}
        )
    )
    forged_realization = realization.model_copy(update={"source_partition_binding": forged_binding})

    with pytest.raises(ValueError, match="molecular facts"):
        validate_source_partition_result_contract(
            request=result.request,
            provenance=result.provenance,
            authority=result.source_partition_authority,
            realizations=(forged_realization,),
            rejection_candidates=result.source_partition_rejection_candidates,
            dispositions=result.combination_dispositions,
            foldback_authority=result.foldback_authority,
            basal_authority=result.basal_authority,
        )


def test_selected_partition_rejection_reason_cannot_be_resealed(
    tmp_path: Path,
) -> None:
    request, foldback, design, partition, _ = _case(tmp_path)
    result = discover_constructions(
        request,
        foldback=verify_foldback_neighborhood_result(foldback),
        basal=None,
        design=design,
        source_partition=partition,
    ).result
    dispositions = tuple(
        item.model_copy(
            update={
                "rejection_reason": (CompositionRejectionCode.SOURCE_PARTITION_CUT_INCOMPATIBLE)
            }
        )
        if item.rejection_reason is CompositionRejectionCode.SOURCE_PARTITION_SOURCE_INCOMPATIBLE
        else item
        for item in result.combination_dispositions
    )
    content = {
        name: getattr(result, name)
        for name in ConstructionSpaceResult.model_fields
        if name != "result_id"
    }
    content.update(
        {
            "combination_dispositions": dispositions,
            "failure_reasons": (
                FailureReasonCount(
                    code=CompositionRejectionCode.SOURCE_PARTITION_CUT_INCOMPATIBLE,
                    count=1,
                ),
            ),
        }
    )

    with pytest.raises(ValueError, match="source-partition rejection"):
        ConstructionSpaceResult.create(**content)
