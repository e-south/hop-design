"""
--------------------------------------------------------------------------------
HOP Design
tests/contract/test_construction_contracts.py

Tests payload-centered construction and retained-overhead search contracts.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from hop_design.models.construction import (
    BasalGeometryDomain,
    BasalPairAllowance,
    BasalPairConstraint,
    CompleteConstructionRealization,
    ConstructionConstraints,
    ConstructionEndpoint,
    ConstructionExecution,
    ConstructionPreferences,
    DigitalDesignStatus,
    FailureReasonCount,
    FinalPayloadReference,
    FinalProductReference,
    FoldbackGeometryDomain,
    FoldbackTarget,
    LocalNeighborhoodFamily,
    LocalNeighborhoodRequest,
    LocalRealization,
    MethodResolutionStatus,
    NeighborhoodClaimBoundary,
    NeighborhoodDiscoveryResult,
    NeighborhoodProvenance,
    NeighborhoodSearchPlan,
    OverheadLevelSummary,
    PairState,
    PairStateException,
    PayloadCompatibilityAccounting,
    PayloadCompatibilityStatus,
    PayloadSourceMap,
    PayloadSourceSegment,
    ProjectionReference,
    RealizationGroup,
    RealizationGrouping,
    RouteFamily,
    SearchCompletionStatus,
    SearchDisposition,
    SearchFeasibilityStatus,
    SearchTerminationReason,
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


def _foldback_target() -> FoldbackTarget:
    return FoldbackTarget(
        junction_offset_nt=0,
        loop_length_nt=3,
        annealing_arm_length_bp=3,
    )


def _foldback_request(
    *,
    max_search_nodes: int = 100,
    max_retained_overhead_nt: int = 9,
) -> LocalNeighborhoodRequest:
    return LocalNeighborhoodRequest(
        name="compact foldback",
        payload=_payload(),
        family=LocalNeighborhoodFamily.FOLDBACK,
        route_family=RouteFamily.LINEAR_SOURCE_V1,
        endpoint=ConstructionEndpoint.SSDNA_HAIRPIN,
        geometry_domain=FoldbackGeometryDomain(
            junction_offsets_nt=(0,),
            loop_lengths_nt=(3,),
            annealing_arm_lengths_bp=(3,),
        ),
        hard_constraints=ConstructionConstraints(),
        enzyme_provisioning=_enzyme_provisioning(),
        search=NeighborhoodSearchPlan(
            max_retained_overhead_nt=max_retained_overhead_nt,
            max_search_nodes=max_search_nodes,
            max_realizations=20,
        ),
    )


def _level(
    retained_overhead_nt: int,
    realization_ids: tuple[str, ...] = (),
    failure_reasons: tuple[FailureReasonCount, ...] = (),
    *,
    complete: bool = True,
) -> OverheadLevelSummary:
    rejected_count = sum(reason.count for reason in failure_reasons)
    return OverheadLevelSummary(
        retained_overhead_nt=retained_overhead_nt,
        examined=True,
        complete=complete,
        candidate_count=len(realization_ids) + rejected_count,
        realization_ids=realization_ids,
        rejected_count=rejected_count,
        failure_reasons=failure_reasons,
    )


def _execution(request: LocalNeighborhoodRequest) -> ConstructionExecution:
    return ConstructionExecution(
        problem_id=problem_id(request),
        hop_version="0.1.0a7",
        route_implementation_version="linear-source/1",
        search=request.search,
        max_operations=request.enzyme_provisioning.max_operations,
        environment={},
    )


def _infeasible_result(request: LocalNeighborhoodRequest) -> NeighborhoodDiscoveryResult:
    execution = _execution(request)
    levels = tuple(
        _level(
            overhead,
            failure_reasons=(FailureReasonCount(code="no-compatible-site", count=1),),
        )
        for overhead in range(request.search.max_retained_overhead_nt + 1)
    )
    rejected_count = len(levels)
    return NeighborhoodDiscoveryResult(
        disposition=SearchDisposition(
            completion=SearchCompletionStatus.COMPLETE,
            feasibility=SearchFeasibilityStatus.INFEASIBLE,
            termination_reason=SearchTerminationReason.EXHAUSTED_DOMAIN,
        ),
        request=request,
        problem_id=problem_id(request),
        execution_id=execution.execution_id,
        execution=execution,
        overhead_levels=levels,
        realizations=(),
        achieved_geometry_groups=(),
        rejected_count=rejected_count,
        failure_reasons=(FailureReasonCount(code="no-compatible-site", count=rejected_count),),
        payload_compatibility=PayloadCompatibilityAccounting(
            status=PayloadCompatibilityStatus.COMPLETE,
            total_assignments=1,
            compatible_assignments=0,
            excluded_assignments=1,
            conflict_counts=(FailureReasonCount(code="payload-site-conflict", count=1),),
            exhaustive=True,
        ),
        provenance=NeighborhoodProvenance(
            hop_version=execution.hop_version,
            route_implementation_version=execution.route_implementation_version,
            enzyme_catalog_digest=request.enzyme_catalog_digest,
        ),
        projection_inventory=(),
        claim_boundary=NeighborhoodClaimBoundary(
            digital_design=DigitalDesignStatus.VERIFIED,
            method=MethodResolutionStatus.NOT_RESOLVED,
        ),
    )


def test_local_identity_bearing_failure_reasons_require_canonical_order() -> None:
    reasons = (
        FailureReasonCount(code="z-conflict", count=1),
        FailureReasonCount(code="a-conflict", count=1),
    )

    with pytest.raises(ValidationError, match="canonical order"):
        _level(0, failure_reasons=reasons)


def test_local_result_replays_embedded_execution_and_provenance() -> None:
    result = _infeasible_result(_foldback_request())

    changed = result.model_dump(mode="python")
    changed["execution"]["max_operations"] += 1
    with pytest.raises(ValidationError, match=r"execution.*request"):
        NeighborhoodDiscoveryResult.model_validate(changed)

    changed = result.model_dump(mode="python")
    changed["provenance"]["route_implementation_version"] = "different-route/1"
    with pytest.raises(ValidationError, match=r"provenance.*execution"):
        NeighborhoodDiscoveryResult.model_validate(changed)


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


def test_neighborhood_payload_accounting_cardinality_must_replay_the_request() -> None:
    result = _infeasible_result(_foldback_request())
    changed = result.model_dump(mode="python")
    changed["payload_compatibility"] = result.payload_compatibility.model_copy(
        update={"total_assignments": 2, "excluded_assignments": 2}
    )

    with pytest.raises(ValidationError, match="payload cardinality"):
        NeighborhoodDiscoveryResult.model_validate(changed)


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


def test_geometry_domains_are_canonical_and_enforce_structural_floors() -> None:
    domain = FoldbackGeometryDomain(
        junction_offsets_nt=(2, 0, 1),
        loop_lengths_nt=(4, 3),
        annealing_arm_lengths_bp=(4, 3),
    )
    assert domain.junction_offsets_nt == (0, 1, 2)
    assert domain.loop_lengths_nt == (3, 4)
    assert domain.annealing_arm_lengths_bp == (3, 4)

    with pytest.raises(ValidationError, match="structural floor"):
        FoldbackGeometryDomain(loop_lengths_nt=(2,))
    with pytest.raises(ValidationError, match="must not repeat"):
        FoldbackGeometryDomain(junction_offsets_nt=(0, 0))


def test_basal_domains_are_limited_to_the_hairpin_pcr_intermediate() -> None:
    pairing = (
        BasalPairConstraint(
            position_from_ligation=0,
            allowed_class=BasalPairAllowance.MATCH,
        ),
    )
    base = {
        "payload": _payload(),
        "family": LocalNeighborhoodFamily.BASAL,
        "route_family": RouteFamily.LINEAR_SOURCE_V1,
        "geometry_domain": BasalGeometryDomain(pairing_constraints=pairing),
        "hard_constraints": ConstructionConstraints(),
        "enzyme_provisioning": _enzyme_provisioning(),
        "search": NeighborhoodSearchPlan(
            max_retained_overhead_nt=2,
            max_search_nodes=10,
            max_realizations=10,
        ),
    }

    for endpoint in (
        ConstructionEndpoint.SSDNA_HAIRPIN,
        ConstructionEndpoint.CLONE_READY_DUPLEX,
    ):
        with pytest.raises(ValidationError, match="hairpin_pcr_duplex"):
            LocalNeighborhoodRequest(**base, endpoint=endpoint)

    request = LocalNeighborhoodRequest(
        **base,
        endpoint=ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
    )
    assert request.endpoint is ConstructionEndpoint.HAIRPIN_PCR_DUPLEX


def test_local_request_family_must_match_geometry_domain() -> None:
    with pytest.raises(ValidationError, match="family must match"):
        LocalNeighborhoodRequest(
            payload=_payload(),
            family=LocalNeighborhoodFamily.BASAL,
            route_family=RouteFamily.LINEAR_SOURCE_V1,
            endpoint=ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
            geometry_domain=FoldbackGeometryDomain(),
            hard_constraints=ConstructionConstraints(),
            enzyme_provisioning=_enzyme_provisioning(),
            search=NeighborhoodSearchPlan(
                max_retained_overhead_nt=9,
                max_search_nodes=10,
                max_realizations=10,
            ),
        )


def test_overhead_level_accounting_partitions_every_examined_candidate() -> None:
    level = _level(
        0,
        realization_ids=("realization-a", "realization-b"),
        failure_reasons=(FailureReasonCount(code="site-conflict", count=1),),
    )
    assert level.candidate_count == len(level.realization_ids) + level.rejected_count

    changed = level.model_dump(mode="python")
    changed["candidate_count"] = 4
    with pytest.raises(ValidationError, match="candidate count"):
        OverheadLevelSummary.model_validate(changed)

    changed = level.model_dump(mode="python")
    changed["failure_reasons"] = (FailureReasonCount(code="site-conflict", count=2),)
    with pytest.raises(ValidationError, match="partition rejected"):
        OverheadLevelSummary.model_validate(changed)


def test_result_allows_only_a_final_partial_overhead_level() -> None:
    result = _infeasible_result(_foldback_request())
    changed = result.model_dump(mode="python")
    changed["disposition"] = SearchDisposition(
        completion=SearchCompletionStatus.TRUNCATED,
        feasibility=SearchFeasibilityStatus.UNKNOWN,
        termination_reason=SearchTerminationReason.EVALUATION_CAP,
    )
    changed["overhead_levels"][0]["complete"] = False
    with pytest.raises(ValidationError, match="Only the final recorded overhead level"):
        NeighborhoodDiscoveryResult.model_validate(changed)

    changed["overhead_levels"][0]["complete"] = True
    changed["overhead_levels"][-1]["complete"] = False
    changed["disposition"] = result.disposition
    with pytest.raises(ValidationError, match="Complete coverage"):
        NeighborhoodDiscoveryResult.model_validate(changed)


def test_truncated_result_requires_unresolved_declared_work() -> None:
    result = _infeasible_result(_foldback_request())
    changed = result.model_dump(mode="python")
    changed["disposition"] = SearchDisposition(
        completion=SearchCompletionStatus.TRUNCATED,
        feasibility=SearchFeasibilityStatus.UNKNOWN,
        termination_reason=SearchTerminationReason.EVALUATION_CAP,
    )

    with pytest.raises(ValidationError, match="unresolved work"):
        NeighborhoodDiscoveryResult.model_validate(changed)


def test_search_disposition_separates_completion_from_feasibility() -> None:
    feasible = SearchDisposition(
        completion=SearchCompletionStatus.COMPLETE,
        feasibility=SearchFeasibilityStatus.FEASIBLE,
        termination_reason=SearchTerminationReason.EXHAUSTED_DOMAIN,
    )
    assert feasible.completion is SearchCompletionStatus.COMPLETE

    with pytest.raises(ValidationError, match="not a completion state"):
        SearchDisposition(
            completion=SearchCompletionStatus.INFEASIBLE,
            feasibility=SearchFeasibilityStatus.INFEASIBLE,
            termination_reason=SearchTerminationReason.EXHAUSTED_DOMAIN,
        )
    with pytest.raises(ValidationError, match="cannot establish infeasibility"):
        SearchDisposition(
            completion=SearchCompletionStatus.TRUNCATED,
            feasibility=SearchFeasibilityStatus.INFEASIBLE,
            termination_reason=SearchTerminationReason.EVALUATION_CAP,
        )


def test_neighborhood_result_rejects_level_and_global_accounting_drift() -> None:
    result = _infeasible_result(_foldback_request())
    changed = result.model_dump(mode="python")
    changed["overhead_levels"][0]["failure_reasons"] = (
        FailureReasonCount(code="different-primary-reason", count=1),
    )

    with pytest.raises(ValidationError, match="aggregate to global failure reasons"):
        NeighborhoodDiscoveryResult.model_validate(changed)


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

    execution_a = _execution(first).model_copy(update={"environment": {"python": "3.12"}})
    execution_b = execution_a.model_copy(
        update={"max_operations": changed_ceiling.enzyme_provisioning.max_operations}
    )
    execution_c = execution_a.model_copy(update={"search": second.search})
    assert execution_a.execution_id != execution_b.execution_id
    assert execution_a.execution_id != execution_c.execution_id
    assert geometry_id(_foldback_target()) == geometry_id(_foldback_target())


def test_declared_preferences_do_not_change_feasibility_identity() -> None:
    request = _foldback_request()
    preferred = request.model_copy(
        update={
            "preferences": ConstructionPreferences(
                preferred_enzyme_ids=("example:enzyme/nick-a@1",),
            )
        }
    )
    assert problem_id(request) == problem_id(preferred)


def test_result_embeds_reversible_geometry_groups_and_claim_boundary() -> None:
    request = _foldback_request()
    execution = _execution(request)
    realization = LocalRealization.create(
        local_sequence="AAACCC",
        enzyme_binding_ids=("enzyme-a",),
        stage_ids=("stage-a",),
        achieved_geometry=_foldback_target(),
    )
    levels = tuple(
        _level(overhead, (realization.local_realization_id,) if overhead == 9 else ())
        for overhead in range(10)
    )
    fields = {
        "disposition": SearchDisposition(
            completion=SearchCompletionStatus.COMPLETE,
            feasibility=SearchFeasibilityStatus.FEASIBLE,
            termination_reason=SearchTerminationReason.EXHAUSTED_DOMAIN,
        ),
        "request": request,
        "problem_id": problem_id(request),
        "execution_id": execution.execution_id,
        "execution": execution,
        "overhead_levels": levels,
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
            hop_version=execution.hop_version,
            route_implementation_version=execution.route_implementation_version,
            enzyme_catalog_digest=request.enzyme_catalog_digest,
        ),
        "projection_inventory": (),
        "claim_boundary": NeighborhoodClaimBoundary(
            digital_design=DigitalDesignStatus.VERIFIED,
            method=MethodResolutionStatus.NOT_RESOLVED,
        ),
    }
    with pytest.raises(ValidationError, match="cover every realization exactly once"):
        NeighborhoodDiscoveryResult(**fields, achieved_geometry_groups=())

    group = RealizationGroup(
        grouping=RealizationGrouping.ACHIEVED_GEOMETRY,
        group_key=geometry_id(realization.achieved_geometry),
        realization_ids=(realization.local_realization_id,),
        multiplicity=1,
    )
    result = NeighborhoodDiscoveryResult(**fields, achieved_geometry_groups=(group,))
    assert result.claim_boundary.method is MethodResolutionStatus.NOT_RESOLVED
    assert result.schema_id == "hop.neighborhood-discovery-result/v4"
    assert result.claim_boundary.physical_construction == "not_recorded"


def test_grouping_projection_preserves_every_realization() -> None:
    target = _foldback_target()
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
            group_key=geometry_id(target),
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
