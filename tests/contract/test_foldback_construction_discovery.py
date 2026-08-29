"""
--------------------------------------------------------------------------------
HOP Design
tests/contract/test_foldback_construction_discovery.py

Tests payload-centered foldback discovery, relaxation, identity, and accounting.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from hop_design.design.construction.foldback import discover_foldback_neighborhood
from hop_design.design.construction.verification import (
    ConstructionVerificationError,
    VerifiedFoldbackNeighborhoodResult,
    verify_foldback_neighborhood_result,
)
from hop_design.models.construction import (
    ConstructionConstraints,
    ConstructionEndpoint,
    ConstructionPreferences,
    EnumerationPolicy,
    FinalPayloadReference,
    FoldbackTarget,
    LocalNeighborhoodFamily,
    LocalNeighborhoodRequest,
    NeighborhoodDiscoveryResult,
    PayloadCompatibilityAccounting,
    PayloadCompatibilityStatus,
    RelaxationCoordinate,
    RelaxationMode,
    RelaxationPolicy,
    RouteFamily,
    SearchCompletionStatus,
    problem_id,
)
from hop_design.models.construction.foldback import (
    FoldbackCleavageProgramKind,
    FoldbackNeighborhoodDiscoveryResult,
)
from hop_design.models.coordinates import Boundary
from hop_design.models.enzymes import (
    CharacterizedEnzyme,
    CharacterizedEnzymeCatalog,
    EnzymeClass,
    EnzymeProvisioningPolicy,
    EnzymeRole,
    EnzymeRoleRestriction,
    RecognitionOrientationSemantics,
    ResultingEndModel,
    SubstrateRequirement,
    TargetMolecule,
)
from hop_design.models.payload import DegeneratePayload, ExactPayload
from hop_design.models.references import ExternalRef


def _source(enzyme_id: str) -> ExternalRef:
    return ExternalRef(
        system="literature",
        kind="synthetic-characterization-fixture",
        id=enzyme_id,
    )


def _nickase(
    *,
    enzyme_id: str = "example:enzyme/foldback-nick@1",
    motif: str = "ACATTT",
    cut_offset: int = 0,
    orientation_semantics: RecognitionOrientationSemantics = (
        RecognitionOrientationSemantics.BOTH_ORIENTATIONS
    ),
) -> CharacterizedEnzyme:
    return CharacterizedEnzyme(
        enzyme_id=enzyme_id,
        canonical_name=enzyme_id.rsplit("/", maxsplit=1)[-1],
        enzyme_class=EnzymeClass.NICKASE,
        target_molecule=TargetMolecule.DNA,
        recognition_pattern=motif,
        recognition_orientation_semantics=orientation_semantics,
        recognition_length=len(motif),
        substrate_requirement=SubstrateRequirement.DUPLEX_DNA,
        cut_offset_reference_strand=cut_offset,
        cut_offset_complement_strand=None,
        resulting_end_model=ResultingEndModel.NICK,
        characterization_source=_source(enzyme_id),
    )


def _terminus_enzyme(
    *,
    reference_cut_offset: int = 0,
    motif: str = "GGCC",
    orientation_semantics: RecognitionOrientationSemantics = (
        RecognitionOrientationSemantics.DECLARED_ONLY
    ),
) -> CharacterizedEnzyme:
    enzyme_id = "example:enzyme/foldback-terminus@1"
    return CharacterizedEnzyme(
        enzyme_id=enzyme_id,
        canonical_name="foldback-terminus",
        enzyme_class=EnzymeClass.DUPLEX_RESTRICTION,
        target_molecule=TargetMolecule.DNA,
        recognition_pattern=motif,
        recognition_orientation_semantics=orientation_semantics,
        recognition_length=len(motif),
        substrate_requirement=SubstrateRequirement.DUPLEX_DNA,
        cut_offset_reference_strand=reference_cut_offset,
        cut_offset_complement_strand=0,
        resulting_end_model=ResultingEndModel.DUPLEX_BREAK,
        characterization_source=_source(enzyme_id),
    )


def _request(
    *enzymes: CharacterizedEnzyme,
    target: FoldbackTarget | None = None,
    relaxation: RelaxationPolicy | None = None,
    max_search_nodes: int = 100,
    max_realizations: int = 100,
) -> LocalNeighborhoodRequest:
    catalog = CharacterizedEnzymeCatalog(
        catalog_id="example:enzyme-catalog/foldback-construction@1",
        enzymes=enzymes,
    )
    roles = []
    nick_ids = tuple(
        enzyme.enzyme_id for enzyme in enzymes if enzyme.enzyme_class is EnzymeClass.NICKASE
    )
    terminus_ids = tuple(
        enzyme.enzyme_id
        for enzyme in enzymes
        if enzyme.enzyme_class is EnzymeClass.DUPLEX_RESTRICTION
    )
    if nick_ids:
        roles.append(
            EnzymeRoleRestriction(
                role=EnzymeRole.FOLDBACK_NICK,
                allowed_enzyme_ids=nick_ids,
            )
        )
    if terminus_ids:
        roles.append(
            EnzymeRoleRestriction(
                role=EnzymeRole.TERMINUS_DEFINITION,
                allowed_enzyme_ids=terminus_ids,
            )
        )
    return LocalNeighborhoodRequest(
        payload=FinalPayloadReference(
            payload=ExactPayload(sequence="GACA"),
            basal_boundary=Boundary(offset=0),
            foldback_boundary=Boundary(offset=4),
        ),
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
        preferences=ConstructionPreferences(),
        enzyme_provisioning=EnzymeProvisioningPolicy(
            catalog=catalog,
            allowed_enzyme_ids=tuple(enzyme.enzyme_id for enzyme in enzymes),
            forbidden_enzyme_ids=(),
            reserved_enzyme_ids=(),
            max_operations=4,
            role_restrictions=tuple(roles),
        ),
        relaxation=relaxation or RelaxationPolicy(mode=RelaxationMode.EXACT_ONLY, max_radius=0),
        enumeration=EnumerationPolicy(
            max_search_nodes=max_search_nodes,
            max_realizations=max_realizations,
        ),
    )


def test_exact_foldback_discovery_preserves_literal_pairing_and_reversible_groups() -> None:
    result = discover_foldback_neighborhood(_request(_nickase(), _terminus_enzyme()))

    assert result.neighborhood.status is SearchCompletionStatus.COMPLETE
    assert result.neighborhood.shells[0].radius == 0
    assert result.neighborhood.claim_boundary.physical_construction == "not_recorded"
    assert result.neighborhood.claim_boundary.biological_activity == "not_recorded"
    assert result.neighborhood.claim_boundary.method == "not_resolved"
    assert {item.program_kind for item in result.realizations} == {
        FoldbackCleavageProgramKind.SINGLE_CLEAVAGE,
        FoldbackCleavageProgramKind.SEQUENTIAL_TERMINUS_PLUS_NICK,
    }
    assert len(result.neighborhood.achieved_geometry_groups) == 1
    assert {item.projection_schema for item in result.neighborhood.projection_inventory} == {
        "hop.foldback-nucleotide-exemplar/v1",
        "hop.foldback-geometry-count-table/v1",
        "hop.foldback-feasibility-landscape/v1",
        "hop.foldback-relaxation-frontier/v1",
    }
    assert all(item.status == "not_generated" for item in result.neighborhood.projection_inventory)
    group = result.neighborhood.achieved_geometry_groups[0]
    assert group.multiplicity == len(result.realizations)
    assert group.realization_ids == tuple(
        item.local_realization.local_realization_id for item in result.realizations
    )
    assert len(set(group.realization_ids)) == len(result.realizations)

    for realization in result.realizations:
        assert realization.foldback_arm_sequence == "TGT"
        assert [(pair.left_base, pair.right_base) for pair in realization.annealing_pairs] == [
            ("A", "T"),
            ("C", "G"),
            ("A", "T"),
        ]
        assert realization.ligation_bond.upstream_strand_id == "top-0-4"
        assert realization.ligation_bond.downstream_strand_id == "bottom-0-13"
        assert realization.retained_sequence == "GACAACAAAATGTTGTC"
        assert (
            realization.local_realization.achieved_geometry
            == _request(_nickase(), _terminus_enzyme()).target
        )


def test_foldback_relaxation_is_exact_first_and_stops_at_complete_first_shell() -> None:
    relaxation = RelaxationPolicy(
        mode=RelaxationMode.FIRST_FEASIBLE_SHELL,
        max_radius=1,
        coordinates=(
            RelaxationCoordinate(
                name="annealing_arm_length_bp",
                minimum=3,
                maximum=4,
            ),
        ),
    )
    result = discover_foldback_neighborhood(
        _request(_nickase(motif="GACATTT"), relaxation=relaxation)
    )

    assert result.neighborhood.status is SearchCompletionStatus.COMPLETE
    assert [(shell.radius, len(shell.realization_ids)) for shell in result.neighborhood.shells] == [
        (0, 0),
        (1, 1),
    ]
    realization = result.realizations[0]
    assert realization.local_realization.achieved_geometry == FoldbackTarget(
        junction_offset_nt=0,
        loop_length_nt=3,
        annealing_arm_length_bp=4,
    )
    assert realization.relaxation_radius == 1
    assert realization.changed_coordinates == ("annealing_arm_length_bp",)


def test_foldback_search_is_truthfully_truncated_when_a_bound_fires() -> None:
    result = discover_foldback_neighborhood(
        _request(
            _nickase(),
            _terminus_enzyme(),
            max_search_nodes=1,
            max_realizations=100,
        )
    )

    assert result.neighborhood.status is SearchCompletionStatus.TRUNCATED
    assert result.neighborhood.truncation_reasons == ("max_search_nodes",)
    assert len(result.realizations) == 1
    assert result.neighborhood.shells[-1].complete is False
    assert all(shell.candidate_count > 0 for shell in result.neighborhood.shells)
    assert all(
        shell.candidate_count == len(shell.realization_ids) + shell.rejected_count
        and sum(reason.count for reason in shell.failure_reasons) == shell.rejected_count
        for shell in result.neighborhood.shells
    )


def test_foldback_verification_rejects_self_consistent_completion_promotion() -> None:
    raw = discover_foldback_neighborhood(
        _request(
            _nickase(),
            _terminus_enzyme(),
            max_search_nodes=1,
            max_realizations=100,
        )
    )
    request = raw.neighborhood.request.model_copy(
        update={
            "enumeration": raw.neighborhood.request.enumeration.model_copy(
                update={"max_search_nodes": 100}
            )
        }
    )
    execution = raw.neighborhood.execution.model_copy(update={"enumeration": request.enumeration})
    shell = raw.neighborhood.shells[0].model_copy(update={"complete": True})
    neighborhood = NeighborhoodDiscoveryResult.model_validate(
        {
            **raw.neighborhood.model_dump(mode="python"),
            "status": SearchCompletionStatus.COMPLETE,
            "request": request,
            "problem_id": problem_id(request),
            "execution": execution,
            "execution_id": execution.execution_id,
            "shells": (shell,),
            "payload_compatibility": PayloadCompatibilityAccounting(
                status=PayloadCompatibilityStatus.COMPLETE,
                total_assignments=1,
                compatible_assignments=1,
                excluded_assignments=0,
                exhaustive=True,
            ),
            "truncation_reasons": (),
        }
    )
    promoted = FoldbackNeighborhoodDiscoveryResult(
        neighborhood=neighborhood,
        realizations=raw.realizations,
    )

    with pytest.raises(ConstructionVerificationError, match="deterministic discovery replay"):
        verify_foldback_neighborhood_result(promoted)
    with pytest.raises(ConstructionVerificationError, match="deterministic discovery replay"):
        VerifiedFoldbackNeighborhoodResult(result=promoted)


def test_exact_foldback_domain_is_complete_when_a_bound_equals_exhaustive_count() -> None:
    enzymes = (_nickase(), _terminus_enzyme())
    exhaustive = discover_foldback_neighborhood(
        _request(*enzymes, max_search_nodes=10_000, max_realizations=10_000)
    )
    examined = sum(shell.candidate_count for shell in exhaustive.neighborhood.shells)
    realized = len(exhaustive.realizations)

    node_bounded = discover_foldback_neighborhood(
        _request(*enzymes, max_search_nodes=examined, max_realizations=10_000)
    )
    realization_bounded = discover_foldback_neighborhood(
        _request(*enzymes, max_search_nodes=10_000, max_realizations=realized)
    )

    assert node_bounded.neighborhood.status is SearchCompletionStatus.COMPLETE
    assert realization_bounded.neighborhood.status is SearchCompletionStatus.COMPLETE


def test_foldback_result_enforces_its_own_program_operation_limit() -> None:
    result = discover_foldback_neighborhood(_request(_nickase(), _terminus_enzyme()))
    request = result.neighborhood.request.model_copy(
        update={
            "enzyme_provisioning": result.neighborhood.request.enzyme_provisioning.model_copy(
                update={"max_operations": 1}
            )
        }
    )
    execution = result.neighborhood.execution.model_copy(update={"max_operations": 1})
    neighborhood = NeighborhoodDiscoveryResult.model_validate(
        {
            **result.neighborhood.model_dump(mode="python"),
            "request": request,
            "execution": execution,
            "execution_id": execution.execution_id,
        }
    )

    with pytest.raises(ValidationError, match="operation limit"):
        FoldbackNeighborhoodDiscoveryResult(
            neighborhood=neighborhood,
            realizations=result.realizations,
        )


def test_foldback_shell_accounting_partitions_rejections_and_policy_suppression() -> None:
    request = _request(
        _nickase(
            motif="ACA",
            orientation_semantics=RecognitionOrientationSemantics.DECLARED_ONLY,
        ),
        max_search_nodes=200,
        max_realizations=200,
    )
    request_data = request.model_dump(mode="python")
    request_data["payload"]["payload"] = DegeneratePayload(sequence="GACW")
    request_data["hard_constraints"]["require_all_members_compatible"] = True

    result = discover_foldback_neighborhood(LocalNeighborhoodRequest.model_validate(request_data))

    assert result.neighborhood.status is SearchCompletionStatus.INFEASIBLE
    assert all(not shell.realization_ids for shell in result.neighborhood.shells)
    assert all(shell.complete for shell in result.neighborhood.shells)
    assert all(
        shell.candidate_count == shell.rejected_count
        and sum(reason.count for reason in shell.failure_reasons) == shell.rejected_count
        for shell in result.neighborhood.shells
    )
    assert any(
        reason.code == "all-members-compatibility-required"
        for shell in result.neighborhood.shells
        for reason in shell.failure_reasons
    )


def test_foldback_payload_recognition_conflict_is_accounted_without_repair() -> None:
    result = discover_foldback_neighborhood(_request(_nickase(motif="GACA", cut_offset=4)))

    assert result.neighborhood.status is SearchCompletionStatus.INFEASIBLE
    assert result.neighborhood.realizations == ()
    assert result.neighborhood.payload_compatibility.compatible_assignments == 0
    assert result.neighborhood.payload_compatibility.excluded_assignments == 1
    assert result.neighborhood.payload_compatibility.conflict_counts[0].code == (
        "payload-recognition-conflict"
    )
    assert result.neighborhood.request.payload.payload.sequence == "GACA"


def test_foldback_result_rejects_lossy_family_detail_membership() -> None:
    result = discover_foldback_neighborhood(_request(_nickase(), _terminus_enzyme()))
    data = result.model_dump(mode="python")
    data["realizations"] = data["realizations"][:-1]

    with pytest.raises(ValidationError, match="ordered relation"):
        type(result).model_validate(data)


def test_foldback_result_rejects_reordered_family_detail_membership() -> None:
    result = discover_foldback_neighborhood(_request(_nickase(), _terminus_enzyme()))
    data = result.model_dump(mode="python")
    data["realizations"] = tuple(reversed(data["realizations"]))

    with pytest.raises(ValidationError, match="ordered"):
        type(result).model_validate(data)


def test_foldback_family_identity_binds_all_detailed_evidence() -> None:
    result = discover_foldback_neighborhood(_request(_nickase(), _terminus_enzyme()))
    first = result.realizations[0]
    changed = first.model_copy(update={"loop_sequence": "CCC"})
    mutated = result.model_copy(update={"realizations": (changed, *result.realizations[1:])})

    assert mutated.neighborhood.result_id == result.neighborhood.result_id
    assert mutated.result_id != result.result_id


@pytest.mark.parametrize(
    "corruption",
    ("candidate", "rejected", "failure", "examined", "global"),
)
def test_foldback_wrapper_revalidates_resealed_shell_accounting(corruption: str) -> None:
    result = discover_foldback_neighborhood(
        _request(_nickase(), _terminus_enzyme(reference_cut_offset=2))
    )
    shell = result.neighborhood.shells[0]
    assert shell.rejected_count > 0
    if corruption == "candidate":
        corrupted_shell = shell.model_copy(update={"candidate_count": shell.candidate_count + 1})
    elif corruption == "rejected":
        corrupted_shell = shell.model_copy(update={"rejected_count": shell.rejected_count + 1})
    elif corruption == "failure":
        corrupted_shell = shell.model_copy(update={"failure_reasons": ()})
    elif corruption == "examined":
        corrupted_shell = shell.model_copy(update={"examined": False})
    else:
        corrupted_shell = shell
    corrupted_neighborhood = result.neighborhood.model_copy(
        update={
            "shells": (corrupted_shell,),
            "rejected_count": (
                result.neighborhood.rejected_count + 1
                if corruption == "global"
                else result.neighborhood.rejected_count
            ),
        }
    )

    with pytest.raises(ValidationError):
        type(result).model_validate(
            {
                "neighborhood": corrupted_neighborhood,
                "realizations": result.realizations,
            }
        )


def test_foldback_bounds_at_a_shell_boundary_do_not_emit_an_unentered_shell() -> None:
    exact = discover_foldback_neighborhood(_request(_nickase()))
    shell = exact.neighborhood.shells[0]
    relaxation = RelaxationPolicy(
        mode=RelaxationMode.THROUGH_RADIUS,
        max_radius=1,
        coordinates=(RelaxationCoordinate(name="junction_offset_nt", minimum=0, maximum=1),),
    )

    for limits in (
        {"max_search_nodes": shell.candidate_count, "max_realizations": 100},
        {"max_search_nodes": 100, "max_realizations": len(shell.realization_ids)},
    ):
        result = discover_foldback_neighborhood(
            _request(_nickase(), relaxation=relaxation, **limits)
        )

        assert result.neighborhood.status is SearchCompletionStatus.TRUNCATED
        assert tuple(item.radius for item in result.neighborhood.shells) == (0,)
        assert result.neighborhood.shells[0].complete is True


def test_foldback_wrapper_rejects_partial_final_shell_resealed_as_complete() -> None:
    result = discover_foldback_neighborhood(
        _request(
            _nickase(),
            _terminus_enzyme(),
            max_search_nodes=1,
            max_realizations=100,
        )
    )
    shell = result.neighborhood.shells[-1]
    assert shell.complete is False
    corrupted_shell = shell.model_copy(update={"complete": True})
    corrupted_neighborhood = result.neighborhood.model_copy(
        update={"shells": (*result.neighborhood.shells[:-1], corrupted_shell)}
    )

    with pytest.raises(ValidationError, match="unentered later shell"):
        type(result).model_validate(
            {
                "neighborhood": corrupted_neighborhood,
                "realizations": result.realizations,
            }
        )


def test_staggered_terminus_is_rejected_when_the_route_cannot_represent_its_intermediate() -> None:
    result = discover_foldback_neighborhood(
        _request(_nickase(), _terminus_enzyme(reference_cut_offset=2))
    )

    assert {item.program_kind for item in result.realizations} == {
        FoldbackCleavageProgramKind.SINGLE_CLEAVAGE
    }
    assert "unsupported-staggered-terminus" in {
        reason.code for reason in result.neighborhood.failure_reasons
    }


def test_single_cleavage_rejects_a_site_extending_beyond_the_physical_source_end() -> None:
    result = discover_foldback_neighborhood(_request(_nickase(motif="ACATTTTGTG")))

    assert result.neighborhood.status is SearchCompletionStatus.INFEASIBLE
    assert result.realizations == ()
    assert {reason.code for reason in result.neighborhood.failure_reasons} == {
        "single-cleavage-site-exceeds-source-terminus"
    }


def test_foldback_target_coordinates_drive_exact_sites_fragments_and_pairing() -> None:
    target = FoldbackTarget(
        junction_offset_nt=1,
        loop_length_nt=4,
        annealing_arm_length_bp=2,
    )
    result = discover_foldback_neighborhood(_request(_nickase(motif="CATTTT"), target=target))
    realization = result.realizations[0]
    binding = realization.enzyme_bindings[0]

    assert realization.local_realization.achieved_geometry == target
    assert realization.foldback_nick.boundary.offset == 5
    assert realization.terminus.boundary.offset == 13
    assert (binding.recognition_span.start.offset, binding.recognition_span.end.offset) == (5, 11)
    assert binding.reference_cut.offset == 5
    assert realization.retained_sequence == "GACA" + "A" + "CA" + "AAAA" + "TG" + "TTGTC"
    assert {
        fragment.fragment_id: fragment.sequence
        for fragment in realization.molecular_fragments
        if fragment.fragment_id
        in {
            realization.ligation_bond.upstream_strand_id,
            realization.ligation_bond.downstream_strand_id,
        }
    } == {
        "top-0-5": "GACAA",
        "bottom-0-13": "CAAAAATGTTGTC",
    }
    assert [(pair.left_index, pair.right_index) for pair in realization.annealing_pairs] == [
        (0, 7),
        (1, 6),
    ]


def test_degenerate_payload_accounting_reports_the_exact_compatible_subset() -> None:
    request = _request(
        _nickase(
            motif="ACA",
            orientation_semantics=RecognitionOrientationSemantics.DECLARED_ONLY,
        ),
        max_search_nodes=200,
        max_realizations=200,
    )
    request_data = request.model_dump(mode="python")
    request_data["payload"]["payload"] = DegeneratePayload(sequence="GACW")
    result = discover_foldback_neighborhood(LocalNeighborhoodRequest.model_validate(request_data))

    assert result.neighborhood.payload_compatibility.total_assignments == 2
    assert result.neighborhood.payload_compatibility.compatible_assignments == 1
    assert result.neighborhood.payload_compatibility.excluded_assignments == 1
    assert {item.payload_sequence for item in result.realizations} == {"GACT"}


def test_all_member_compatibility_rejects_a_partially_compatible_payload_space() -> None:
    request = _request(
        _nickase(
            motif="ACA",
            orientation_semantics=RecognitionOrientationSemantics.DECLARED_ONLY,
        ),
        max_search_nodes=200,
        max_realizations=200,
    )
    request_data = request.model_dump(mode="python")
    request_data["payload"]["payload"] = DegeneratePayload(sequence="GACW")
    request_data["hard_constraints"]["require_all_members_compatible"] = True

    result = discover_foldback_neighborhood(LocalNeighborhoodRequest.model_validate(request_data))

    assert result.neighborhood.status is SearchCompletionStatus.INFEASIBLE
    assert result.realizations == ()
    assert result.neighborhood.payload_compatibility.compatible_assignments == 1
    assert result.neighborhood.payload_compatibility.excluded_assignments == 1
    assert "all-members-compatibility-required" in {
        reason.code for reason in result.neighborhood.failure_reasons
    }


def test_all_member_first_feasible_search_continues_past_a_partial_shell() -> None:
    relaxation = RelaxationPolicy(
        mode=RelaxationMode.FIRST_FEASIBLE_SHELL,
        max_radius=1,
        coordinates=(
            RelaxationCoordinate(
                name="junction_offset_nt",
                minimum=0,
                maximum=1,
            ),
        ),
    )
    request = _request(
        _nickase(
            motif="AAA",
            orientation_semantics=RecognitionOrientationSemantics.DECLARED_ONLY,
        ),
        relaxation=relaxation,
        max_search_nodes=1000,
        max_realizations=1000,
    )
    request_data = request.model_dump(mode="python")
    request_data["payload"]["payload"] = DegeneratePayload(sequence="GACW")
    request_data["hard_constraints"]["require_all_members_compatible"] = True

    result = discover_foldback_neighborhood(LocalNeighborhoodRequest.model_validate(request_data))

    assert result.neighborhood.status is SearchCompletionStatus.COMPLETE
    assert tuple(shell.radius for shell in result.neighborhood.shells) == (0, 1)
    assert result.neighborhood.payload_compatibility.compatible_assignments == 2
    assert {item.payload_sequence for item in result.realizations} == {"GACA", "GACT"}


def test_reverse_orientation_placement_derives_its_site_and_cut_coordinates() -> None:
    result = discover_foldback_neighborhood(
        _request(
            _nickase(),
            _terminus_enzyme(
                motif="AAAT",
                orientation_semantics=RecognitionOrientationSemantics.BOTH_ORIENTATIONS,
            ),
        )
    )
    sequential = tuple(
        item
        for item in result.realizations
        if item.program_kind is FoldbackCleavageProgramKind.SEQUENTIAL_TERMINUS_PLUS_NICK
    )

    assert sequential == ()
    assert "terminus-cleavage-at-source-end" in {
        reason.code for reason in result.neighborhood.failure_reasons
    }
