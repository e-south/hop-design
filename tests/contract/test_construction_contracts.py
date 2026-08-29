"""
--------------------------------------------------------------------------------
HOP Design
tests/contract/test_construction_contracts.py

Tests payload-centered construction contracts and discrete relaxation semantics.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from hop_design.design.relaxation import relaxation_shells
from hop_design.models.construction import (
    BasalPairClass,
    BasalPairingPosition,
    BasalTarget,
    CompleteConstructionRealization,
    ConstructionConstraints,
    ConstructionEndpoint,
    ConstructionExecution,
    ConstructionPreferences,
    DigitalDesignStatus,
    EndGenerationRequest,
    EnumerationPolicy,
    FailureReasonCount,
    FinalPayloadReference,
    FinalProductReference,
    FoldbackTarget,
    LocalNeighborhoodFamily,
    LocalNeighborhoodRequest,
    LocalRealization,
    MethodResolutionStatus,
    NeighborhoodClaimBoundary,
    NeighborhoodDiscoveryResult,
    NeighborhoodProvenance,
    PairState,
    PairStateException,
    PayloadCompatibilityAccounting,
    PayloadCompatibilityStatus,
    PayloadSourceMap,
    PayloadSourceSegment,
    ProjectionInventoryItem,
    ProjectionInventoryStatus,
    ProjectionReference,
    RealizationGroup,
    RealizationGrouping,
    RelaxationCoordinate,
    RelaxationMode,
    RelaxationPolicy,
    RelaxationShellSummary,
    RouteFamily,
    SearchCompletionStatus,
    SourceOrientation,
    geometry_id,
    grouped_realization_projection,
    problem_id,
    validate_linear_source_map,
    validate_linear_source_payload,
)
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.enzymes import (
    CharacterizedEnzyme,
    CharacterizedEnzymeCatalog,
    EnzymeClass,
    EnzymeProvisioningPolicy,
    RecognitionOrientationSemantics,
    ResultingEndModel,
    SubstrateRequirement,
    TargetMolecule,
    VendorMetadata,
)
from hop_design.models.junction import Strand
from hop_design.models.payload import DegeneratePayload, ExactPayload
from hop_design.models.references import ExternalRef


def _payload(*, display_name: str = "example") -> FinalPayloadReference:
    return FinalPayloadReference(
        display_name=display_name,
        payload=ExactPayload(sequence="ACTG"),
        basal_boundary=Boundary(offset=0),
        foldback_boundary=Boundary(offset=4),
    )


def _enzyme(
    *,
    enzyme_id: str = "example:enzyme/nick-a@1",
    vendor_name: str = "Vendor A",
) -> CharacterizedEnzyme:
    return CharacterizedEnzyme(
        enzyme_id=enzyme_id,
        canonical_name=enzyme_id.rsplit("/", maxsplit=1)[-1],
        enzyme_class=EnzymeClass.NICKASE,
        target_molecule=TargetMolecule.DNA,
        recognition_pattern="AAGC",
        recognition_orientation_semantics=RecognitionOrientationSemantics.BOTH_ORIENTATIONS,
        recognition_length=4,
        substrate_requirement=SubstrateRequirement.DUPLEX_DNA,
        cut_offset_reference_strand=1,
        cut_offset_complement_strand=None,
        resulting_end_model=ResultingEndModel.NICK,
        characterization_source=ExternalRef(
            system="literature",
            kind="enzyme-characterization",
            id=f"source-{enzyme_id}",
        ),
        vendor_metadata=(VendorMetadata(vendor_name=vendor_name),),
    )


def _enzyme_provisioning(
    *,
    max_operations: int = 4,
    vendor_name: str = "Vendor A",
    reserve_second: bool = False,
) -> EnzymeProvisioningPolicy:
    first = _enzyme(vendor_name=vendor_name)
    second = _enzyme(enzyme_id="example:enzyme/nick-b@1")
    return EnzymeProvisioningPolicy(
        catalog=CharacterizedEnzymeCatalog(
            catalog_id="example:enzyme-catalog/construction-test@1",
            enzymes=(first, second),
        ),
        allowed_enzyme_ids=(
            (first.enzyme_id,) if reserve_second else (first.enzyme_id, second.enzyme_id)
        ),
        forbidden_enzyme_ids=(),
        reserved_enzyme_ids=((second.enzyme_id,) if reserve_second else ()),
        max_operations=max_operations,
        role_restrictions=(),
    )


def _foldback_request(
    *,
    target: FoldbackTarget | None = None,
    max_search_nodes: int = 100,
) -> LocalNeighborhoodRequest:
    return LocalNeighborhoodRequest(
        name="compact foldback",
        payload=_payload(),
        family=LocalNeighborhoodFamily.FOLDBACK,
        route_family=RouteFamily.LINEAR_SOURCE_V1,
        endpoint=ConstructionEndpoint.SSDNA_HAIRPIN,
        target=target
        or FoldbackTarget(
            junction_offset_nt=0,
            loop_length_nt=3,
            annealing_arm_length_bp=3,
        ),
        hard_constraints=ConstructionConstraints(),
        enzyme_provisioning=_enzyme_provisioning(),
        relaxation=RelaxationPolicy(
            mode=RelaxationMode.FIRST_FEASIBLE_SHELL,
            max_radius=2,
            coordinates=(
                RelaxationCoordinate(name="loop_length_nt", minimum=2, maximum=4),
                RelaxationCoordinate(name="annealing_arm_length_bp", minimum=2, maximum=4),
            ),
        ),
        enumeration=EnumerationPolicy(max_search_nodes=max_search_nodes, max_realizations=20),
    )


def _infeasible_result(request: LocalNeighborhoodRequest) -> NeighborhoodDiscoveryResult:
    return NeighborhoodDiscoveryResult(
        status=SearchCompletionStatus.INFEASIBLE,
        request=request,
        problem_id=problem_id(request),
        execution_id="hop:execution/" + "a" * 64 + "@1",
        shells=tuple(
            RelaxationShellSummary(radius=radius, examined=True, realization_ids=())
            for radius in range(3)
        ),
        realizations=(),
        achieved_geometry_groups=(),
        rejected_count=3,
        failure_reasons=(FailureReasonCount(code="no-compatible-site", count=3),),
        payload_compatibility=PayloadCompatibilityAccounting(
            status=PayloadCompatibilityStatus.COMPLETE,
            total_assignments=1,
            compatible_assignments=0,
            excluded_assignments=1,
            conflict_counts=(FailureReasonCount(code="payload-site-conflict", count=1),),
            exhaustive=True,
        ),
        provenance=NeighborhoodProvenance(
            hop_version="0.1.0a7",
            route_implementation_version="linear-source/1",
            enzyme_catalog_digest=request.enzyme_catalog_digest,
        ),
        projection_inventory=(),
        claim_boundary=NeighborhoodClaimBoundary(
            digital_design=DigitalDesignStatus.VERIFIED,
            method=MethodResolutionStatus.NOT_RESOLVED,
        ),
    )


def test_payload_identity_ignores_presentation_and_linear_mapping_is_route_owned() -> None:
    assert (
        _payload(display_name="first").payload_spec_id
        == _payload(display_name="second").payload_spec_id
    )
    assert _payload().paired_sequence == "CAGT"

    segmented = PayloadSourceMap(
        segments=(
            PayloadSourceSegment(
                payload_span=Span(start=Boundary(offset=0), end=Boundary(offset=2)),
                source_material_id="source-a",
                source_span=Span(start=Boundary(offset=4), end=Boundary(offset=6)),
                orientation=SourceOrientation.FORWARD,
            ),
            PayloadSourceSegment(
                payload_span=Span(start=Boundary(offset=2), end=Boundary(offset=4)),
                source_material_id="source-b",
                source_span=Span(start=Boundary(offset=8), end=Boundary(offset=10)),
                orientation=SourceOrientation.FORWARD,
            ),
        )
    )
    assert len(segmented.segments) == 2
    with pytest.raises(ValueError, match="one contiguous source segment"):
        validate_linear_source_map(_payload(), segmented)

    contiguous = PayloadSourceMap(
        segments=(
            PayloadSourceSegment(
                payload_span=Span(start=Boundary(offset=0), end=Boundary(offset=4)),
                source_material_id="source-a",
                source_span=Span(start=Boundary(offset=7), end=Boundary(offset=11)),
                orientation=SourceOrientation.FORWARD,
            ),
        )
    )
    validate_linear_source_map(_payload(), contiguous)


def test_pair_state_exceptions_are_representable_but_linear_source_rejects_them() -> None:
    payload = FinalPayloadReference(
        payload=ExactPayload(sequence="ACTG"),
        basal_boundary=Boundary(offset=0),
        foldback_boundary=Boundary(offset=4),
        pair_state_exceptions=(
            PairStateException(
                payload_position=1,
                allowed_states=(PairState(reference_base="C", paired_base="A"),),
            ),
        ),
    )
    assert payload.pair_state_exceptions[0].allowed_states[0].paired_base == "A"
    with pytest.raises(ValueError, match="does not support pair-state exceptions"):
        validate_linear_source_payload(payload)


def test_payload_pair_state_identity_is_canonical_and_respects_authored_domains() -> None:
    states = (
        PairState(reference_base="C", paired_base="A"),
        PairState(reference_base="C", paired_base="G"),
    )
    first = FinalPayloadReference(
        payload=ExactPayload(sequence="ACTG"),
        basal_boundary=Boundary(offset=0),
        foldback_boundary=Boundary(offset=4),
        pair_state_exceptions=(
            PairStateException(payload_position=1, allowed_states=states),
            PairStateException(
                payload_position=2,
                allowed_states=(PairState(reference_base="T", paired_base="C"),),
            ),
        ),
    )
    reordered = first.model_copy(
        update={
            "pair_state_exceptions": (
                first.pair_state_exceptions[1],
                PairStateException(payload_position=1, allowed_states=tuple(reversed(states))),
            )
        }
    )
    assert first.payload_spec_id == reordered.payload_spec_id

    with pytest.raises(ValidationError, match="authored payload domain"):
        FinalPayloadReference(
            payload=ExactPayload(sequence="ACTG"),
            basal_boundary=Boundary(offset=0),
            foldback_boundary=Boundary(offset=4),
            pair_state_exceptions=(
                PairStateException(
                    payload_position=1,
                    allowed_states=(PairState(reference_base="G", paired_base="C"),),
                ),
            ),
        )

    FinalPayloadReference(
        payload=DegeneratePayload(sequence="ANTG"),
        basal_boundary=Boundary(offset=0),
        foldback_boundary=Boundary(offset=4),
        pair_state_exceptions=(
            PairStateException(
                payload_position=1,
                allowed_states=(PairState(reference_base="G", paired_base="C"),),
            ),
        ),
    )


def test_set_valued_request_inputs_have_canonical_ordering() -> None:
    first_end_request = EndGenerationRequest(
        type_iis_cut_offset_nt=4,
        requested_overhangs=("GGCC", "AATT"),
    )
    second_end_request = EndGenerationRequest(
        type_iis_cut_offset_nt=4,
        requested_overhangs=("AATT", "GGCC"),
    )
    assert first_end_request == second_end_request

    first_policy = RelaxationPolicy(
        mode=RelaxationMode.THROUGH_RADIUS,
        max_radius=1,
        coordinates=(
            RelaxationCoordinate(name="loop_length_nt", minimum=2, maximum=4),
            RelaxationCoordinate(name="annealing_arm_length_bp", minimum=2, maximum=4),
        ),
    )
    second_policy = RelaxationPolicy(
        mode=RelaxationMode.THROUGH_RADIUS,
        max_radius=1,
        coordinates=tuple(reversed(first_policy.coordinates)),
    )
    first_request = _foldback_request().model_copy(update={"relaxation": first_policy})
    second_request = _foldback_request().model_copy(update={"relaxation": second_policy})
    assert problem_id(first_request) == problem_id(second_request)
    assert relaxation_shells(first_request.target, first_policy) == relaxation_shells(
        second_request.target, second_policy
    )


def test_endpoint_specific_basal_targets_reject_leaked_requirements() -> None:
    pairing = (
        BasalPairingPosition(
            profile_position=0,
            source_base="G",
            adapter_base="C",
            pair_class=BasalPairClass.MATCH,
        ),
    )
    base = {
        "payload": _payload(),
        "family": LocalNeighborhoodFamily.BASAL,
        "route_family": RouteFamily.LINEAR_SOURCE_V1,
        "hard_constraints": ConstructionConstraints(),
        "enzyme_provisioning": _enzyme_provisioning(),
        "relaxation": RelaxationPolicy(mode=RelaxationMode.EXACT_ONLY, max_radius=0),
        "enumeration": EnumerationPolicy(max_search_nodes=10, max_realizations=10),
    }

    LocalNeighborhoodRequest(
        **base,
        endpoint=ConstructionEndpoint.SSDNA_HAIRPIN,
        target=BasalTarget(nick_strand=Strand.TOP, nick_offset_nt=0),
    )
    with pytest.raises(ValidationError, match="must not request end generation"):
        LocalNeighborhoodRequest(
            **base,
            endpoint=ConstructionEndpoint.SSDNA_HAIRPIN,
            target=BasalTarget(
                nick_strand=Strand.TOP,
                nick_offset_nt=0,
                end_generation=EndGenerationRequest(type_iis_cut_offset_nt=4),
            ),
        )
    with pytest.raises(ValidationError, match="requires a pairing profile"):
        LocalNeighborhoodRequest(
            **base,
            endpoint=ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
            target=BasalTarget(nick_strand=Strand.TOP, nick_offset_nt=0),
        )

    clone_request = LocalNeighborhoodRequest(
        **base,
        endpoint=ConstructionEndpoint.CLONE_READY_DUPLEX,
        target=BasalTarget(
            nick_strand=Strand.TOP,
            nick_offset_nt=0,
            pairing_profile=pairing,
            ligation_proximal_match_required=True,
            end_generation=EndGenerationRequest(
                type_iis_cut_offset_nt=4,
                requested_overhangs=("AATT", "GGCC"),
            ),
        ),
    )
    assert clone_request.target.end_generation is not None


def test_local_request_family_must_match_target() -> None:
    with pytest.raises(ValidationError, match="family must match"):
        LocalNeighborhoodRequest(
            name="wrong family",
            payload=_payload(),
            family=LocalNeighborhoodFamily.BASAL,
            route_family=RouteFamily.LINEAR_SOURCE_V1,
            endpoint=ConstructionEndpoint.SSDNA_HAIRPIN,
            target=FoldbackTarget(
                junction_offset_nt=0,
                loop_length_nt=3,
                annealing_arm_length_bp=3,
            ),
            hard_constraints=ConstructionConstraints(),
            enzyme_provisioning=_enzyme_provisioning(),
            relaxation=RelaxationPolicy(mode=RelaxationMode.EXACT_ONLY, max_radius=0),
            enumeration=EnumerationPolicy(max_search_nodes=10, max_realizations=10),
        )


def test_relaxation_shells_are_exact_first_bounded_and_directionally_unbiased() -> None:
    request = _foldback_request()
    shells = relaxation_shells(request.target, request.relaxation)

    assert [shell.radius for shell in shells] == [0, 1, 2]
    assert shells[0].geometries == (request.target,)
    assert {
        (geometry.loop_length_nt, geometry.annealing_arm_length_bp)
        for geometry in shells[1].geometries
    } == {(2, 3), (3, 2), (3, 4), (4, 3)}
    assert all(
        geometry.junction_offset_nt == 0 for shell in shells for geometry in shell.geometries
    )

    exact = relaxation_shells(
        request.target,
        RelaxationPolicy(mode=RelaxationMode.EXACT_ONLY, max_radius=0),
    )
    assert len(exact) == 1
    assert exact[0].radius == 0


def test_problem_and_execution_identity_separate_science_from_runtime() -> None:
    first = _foldback_request(max_search_nodes=100)
    second = _foldback_request(max_search_nodes=200)
    assert problem_id(first) == problem_id(second)
    assert problem_id(first) == problem_id(first.model_copy(update={"name": "renamed"}))
    changed_provisioning = first.model_copy(
        update={"enzyme_provisioning": _enzyme_provisioning(reserve_second=True)}
    )
    assert problem_id(first) != problem_id(changed_provisioning)
    changed_vendor = first.model_copy(
        update={"enzyme_provisioning": _enzyme_provisioning(vendor_name="Vendor B")}
    )
    assert problem_id(first) == problem_id(changed_vendor)
    assert _infeasible_result(first).result_id == _infeasible_result(changed_vendor).result_id
    changed_ceiling = first.model_copy(
        update={"enzyme_provisioning": _enzyme_provisioning(max_operations=8)}
    )
    assert problem_id(first) == problem_id(changed_ceiling)

    execution_a = ConstructionExecution(
        problem_id=problem_id(first),
        hop_version="0.1.0a7",
        route_implementation_version="linear-source/1",
        enumeration=first.enumeration,
        max_operations=first.enzyme_provisioning.max_operations,
        environment={"python": "3.12"},
    )
    execution_b = execution_a.model_copy(
        update={"max_operations": changed_ceiling.enzyme_provisioning.max_operations},
    )
    assert execution_a.execution_id != execution_b.execution_id
    execution_c = execution_a.model_copy(update={"enumeration": second.enumeration})
    assert execution_a.execution_id != execution_c.execution_id
    assert geometry_id(first.target) == geometry_id(
        first.target.model_copy(update={"loop_length_nt": 3})
    )


def test_declared_preferences_do_not_change_feasibility_identity() -> None:
    request = _foldback_request()
    assert request.preferences == ConstructionPreferences()
    preferred = request.model_copy(
        update={
            "preferences": ConstructionPreferences(
                preferred_enzyme_ids=("example:enzyme/nick-a@1",),
            )
        }
    )
    assert problem_id(request) == problem_id(preferred)


def test_result_status_is_truthful_and_invalid_is_not_a_search_disposition() -> None:
    request = _foldback_request()
    result_metadata = {
        "failure_reasons": (FailureReasonCount(code="no-compatible-site", count=3),),
        "payload_compatibility": PayloadCompatibilityAccounting(
            status=PayloadCompatibilityStatus.COMPLETE,
            total_assignments=1,
            compatible_assignments=0,
            excluded_assignments=1,
            conflict_counts=(FailureReasonCount(code="payload-site-conflict", count=1),),
            exhaustive=True,
        ),
        "provenance": NeighborhoodProvenance(
            hop_version="0.1.0a7",
            route_implementation_version="linear-source/1",
            enzyme_catalog_digest=request.enzyme_catalog_digest,
        ),
        "projection_inventory": (
            ProjectionInventoryItem(
                projection_schema="hop.geometry-groups/v1",
                renderer_version="1",
                status=ProjectionInventoryStatus.NOT_GENERATED,
            ),
        ),
        "claim_boundary": NeighborhoodClaimBoundary(
            digital_design=DigitalDesignStatus.VERIFIED,
            method=MethodResolutionStatus.NOT_RESOLVED,
        ),
        "achieved_geometry_groups": (),
    }
    with pytest.raises(ValidationError):
        NeighborhoodDiscoveryResult(
            status="invalid",
            request=request,
            problem_id=problem_id(request),
            execution_id="hop:execution/" + "a" * 64 + "@1",
            shells=(),
            realizations=(),
            rejected_count=0,
            **result_metadata,
        )
    with pytest.raises(ValidationError, match="truncation reasons"):
        NeighborhoodDiscoveryResult(
            status=SearchCompletionStatus.TRUNCATED,
            request=request,
            problem_id=problem_id(request),
            execution_id="hop:execution/" + "a" * 64 + "@1",
            shells=(RelaxationShellSummary(radius=0, examined=True, realization_ids=()),),
            realizations=(),
            rejected_count=0,
            **result_metadata,
        )
    with pytest.raises(ValidationError, match="all declared relaxation shells"):
        NeighborhoodDiscoveryResult(
            status=SearchCompletionStatus.INFEASIBLE,
            request=request,
            problem_id=problem_id(request),
            execution_id="hop:execution/" + "a" * 64 + "@1",
            shells=(RelaxationShellSummary(radius=0, examined=True, realization_ids=()),),
            realizations=(),
            rejected_count=3,
            **result_metadata,
        )
    infeasible = NeighborhoodDiscoveryResult(
        status=SearchCompletionStatus.INFEASIBLE,
        request=request,
        problem_id=problem_id(request),
        execution_id="hop:execution/" + "a" * 64 + "@1",
        shells=tuple(
            RelaxationShellSummary(radius=radius, examined=True, realization_ids=())
            for radius in range(3)
        ),
        realizations=(),
        rejected_count=3,
        **result_metadata,
    )
    assert infeasible.result_id.startswith("hop:neighborhood-result/")
    assert infeasible.schema_id == "hop.neighborhood-discovery-result/v1"
    assert infeasible.provenance.enzyme_catalog_digest == request.enzyme_catalog_digest
    assert infeasible.payload_compatibility.exhaustive is True
    assert infeasible.claim_boundary.physical_construction == "not_recorded"


def test_result_embeds_reversible_geometry_groups_and_claim_boundary() -> None:
    request = _foldback_request()
    realization = LocalRealization.create(
        local_sequence="AAACCC",
        enzyme_binding_ids=("enzyme-a",),
        stage_ids=("stage-a",),
        achieved_geometry=request.target,
    )
    result_fields = {
        "status": SearchCompletionStatus.COMPLETE,
        "request": request,
        "problem_id": problem_id(request),
        "execution_id": "hop:execution/" + "a" * 64 + "@1",
        "shells": (
            RelaxationShellSummary(
                radius=0,
                examined=True,
                realization_ids=(realization.local_realization_id,),
            ),
        ),
        "realizations": (realization,),
        "rejected_count": 0,
        "failure_reasons": (),
        "payload_compatibility": PayloadCompatibilityAccounting(
            status=PayloadCompatibilityStatus.COMPLETE,
            total_assignments=1,
            compatible_assignments=1,
            excluded_assignments=0,
            exhaustive=True,
        ),
        "provenance": NeighborhoodProvenance(
            hop_version="0.1.0a7",
            route_implementation_version="linear-source/1",
            enzyme_catalog_digest=request.enzyme_catalog_digest,
        ),
        "projection_inventory": (),
        "claim_boundary": NeighborhoodClaimBoundary(
            digital_design=DigitalDesignStatus.VERIFIED,
            method=MethodResolutionStatus.RESOLVED,
        ),
    }
    with pytest.raises(ValidationError, match="cover every realization exactly once"):
        NeighborhoodDiscoveryResult(**result_fields, achieved_geometry_groups=())
    with pytest.raises(ValidationError, match="group key must match"):
        NeighborhoodDiscoveryResult(
            **result_fields,
            achieved_geometry_groups=(
                RealizationGroup(
                    grouping=RealizationGrouping.ACHIEVED_GEOMETRY,
                    group_key="hop:geometry/" + "e" * 64 + "@1",
                    realization_ids=(realization.local_realization_id,),
                    multiplicity=1,
                ),
            ),
        )

    result = NeighborhoodDiscoveryResult(
        **result_fields,
        achieved_geometry_groups=(
            RealizationGroup(
                grouping=RealizationGrouping.ACHIEVED_GEOMETRY,
                group_key=geometry_id(request.target),
                realization_ids=(realization.local_realization_id,),
                multiplicity=1,
            ),
        ),
    )
    assert result.claim_boundary.method is MethodResolutionStatus.RESOLVED

    relaxed_geometry = request.target.model_copy(update={"loop_length_nt": 4})
    wrong_shell_realization = LocalRealization.create(
        local_sequence="AAAGGG",
        enzyme_binding_ids=("enzyme-a",),
        stage_ids=("stage-a",),
        achieved_geometry=relaxed_geometry,
    )
    with pytest.raises(ValidationError, match="declared relaxation shell"):
        NeighborhoodDiscoveryResult(
            **{
                **result_fields,
                "shells": (
                    RelaxationShellSummary(
                        radius=0,
                        examined=True,
                        realization_ids=(wrong_shell_realization.local_realization_id,),
                    ),
                ),
                "realizations": (wrong_shell_realization,),
            },
            achieved_geometry_groups=(
                RealizationGroup(
                    grouping=RealizationGrouping.ACHIEVED_GEOMETRY,
                    group_key=geometry_id(relaxed_geometry),
                    realization_ids=(wrong_shell_realization.local_realization_id,),
                    multiplicity=1,
                ),
            ),
        )

    non_relaxed_geometry = request.target.model_copy(update={"junction_offset_nt": 1})
    non_relaxed_realization = LocalRealization.create(
        local_sequence="CCCGGG",
        enzyme_binding_ids=("enzyme-a",),
        stage_ids=("stage-a",),
        achieved_geometry=non_relaxed_geometry,
    )
    with pytest.raises(ValidationError, match="non-enabled geometry field"):
        NeighborhoodDiscoveryResult(
            **{
                **result_fields,
                "shells": (
                    RelaxationShellSummary(
                        radius=0,
                        examined=True,
                        realization_ids=(non_relaxed_realization.local_realization_id,),
                    ),
                ),
                "realizations": (non_relaxed_realization,),
            },
            achieved_geometry_groups=(
                RealizationGroup(
                    grouping=RealizationGrouping.ACHIEVED_GEOMETRY,
                    group_key=geometry_id(non_relaxed_geometry),
                    realization_ids=(non_relaxed_realization.local_realization_id,),
                    multiplicity=1,
                ),
            ),
        )

    wrong_family_geometry = BasalTarget(nick_strand=Strand.TOP, nick_offset_nt=0)
    wrong_family_realization = LocalRealization.create(
        local_sequence="TTTGGG",
        enzyme_binding_ids=("enzyme-a",),
        stage_ids=("stage-a",),
        achieved_geometry=wrong_family_geometry,
    )
    with pytest.raises(ValidationError, match="requested neighborhood family"):
        NeighborhoodDiscoveryResult(
            **{
                **result_fields,
                "shells": (
                    RelaxationShellSummary(
                        radius=0,
                        examined=True,
                        realization_ids=(wrong_family_realization.local_realization_id,),
                    ),
                ),
                "realizations": (wrong_family_realization,),
            },
            achieved_geometry_groups=(
                RealizationGroup(
                    grouping=RealizationGrouping.ACHIEVED_GEOMETRY,
                    group_key=geometry_id(wrong_family_geometry),
                    realization_ids=(wrong_family_realization.local_realization_id,),
                    multiplicity=1,
                ),
            ),
        )


def test_grouping_is_reversible_and_preserves_every_realization() -> None:
    target = _foldback_request().target
    target_geometry_id = geometry_id(target)
    local_a = LocalRealization.create(
        local_sequence="AAACCC",
        enzyme_binding_ids=("enzyme-a",),
        stage_ids=("stage-a",),
        achieved_geometry=target,
    )
    local_b = LocalRealization.create(
        local_sequence="GGGCCC",
        enzyme_binding_ids=("enzyme-b",),
        stage_ids=("stage-b",),
        achieved_geometry=target,
    )
    final_product = FinalProductReference.create(
        endpoint=ConstructionEndpoint.SSDNA_HAIRPIN,
        sequence="AAACCCGGGTTT",
        topology="linear_hairpin",
        end_descriptors=("closed_foldback", "basal_3prime_hydroxyl"),
    )
    complete = CompleteConstructionRealization.create(
        precursor_sequence="AAACCCGGGTTT",
        local_realization_ids=(local_a.local_realization_id, local_b.local_realization_id),
        stage_ids=("stage-a", "stage-b"),
        final_product_id=final_product.final_product_id,
    )
    assert complete.complete_realization_id.startswith("hop:complete-realization/")

    groups = (
        RealizationGroup(
            grouping=RealizationGrouping.ACHIEVED_GEOMETRY,
            group_key=target_geometry_id,
            realization_ids=(local_a.local_realization_id, local_b.local_realization_id),
            multiplicity=2,
        ),
    )
    projection = grouped_realization_projection(
        result_id="hop:neighborhood-result/" + "b" * 64 + "@1",
        projection_schema="hop.geometry-groups/v1",
        renderer_version="1",
        realization_ids=(local_a.local_realization_id, local_b.local_realization_id),
        groups=groups,
    )
    assert isinstance(projection, ProjectionReference)
    with pytest.raises(ValidationError, match="projection_id must replay"):
        ProjectionReference(
            projection_id="hop:projection/" + "f" * 64 + "@1",
            result_id=projection.result_id,
            projection_schema=projection.projection_schema,
            renderer_version=projection.renderer_version,
            realization_ids=projection.realization_ids,
            groups=projection.groups,
        )
    with pytest.raises(ValidationError, match="cover every realization exactly once"):
        ProjectionReference(
            projection_id=projection.projection_id,
            result_id=projection.result_id,
            projection_schema=projection.projection_schema,
            renderer_version=projection.renderer_version,
            realization_ids=(local_a.local_realization_id,),
            groups=projection.groups,
        )
    with pytest.raises(ValueError, match="exactly once"):
        grouped_realization_projection(
            result_id="hop:neighborhood-result/" + "b" * 64 + "@1",
            projection_schema="hop.geometry-groups/v1",
            renderer_version="1",
            realization_ids=(local_a.local_realization_id, local_b.local_realization_id),
            groups=(
                groups[0].model_copy(
                    update={
                        "realization_ids": (local_a.local_realization_id,),
                        "multiplicity": 1,
                    }
                ),
            ),
        )
