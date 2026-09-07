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
    FinalPayloadReference,
    FoldbackGeometryDomain,
    FoldbackTarget,
    LocalNeighborhoodFamily,
    LocalNeighborhoodRequest,
    NeighborhoodDiscoveryResult,
    NeighborhoodSearchPlan,
    PayloadCompatibilityAccounting,
    PayloadCompatibilityStatus,
    RouteFamily,
    SearchCompletionStatus,
    SearchDisposition,
    SearchFeasibilityStatus,
    SearchTerminationReason,
    SourceOrientation,
    problem_id,
)
from hop_design.models.construction.foldback import (
    FoldbackCleavageProgramKind,
    FoldbackMaterialRequirement,
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
from hop_design.models.physical import Strand
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
    domain: FoldbackGeometryDomain | None = None,
    max_retained_overhead_nt: int | None = None,
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
    exact_target = target or FoldbackTarget(
        junction_offset_nt=0,
        loop_length_nt=3,
        annealing_arm_length_bp=3,
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
        geometry_domain=domain
        or FoldbackGeometryDomain(
            nick_strand=exact_target.nick_strand,
            junction_offsets_nt=(exact_target.junction_offset_nt,),
            loop_lengths_nt=(exact_target.loop_length_nt,),
            annealing_arm_lengths_bp=(exact_target.annealing_arm_length_bp,),
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
        search=NeighborhoodSearchPlan(
            max_retained_overhead_nt=max_retained_overhead_nt
            if max_retained_overhead_nt is not None
            else exact_target.loop_length_nt + 2 * exact_target.annealing_arm_length_bp,
            max_search_nodes=max_search_nodes,
            max_realizations=max_realizations,
        ),
    )


def test_foldback_target_rejects_ambiguous_or_out_of_arm_nick_coordinates() -> None:
    with pytest.raises(ValidationError, match="junction_offset_nt"):
        FoldbackTarget.model_validate(
            {
                "nick_offset_within_foldback_nt": 0,
                "loop_length_nt": 3,
                "annealing_arm_length_bp": 3,
            }
        )

    with pytest.raises(ValidationError, match="first annealing arm"):
        FoldbackTarget(
            junction_offset_nt=4,
            loop_length_nt=3,
            annealing_arm_length_bp=3,
        )


def test_exact_foldback_discovery_preserves_literal_pairing_and_reversible_groups() -> None:
    result = discover_foldback_neighborhood(_request(_nickase(), _terminus_enzyme()))

    assert result.neighborhood.disposition.completion is SearchCompletionStatus.COMPLETE
    assert result.neighborhood.overhead_levels[-1].retained_overhead_nt == 9
    assert result.neighborhood.claim_boundary.physical_construction == "not_recorded"
    assert result.neighborhood.claim_boundary.biological_activity == "not_recorded"
    assert result.neighborhood.claim_boundary.method == "not_resolved"
    assert {item.program_kind for item in result.realizations} == {
        FoldbackCleavageProgramKind.SINGLE_CLEAVAGE,
        FoldbackCleavageProgramKind.SEQUENTIAL_TERMINUS_PLUS_NICK,
    }
    assert len(result.neighborhood.achieved_geometry_groups) == 2
    assert {item.projection_schema for item in result.neighborhood.projection_inventory} == {
        "hop.foldback-nucleotide-exemplar/v1",
        "hop.foldback-geometry-count-table/v1",
        "hop.foldback-feasibility-landscape/v3",
        "hop.foldback-overhead-frontier/v1",
    }
    assert all(item.status == "not_generated" for item in result.neighborhood.projection_inventory)
    assert sum(group.multiplicity for group in result.neighborhood.achieved_geometry_groups) == len(
        result.realizations
    )
    assert {
        realization.local_realization.achieved_geometry.nick_strand
        for realization in result.realizations
    } == {Strand.TOP, Strand.BOTTOM}

    for realization in result.realizations:
        assert realization.retained_overhead.neighborhood == "foldback"
        assert realization.retained_overhead.reference_state_id == "foldback-local-product"
        assert realization.retained_overhead.retained_overhead_nt == 9
        assert tuple(
            (position.position, position.base)
            for position in realization.retained_overhead.positions
        ) == tuple(enumerate(realization.retained_sequence[4:13], start=4))
        assert realization.foldback_arm_sequence == "TGT"
        assert [(pair.left_base, pair.right_base) for pair in realization.annealing_pairs] == [
            ("A", "T"),
            ("C", "G"),
            ("A", "T"),
        ]
        assert realization.retained_sequence == "GACAACAAAATGTTGTC"
    assert {
        (
            realization.ligation_bond.upstream_strand_id,
            realization.ligation_bond.downstream_strand_id,
        )
        for realization in result.realizations
    } == {
        ("top-0-4", "bottom-0-13"),
        ("bottom-9-13", "top-0-13"),
    }


def test_foldback_discovery_searches_both_physical_nick_strands_by_default() -> None:
    result = discover_foldback_neighborhood(_request(_nickase()))

    assert result.neighborhood.disposition.completion is SearchCompletionStatus.COMPLETE
    assert len(result.realizations) == 2
    assert {item.foldback_nick.strand.value for item in result.realizations} == {
        "top",
        "bottom",
    }
    assert {item.source_reference_sequence for item in result.realizations} == {
        "GACAACATTTTGT",
        "ACAAAATGTTGTC",
    }
    assert {item.retained_sequence for item in result.realizations} == {"GACAACAAAATGTTGTC"}
    by_strand = {item.foldback_nick.strand: item for item in result.realizations}
    assert by_strand[Strand.TOP].payload_source_map.segments[0].orientation is (
        SourceOrientation.FORWARD
    )
    assert by_strand[Strand.BOTTOM].payload_source_map.segments[0].orientation is (
        SourceOrientation.REVERSE_COMPLEMENT
    )
    assert by_strand[Strand.TOP].material_requirements == (
        FoldbackMaterialRequirement.SOURCE_BOTTOM_5PRIME_PHOSPHATE,
    )
    assert by_strand[Strand.BOTTOM].material_requirements == (
        FoldbackMaterialRequirement.SOURCE_TOP_5PRIME_PHOSPHATE,
    )
    assert by_strand[Strand.BOTTOM].released_state.route.value == ("top_active_after_bottom_nick")


def test_any_strand_discovery_is_the_union_of_exact_strand_searches() -> None:
    target = FoldbackTarget(
        junction_offset_nt=0,
        loop_length_nt=3,
        annealing_arm_length_bp=3,
    )
    any_strand = discover_foldback_neighborhood(_request(_nickase(), target=target))
    exact_results = tuple(
        discover_foldback_neighborhood(
            _request(
                _nickase(),
                target=target.model_copy(update={"nick_strand": strand}),
            )
        )
        for strand in (Strand.TOP, Strand.BOTTOM)
    )

    any_ids = {item.foldback_realization_id for item in any_strand.realizations}
    exact_ids = {
        item.foldback_realization_id for result in exact_results for item in result.realizations
    }
    assert any_ids == exact_ids
    assert len(any_ids) == 2
    assert {
        item.foldback_nick.strand for result in exact_results for item in result.realizations
    } == {Strand.TOP, Strand.BOTTOM}


@pytest.mark.parametrize("nick_strand", (Strand.TOP, Strand.BOTTOM))
def test_foldback_discovery_honors_an_exact_physical_nick_strand(
    nick_strand: Strand,
) -> None:
    target = FoldbackTarget(
        nick_strand=nick_strand,
        junction_offset_nt=0,
        loop_length_nt=3,
        annealing_arm_length_bp=3,
    )
    result = discover_foldback_neighborhood(_request(_nickase(), target=target))

    assert {item.foldback_nick.strand for item in result.realizations} == {nick_strand}


def test_declared_only_nickase_does_not_fabricate_a_bottom_strand_route() -> None:
    target = FoldbackTarget(
        nick_strand=Strand.BOTTOM,
        junction_offset_nt=0,
        loop_length_nt=3,
        annealing_arm_length_bp=3,
    )
    result = discover_foldback_neighborhood(
        _request(
            _nickase(
                orientation_semantics=RecognitionOrientationSemantics.DECLARED_ONLY,
            ),
            target=target,
        )
    )

    assert result.neighborhood.disposition.feasibility is SearchFeasibilityStatus.INFEASIBLE
    assert result.realizations == ()


def test_bottom_strand_sequential_route_replays_its_mirrored_source_lineage() -> None:
    result = discover_foldback_neighborhood(
        _request(
            _nickase(),
            _terminus_enzyme(
                motif="AAGC",
                orientation_semantics=RecognitionOrientationSemantics.BOTH_ORIENTATIONS,
            ),
        )
    )
    realization = next(
        item
        for item in result.realizations
        if item.foldback_nick.strand is Strand.BOTTOM
        and item.program_kind is FoldbackCleavageProgramKind.SEQUENTIAL_TERMINUS_PLUS_NICK
    )

    assert realization.source_reference_sequence == "GCTTACAAAATGTTGTC"
    assert realization.terminus.strand is Strand.TOP
    assert realization.terminus.boundary == Boundary(offset=4)
    assert realization.payload_source_map.segments[0].orientation is (
        SourceOrientation.REVERSE_COMPLEMENT
    )
    assert realization.retained_sequence == "GACAACAAAATGTTGTC"
    assert realization.released_state.route.value == "top_active_after_bottom_nick"


def test_foldback_search_resolves_empty_lower_overheads_before_a_larger_hit() -> None:
    result = discover_foldback_neighborhood(
        _request(
            _nickase(motif="GACATTT"),
            domain=FoldbackGeometryDomain(
                junction_offsets_nt=(0,),
                loop_lengths_nt=(3,),
                annealing_arm_lengths_bp=(3, 4),
            ),
            max_retained_overhead_nt=11,
        )
    )

    assert result.neighborhood.disposition.completion is SearchCompletionStatus.COMPLETE
    assert result.neighborhood.overhead_levels[9].realization_ids == ()
    assert len(result.neighborhood.overhead_levels[11].realization_ids) == 2
    realization = result.realizations[0]
    assert realization.local_realization.achieved_geometry == FoldbackTarget(
        nick_strand=Strand.TOP,
        junction_offset_nt=0,
        loop_length_nt=3,
        annealing_arm_length_bp=4,
    )
    assert realization.retained_overhead.retained_overhead_nt == 11


def test_foldback_search_is_truthfully_truncated_when_a_bound_fires() -> None:
    result = discover_foldback_neighborhood(
        _request(
            _nickase(),
            _terminus_enzyme(),
            max_search_nodes=1,
            max_realizations=100,
        )
    )

    assert result.neighborhood.disposition.completion is SearchCompletionStatus.TRUNCATED
    assert result.neighborhood.disposition.feasibility is SearchFeasibilityStatus.FEASIBLE
    assert (
        result.neighborhood.disposition.termination_reason is SearchTerminationReason.EVALUATION_CAP
    )
    assert len(result.realizations) == 1
    assert result.neighborhood.overhead_levels[-1].complete is False
    assert result.neighborhood.overhead_levels[-1].candidate_count > 0
    assert all(
        level.candidate_count == len(level.realization_ids) + level.rejected_count
        and sum(reason.count for reason in level.failure_reasons) == level.rejected_count
        for level in result.neighborhood.overhead_levels
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
            "search": raw.neighborhood.request.search.model_copy(update={"max_search_nodes": 100})
        }
    )
    execution = raw.neighborhood.execution.model_copy(update={"search": request.search})
    levels = (
        *raw.neighborhood.overhead_levels[:-1],
        raw.neighborhood.overhead_levels[-1].model_copy(update={"complete": True}),
    )
    neighborhood = NeighborhoodDiscoveryResult.model_validate(
        {
            **raw.neighborhood.model_dump(mode="python"),
            "disposition": SearchDisposition(
                completion=SearchCompletionStatus.COMPLETE,
                feasibility=SearchFeasibilityStatus.FEASIBLE,
                termination_reason=SearchTerminationReason.EXHAUSTED_DOMAIN,
            ),
            "request": request,
            "problem_id": problem_id(request),
            "execution": execution,
            "execution_id": execution.execution_id,
            "overhead_levels": levels,
            "payload_compatibility": PayloadCompatibilityAccounting(
                status=PayloadCompatibilityStatus.COMPLETE,
                total_assignments=1,
                compatible_assignments=1,
                excluded_assignments=0,
                exhaustive=True,
            ),
        }
    )
    promoted = FoldbackNeighborhoodDiscoveryResult.create(
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
    examined = sum(level.candidate_count for level in exhaustive.neighborhood.overhead_levels)
    realized = len(exhaustive.realizations)

    node_bounded = discover_foldback_neighborhood(
        _request(*enzymes, max_search_nodes=examined, max_realizations=10_000)
    )
    realization_bounded = discover_foldback_neighborhood(
        _request(*enzymes, max_search_nodes=10_000, max_realizations=realized)
    )

    assert node_bounded.neighborhood.disposition.completion is SearchCompletionStatus.COMPLETE
    assert (
        realization_bounded.neighborhood.disposition.completion is SearchCompletionStatus.COMPLETE
    )


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
        FoldbackNeighborhoodDiscoveryResult.create(
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

    assert result.neighborhood.disposition.feasibility is SearchFeasibilityStatus.INFEASIBLE
    assert all(not level.realization_ids for level in result.neighborhood.overhead_levels)
    assert all(level.complete for level in result.neighborhood.overhead_levels)
    assert all(
        level.candidate_count == level.rejected_count
        and sum(reason.count for reason in level.failure_reasons) == level.rejected_count
        for level in result.neighborhood.overhead_levels
    )
    assert any(
        reason.code == "all-members-compatibility-required"
        for level in result.neighborhood.overhead_levels
        for reason in level.failure_reasons
    )


def test_foldback_payload_recognition_conflict_is_accounted_without_repair() -> None:
    result = discover_foldback_neighborhood(_request(_nickase(motif="GACA", cut_offset=4)))

    assert result.neighborhood.disposition.feasibility is SearchFeasibilityStatus.INFEASIBLE
    assert result.neighborhood.realizations == ()
    assert result.neighborhood.payload_compatibility.compatible_assignments == 0
    assert result.neighborhood.payload_compatibility.excluded_assignments == 1
    assert result.neighborhood.payload_compatibility.conflict_counts[0].code == (
        "payload-recognition-conflict"
    )
    assert result.neighborhood.request.payload.payload.sequence == "GACA"


def test_foldback_discovery_places_the_nick_inside_the_retained_tract() -> None:
    result = discover_foldback_neighborhood(
        _request(
            _nickase(motif="CCTNAGC", cut_offset=2),
            target=FoldbackTarget(
                junction_offset_nt=3,
                loop_length_nt=4,
                annealing_arm_length_bp=7,
            ),
            max_search_nodes=100_000,
            max_realizations=100_000,
        )
    )

    assert result.neighborhood.disposition.completion is SearchCompletionStatus.COMPLETE
    assert result.neighborhood.request.payload.payload.sequence == "GACA"
    assert any(
        realization.retained_sequence == "GACATCCTCAGCCCGCTGAGGATGTC"
        and realization.source_reference_sequence == "GACATCCTCAGCGGGCTGA"
        and realization.enzyme_bindings[0].recognition_span.start.offset == 5
        and realization.enzyme_bindings[0].reference_cut == Boundary(offset=7)
        for realization in result.realizations
    )


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
    assert result.schema_id == "hop.foldback-neighborhood-result/v4"
    assert result.model_dump(mode="json", by_alias=True)["schema"] == result.schema_id
    assert result.model_dump(mode="json")["result_id"] == result.result_id
    first = result.realizations[0]
    changed = first.model_copy(update={"loop_sequence": "CCC"})
    mutated = result.model_copy(update={"realizations": (changed, *result.realizations[1:])})

    assert mutated.neighborhood.result_id == result.neighborhood.result_id
    with pytest.raises(ValidationError, match="identity must seal every molecular fact"):
        FoldbackNeighborhoodDiscoveryResult.model_validate(mutated.model_dump(mode="python"))

    forged = result.model_dump(mode="python")
    forged["result_id"] = "hop:foldback-neighborhood-result/" + "0" * 64 + "@1"
    with pytest.raises(ValidationError, match="result_id"):
        FoldbackNeighborhoodDiscoveryResult.model_validate(forged)


@pytest.mark.parametrize(
    "corruption",
    ("candidate", "rejected", "failure", "examined", "global"),
)
def test_foldback_wrapper_revalidates_resealed_overhead_accounting(corruption: str) -> None:
    result = discover_foldback_neighborhood(
        _request(_nickase(), _terminus_enzyme(reference_cut_offset=2))
    )
    level_index = next(
        index
        for index, item in enumerate(result.neighborhood.overhead_levels)
        if item.rejected_count
    )
    level = result.neighborhood.overhead_levels[level_index]
    assert level.rejected_count > 0
    if corruption == "candidate":
        corrupted_level = level.model_copy(update={"candidate_count": level.candidate_count + 1})
    elif corruption == "rejected":
        corrupted_level = level.model_copy(update={"rejected_count": level.rejected_count + 1})
    elif corruption == "failure":
        corrupted_level = level.model_copy(update={"failure_reasons": ()})
    elif corruption == "examined":
        corrupted_level = level.model_copy(update={"examined": False})
    else:
        corrupted_level = level
    corrupted_neighborhood = result.neighborhood.model_copy(
        update={
            "overhead_levels": (
                *result.neighborhood.overhead_levels[:level_index],
                corrupted_level,
                *result.neighborhood.overhead_levels[level_index + 1 :],
            ),
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


def test_foldback_bounds_preserve_the_entered_overhead_level() -> None:
    exact = discover_foldback_neighborhood(_request(_nickase()))
    active_level = exact.neighborhood.overhead_levels[-1]
    domain = FoldbackGeometryDomain(
        junction_offsets_nt=(0,),
        loop_lengths_nt=(3,),
        annealing_arm_lengths_bp=(3, 4),
    )

    node_bounded = discover_foldback_neighborhood(
        _request(
            _nickase(),
            domain=domain,
            max_retained_overhead_nt=11,
            max_search_nodes=active_level.candidate_count,
            max_realizations=100,
        )
    )
    realization_bounded = discover_foldback_neighborhood(
        _request(
            _nickase(),
            domain=domain,
            max_retained_overhead_nt=11,
            max_search_nodes=100,
            max_realizations=len(active_level.realization_ids),
        )
    )

    assert node_bounded.neighborhood.disposition.completion is SearchCompletionStatus.TRUNCATED
    assert tuple(
        item.retained_overhead_nt for item in node_bounded.neighborhood.overhead_levels
    ) == tuple(range(12))
    assert node_bounded.neighborhood.overhead_levels[-1].complete is False
    assert (
        realization_bounded.neighborhood.disposition.completion is SearchCompletionStatus.TRUNCATED
    )
    assert realization_bounded.neighborhood.overhead_levels[-1].complete is False


def test_foldback_wrapper_rejects_partial_final_level_resealed_as_complete() -> None:
    result = discover_foldback_neighborhood(
        _request(
            _nickase(),
            _terminus_enzyme(),
            max_search_nodes=1,
            max_realizations=100,
        )
    )
    level = result.neighborhood.overhead_levels[-1]
    assert level.complete is False
    corrupted_level = level.model_copy(update={"complete": True})
    corrupted_neighborhood = result.neighborhood.model_copy(
        update={
            "overhead_levels": (
                *result.neighborhood.overhead_levels[:-1],
                corrupted_level,
            )
        }
    )

    with pytest.raises(ValidationError, match="Truncated coverage"):
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

    assert result.neighborhood.disposition.feasibility is SearchFeasibilityStatus.INFEASIBLE
    assert result.realizations == ()
    assert {reason.code for reason in result.neighborhood.failure_reasons} == {
        "single-cleavage-site-exceeds-source-terminus"
    }


def test_foldback_target_coordinates_drive_exact_sites_fragments_and_pairing() -> None:
    target = FoldbackTarget(
        nick_strand=Strand.TOP,
        junction_offset_nt=1,
        loop_length_nt=4,
        annealing_arm_length_bp=3,
    )
    result = discover_foldback_neighborhood(_request(_nickase(motif="ATTTTT"), target=target))
    realization = result.realizations[0]
    binding = realization.enzyme_bindings[0]

    assert realization.local_realization.achieved_geometry == target
    assert realization.foldback_nick.boundary.offset == 5
    assert realization.terminus.boundary.offset == 13
    assert (binding.recognition_span.start.offset, binding.recognition_span.end.offset) == (5, 11)
    assert binding.reference_cut.offset == 5
    assert realization.retained_sequence == "GACA" + "AAT" + "AAAA" + "ATT" + "TGTC"
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
        "bottom-0-13": "ATAAAAATTTGTC",
    }
    assert [(pair.left_index, pair.right_index) for pair in realization.annealing_pairs] == [
        (4, 8),
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

    assert result.neighborhood.disposition.feasibility is SearchFeasibilityStatus.INFEASIBLE
    assert result.realizations == ()
    assert result.neighborhood.payload_compatibility.compatible_assignments == 1
    assert result.neighborhood.payload_compatibility.excluded_assignments == 1
    assert "all-members-compatibility-required" in {
        reason.code for reason in result.neighborhood.failure_reasons
    }


def test_all_member_search_preserves_hits_across_the_complete_geometry_domain() -> None:
    request = _request(
        _nickase(
            motif="AAA",
            orientation_semantics=RecognitionOrientationSemantics.DECLARED_ONLY,
        ),
        domain=FoldbackGeometryDomain(
            junction_offsets_nt=(0, 1),
            loop_lengths_nt=(3,),
            annealing_arm_lengths_bp=(3,),
        ),
        max_search_nodes=1000,
        max_realizations=1000,
    )
    request_data = request.model_dump(mode="python")
    request_data["payload"]["payload"] = DegeneratePayload(sequence="GACW")
    request_data["hard_constraints"]["require_all_members_compatible"] = True

    result = discover_foldback_neighborhood(LocalNeighborhoodRequest.model_validate(request_data))

    assert result.neighborhood.disposition.completion is SearchCompletionStatus.COMPLETE
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
