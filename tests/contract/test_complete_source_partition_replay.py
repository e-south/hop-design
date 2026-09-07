"""
--------------------------------------------------------------------------------
HOP Design
tests/contract/test_complete_source_partition_replay.py

Tests molecular replay binding between selected source partitions and complete routes.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hop_design.design.construction.foldback import discover_foldback_neighborhood
from hop_design.design.construction.source_partition import discover_source_partitions
from hop_design.models.construction import FinalPayloadReference, FoldbackTarget
from hop_design.models.construction.complete.source_partition import (
    SourcePartitionBindingError,
    SourcePartitionBindingFailure,
    bind_source_partition,
)
from hop_design.models.construction.payload import (
    PayloadSourceMap,
    PayloadSourceSegment,
    SourceOrientation,
)
from hop_design.models.construction.source_partition import (
    SourceDuplexMaterial,
    SourcePartitionConstraints,
    SourcePartitionDiscoveryRequest,
    SourcePartitionEnumerationPolicy,
    SourcePartitionSurvivor,
)
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.enzymes import (
    CharacterizedEnzyme,
    CharacterizedEnzymeCatalog,
    EnzymeProvisioningPolicy,
    EnzymeRole,
    EnzymeRoleRestriction,
    RecognitionOrientationSemantics,
    VendorMetadata,
)
from hop_design.models.junction import Strand
from hop_design.models.molecular_state import FragmentLengthSelection
from hop_design.models.payload import ExactPayload
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

PAYLOAD = "GACAGACAGACAGACAGACA"


def _span(start: int, end: int) -> Span:
    return Span(start=Boundary(offset=start), end=Boundary(offset=end))


def _routes(tmp_path: Path):
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
    foldback_request = _request(
        nickase,
        _terminus_enzyme(),
        target=FoldbackTarget(
            junction_offset_nt=0,
            loop_length_nt=3,
            annealing_arm_length_bp=4,
        ),
    ).model_copy(update={"payload": payload})
    foldback = discover_foldback_neighborhood(foldback_request)
    design = _verified_design(tmp_path, PAYLOAD)
    request = _construction_request(
        payload=payload,
        foldback=foldback,
        basal=None,
        design=design,
    )
    result = _discover_raw(request, foldback=foldback, basal=None, design=design)
    by_stage_count = {
        len(item.construction_program.reaction_programs[0].stages): item
        for item in result.realizations
    }
    return payload, nickase, by_stage_count


def _partition_result(
    payload,
    nickase,
    realization,
    *,
    retain_released: bool = False,
    truncated: bool = False,
):
    source = realization.source_preparation.source_ssdna
    source_length = len(source.sequence_5prime)
    payload_length = len(payload.payload.sequence)
    cut = (
        realization.construction_program.reaction_programs[0]
        .stages[-1]
        .operations[0]
        .intended_binding.reference_cut
    )
    assert cut is not None
    released_length = source_length - cut.offset
    threshold = released_length if retain_released else released_length + 1
    source_id = "source-duplex"
    enzymes = (nickase,)
    if truncated:
        distractor_data = nickase.model_dump(mode="python") | {
            "enzyme_id": "example:enzyme/zz-distractor@1",
            "canonical_name": "zz-distractor",
            "recognition_pattern": "CGCGCG",
            "recognition_length": 6,
        }
        enzymes = (nickase, CharacterizedEnzyme.model_validate(distractor_data))
    allowed_ids = tuple(item.enzyme_id for item in enzymes)
    survivors = [
        SourcePartitionSurvivor(
            survivor_id="retained-top",
            precursor_strand=Strand.TOP,
            source_span=_span(0, cut.offset),
        ),
        SourcePartitionSurvivor(
            survivor_id="retained-bottom",
            precursor_strand=Strand.BOTTOM,
            source_span=_span(0, source_length),
        ),
    ]
    if retain_released:
        survivors.append(
            SourcePartitionSurvivor(
                survivor_id="retained-released-top",
                precursor_strand=Strand.TOP,
                source_span=_span(cut.offset, source_length),
            )
        )
    request = SourcePartitionDiscoveryRequest(
        payload=payload,
        source=SourceDuplexMaterial(
            material_id=source_id,
            top_sequence_5prime=source.sequence_5prime,
            top_five_prime_end=realization.materials[0].five_prime_end,
            top_three_prime_end=realization.materials[0].three_prime_end,
            bottom_five_prime_end=realization.materials[1].five_prime_end,
            bottom_three_prime_end=realization.materials[1].three_prime_end,
        ),
        payload_source_map=PayloadSourceMap(
            segments=(
                PayloadSourceSegment(
                    payload_span=_span(0, payload_length),
                    source_material_id=source_id,
                    source_span=realization.payload_source_map.segments[0].source_span,
                    orientation=SourceOrientation.FORWARD,
                ),
            )
        ),
        enzyme_provisioning=EnzymeProvisioningPolicy(
            catalog=CharacterizedEnzymeCatalog(
                catalog_id="example:enzyme-catalog/partition-binding@1",
                enzymes=enzymes,
            ),
            allowed_enzyme_ids=allowed_ids,
            forbidden_enzyme_ids=(),
            reserved_enzyme_ids=(),
            max_operations=2,
            role_restrictions=(
                EnzymeRoleRestriction(
                    role=EnzymeRole.STRAND_EXPOSURE,
                    allowed_enzyme_ids=allowed_ids,
                ),
            ),
        ),
        constraints=SourcePartitionConstraints(
            selection=FragmentLengthSelection(min_length_nt=threshold),
            required_survivors=tuple(survivors),
            max_enzymes_per_program=1,
        ),
        enumeration=SourcePartitionEnumerationPolicy(
            max_search_nodes=1,
            max_realizations=2,
        ),
    )
    return discover_source_partitions(request)


def _bind(payload, realization, partition, *, route_enzymes):
    return bind_source_partition(
        payload=payload,
        payload_source_map=realization.payload_source_map,
        source_preparation=realization.source_preparation,
        construction_program=realization.construction_program,
        materials=realization.materials,
        material_uses=realization.material_uses,
        route_enzyme_definitions=route_enzymes,
        partition_result=partition,
        selected_realization_id=partition.realizations[0].realization_id,
    )


def test_matching_partition_binds_representation_neutral_molecular_facts(
    tmp_path: Path,
) -> None:
    payload, nickase, routes = _routes(tmp_path)
    route = routes[1]
    partition = _partition_result(payload, nickase, route)

    binding = _bind(payload, route, partition, route_enzymes=(nickase,))

    assert binding.result_id == partition.result_id
    assert binding.realization_id == partition.realizations[0].realization_id
    assert binding.source_preparation_product_state_id == (
        route.source_preparation.product_state.state_id
    )


def test_selected_member_of_truncated_result_remains_exactly_bindable(
    tmp_path: Path,
) -> None:
    payload, nickase, routes = _routes(tmp_path)
    route = routes[1]
    partition = _partition_result(payload, nickase, route, truncated=True)

    binding = _bind(payload, route, partition, route_enzymes=(nickase,))

    assert partition.status == "truncated"
    assert binding.realization_id == partition.realizations[0].realization_id


def test_binding_reports_source_cut_and_selection_incompatibilities(
    tmp_path: Path,
) -> None:
    payload, nickase, routes = _routes(tmp_path)
    route = routes[1]
    partition = _partition_result(payload, nickase, route)
    map_segment = route.payload_source_map.segments[0]
    shifted_map = PayloadSourceMap(
        segments=(map_segment.model_copy(update={"source_span": _span(3, 3 + len(PAYLOAD))}),)
    )
    with pytest.raises(SourcePartitionBindingError) as source_error:
        bind_source_partition(
            payload=payload,
            payload_source_map=shifted_map,
            source_preparation=route.source_preparation,
            construction_program=route.construction_program,
            materials=route.materials,
            material_uses=route.material_uses,
            route_enzyme_definitions=(nickase,),
            partition_result=partition,
            selected_realization_id=partition.realizations[0].realization_id,
        )
    assert source_error.value.code is SourcePartitionBindingFailure.SOURCE_INCOMPATIBLE

    alternate_data = nickase.model_dump(mode="python") | {
        "enzyme_id": "example:enzyme/alternate-nick@1",
        "canonical_name": "alternate-nick",
    }
    alternate = CharacterizedEnzyme.model_validate(alternate_data)
    alternate_partition = _partition_result(payload, alternate, route)
    with pytest.raises(SourcePartitionBindingError) as cut_error:
        _bind(payload, route, alternate_partition, route_enzymes=(nickase,))
    assert cut_error.value.code is SourcePartitionBindingFailure.CUT_INCOMPATIBLE

    broad_partition = _partition_result(
        payload,
        nickase,
        route,
        retain_released=True,
    )
    with pytest.raises(SourcePartitionBindingError) as selection_error:
        _bind(payload, route, broad_partition, route_enzymes=(nickase,))
    assert selection_error.value.code is SourcePartitionBindingFailure.SELECTION_INCOMPATIBLE


def test_valid_sequential_route_is_not_flattened_into_one_partition_stage(
    tmp_path: Path,
) -> None:
    payload, nickase, routes = _routes(tmp_path)
    route = routes[2]
    partition = _partition_result(payload, nickase, route)

    with pytest.raises(SourcePartitionBindingError) as caught:
        _bind(payload, route, partition, route_enzymes=(nickase,))

    assert caught.value.code is SourcePartitionBindingFailure.STAGE_INCOMPATIBLE


def test_binding_rejects_conflicting_definition_behind_the_same_enzyme_id(
    tmp_path: Path,
) -> None:
    payload, nickase, routes = _routes(tmp_path)
    route = routes[1]
    conflicting = CharacterizedEnzyme.model_validate(
        nickase.model_dump(mode="python") | {"canonical_name": "conflicting-definition"}
    )
    partition = _partition_result(payload, conflicting, route)

    with pytest.raises(SourcePartitionBindingError) as caught:
        _bind(payload, route, partition, route_enzymes=(nickase,))

    assert caught.value.code is SourcePartitionBindingFailure.CUT_INCOMPATIBLE


def test_binding_ignores_procurement_metadata_when_definitions_match(
    tmp_path: Path,
) -> None:
    payload, nickase, routes = _routes(tmp_path)
    route = routes[1]
    procurement_variant = CharacterizedEnzyme.model_validate(
        nickase.model_dump(mode="python")
        | {
            "vendor_metadata": (
                VendorMetadata(vendor_name="Example supplier", catalog_number="EX-1"),
            )
        }
    )
    partition = _partition_result(payload, procurement_variant, route)

    binding = _bind(payload, route, partition, route_enzymes=(nickase,))

    assert binding.realization_id == partition.realizations[0].realization_id
