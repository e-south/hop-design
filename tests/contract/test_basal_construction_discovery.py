"""
--------------------------------------------------------------------------------
HOP Design
tests/contract/test_basal_construction_discovery.py

Contract tests for endpoint-aware basal-neighborhood construction discovery.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import json
from dataclasses import replace

import pytest
from pydantic import ValidationError

from hop_design.design.construction.basal import discover_basal_neighborhood
from hop_design.design.construction.basal.reactions import _nicked_duplex
from hop_design.design.construction.basal.realization import (
    _failure_code,
    _realization,
)
from hop_design.design.construction.verification import (
    ConstructionVerificationError,
    VerifiedBasalNeighborhoodResult,
    verify_basal_neighborhood_result,
)
from hop_design.kernel.construction.basal import (
    BasalPlacementFailure,
    iter_basal_program_solutions,
    iter_basal_programs,
    resolve_basal_pairing_state,
)
from hop_design.models.construction import (
    BasalGeometryDomain,
    BasalPairAllowance,
    BasalPairClass,
    BasalPairConstraint,
    BasalTarget,
    ConstructionConstraints,
    ConstructionEndpoint,
    FinalPayloadReference,
    LocalNeighborhoodFamily,
    LocalNeighborhoodRequest,
    NeighborhoodDiscoveryResult,
    NeighborhoodSearchPlan,
    NickStrandSelection,
    RouteFamily,
    SearchCompletionStatus,
    SearchFeasibilityStatus,
    SearchTerminationReason,
    problem_id,
)
from hop_design.models.construction.basal import (
    BasalAdapterLigatedProduct,
    BasalMaterialAccounting,
    BasalMaterialRecord,
    BasalMaterialRole,
    BasalNeighborhoodDiscoveryResult,
    BasalPairRecord,
    BasalRealizationRecord,
)
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.diagnostics import CheckReport, Diagnostic, Severity
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
    VendorMetadata,
    characterized_enzyme_digest,
)
from hop_design.models.junction import Strand
from hop_design.models.payload import DegeneratePayload, ExactPayload
from hop_design.models.references import ExternalRef
from hop_design.models.sequence import reverse_complement_iupac


def _enzyme(
    enzyme_id: str,
    *,
    enzyme_class: EnzymeClass,
    pattern: str,
    reference_cut: int,
    complement_cut: int | None,
) -> CharacterizedEnzyme:
    return CharacterizedEnzyme(
        enzyme_id=enzyme_id,
        canonical_name=enzyme_id.rsplit("/", maxsplit=1)[-1],
        enzyme_class=enzyme_class,
        target_molecule=TargetMolecule.DNA,
        recognition_pattern=pattern,
        recognition_orientation_semantics=RecognitionOrientationSemantics.BOTH_ORIENTATIONS,
        recognition_length=len(pattern),
        substrate_requirement=SubstrateRequirement.DUPLEX_DNA,
        cut_offset_reference_strand=reference_cut,
        cut_offset_complement_strand=complement_cut,
        resulting_end_model=(
            ResultingEndModel.NICK
            if enzyme_class is EnzymeClass.NICKASE
            else ResultingEndModel.DUPLEX_BREAK
        ),
        characterization_source=ExternalRef(
            system="literature",
            kind="enzyme-characterization",
            id=f"source-{enzyme_id}",
        ),
    )


def _nickase(enzyme_id: str = "example:enzyme/basal-nick-a@1") -> CharacterizedEnzyme:
    return _enzyme(
        enzyme_id,
        enzyme_class=EnzymeClass.NICKASE,
        pattern="AAC",
        reference_cut=2,
        complement_cut=None,
    )


def _type_iis(
    enzyme_id: str = "example:enzyme/end-a@1",
    *,
    pattern: str = "GGTCTC",
) -> CharacterizedEnzyme:
    return _enzyme(
        enzyme_id,
        enzyme_class=EnzymeClass.DUPLEX_RESTRICTION,
        pattern=pattern,
        reference_cut=6,
        complement_cut=10,
    )


def _provisioning(
    *enzymes: CharacterizedEnzyme,
    max_operations: int = 3,
) -> EnzymeProvisioningPolicy:
    catalog = CharacterizedEnzymeCatalog(
        catalog_id="example:enzyme-catalog/basal-construction@1",
        enzymes=enzymes,
    )
    nick_ids = tuple(
        enzyme.enzyme_id for enzyme in enzymes if enzyme.enzyme_class is EnzymeClass.NICKASE
    )
    restrictions = []
    if nick_ids:
        restrictions.append(
            EnzymeRoleRestriction(
                role=EnzymeRole.BASAL_NICK,
                allowed_enzyme_ids=nick_ids,
            )
        )
    end_ids = tuple(
        enzyme.enzyme_id
        for enzyme in enzymes
        if enzyme.enzyme_class is EnzymeClass.DUPLEX_RESTRICTION
    )
    if end_ids:
        restrictions.append(
            EnzymeRoleRestriction(
                role=EnzymeRole.END_GENERATION,
                allowed_enzyme_ids=end_ids,
            )
        )
    return EnzymeProvisioningPolicy(
        catalog=catalog,
        allowed_enzyme_ids=tuple(enzyme.enzyme_id for enzyme in enzymes),
        forbidden_enzyme_ids=(),
        reserved_enzyme_ids=(),
        max_operations=max_operations,
        role_restrictions=tuple(restrictions),
    )


def _pairing_constraints(
    allowances: tuple[BasalPairAllowance, ...] = (
        BasalPairAllowance.MATCH,
        BasalPairAllowance.MATCH,
        BasalPairAllowance.ANY,
        BasalPairAllowance.MATCH,
    ),
) -> tuple[BasalPairConstraint, ...]:
    return tuple(
        BasalPairConstraint(
            position_from_ligation=position,
            allowed_class=allowance,
        )
        for position, allowance in enumerate(allowances)
    )


def _request(
    endpoint: ConstructionEndpoint,
    *,
    payload: str | ExactPayload | DegeneratePayload = "CCCC",
    pairing_constraints: tuple[BasalPairConstraint, ...] | None = None,
    max_nodes: int = 10000,
    max_realizations: int = 10000,
    domain: BasalGeometryDomain | None = None,
    extra_nickase: bool = False,
    max_operations: int = 3,
) -> LocalNeighborhoodRequest:
    if endpoint is not ConstructionEndpoint.HAIRPIN_PCR_DUPLEX:
        raise ValueError("Basal test requests must terminate at the PCR intermediate.")
    enzymes = [_nickase()]
    if extra_nickase:
        enzymes.append(_nickase("example:enzyme/basal-nick-b@1"))
    constraints = pairing_constraints or _pairing_constraints()
    return LocalNeighborhoodRequest(
        payload=FinalPayloadReference(
            payload=(ExactPayload(sequence=payload) if isinstance(payload, str) else payload),
            basal_boundary=Boundary(offset=0),
            foldback_boundary=Boundary(offset=4),
        ),
        family=LocalNeighborhoodFamily.BASAL,
        route_family=RouteFamily.LINEAR_SOURCE_V1,
        endpoint=endpoint,
        geometry_domain=domain
        or BasalGeometryDomain(
            nick_strand=Strand.TOP,
            nick_offsets_nt=(0,),
            pairing_constraints=constraints,
        ),
        hard_constraints=ConstructionConstraints(),
        enzyme_provisioning=_provisioning(*enzymes, max_operations=max_operations),
        search=NeighborhoodSearchPlan(
            max_retained_overhead_nt=2 * len(constraints),
            max_search_nodes=max_nodes,
            max_realizations=max_realizations,
        ),
    )


def _exact_target(request: LocalNeighborhoodRequest) -> BasalTarget:
    assert isinstance(request.geometry_domain, BasalGeometryDomain)
    return request.geometry_domain.exact_targets()[0]


def test_literal_pairing_is_variable_length_proximal_outward_and_projects_mwx() -> None:
    pairing_state = resolve_basal_pairing_state(
        source_sequence_5prime="AGCA",
        adapter_sequence_5prime="TATT",
        end_projection_positions=(2,),
    )

    assert [pair.position_from_ligation for pair in pairing_state.pairs] == [0, 1, 2, 3]
    assert [(pair.source_index, pair.adapter_index) for pair in pairing_state.pairs] == [
        (3, 0),
        (2, 1),
        (1, 2),
        (0, 3),
    ]
    assert pairing_state.pairing_pattern == "MXWM"
    assert pairing_state.pairs[2].participates_in_end_projection

    shorter = resolve_basal_pairing_state(
        source_sequence_5prime="ACG",
        adapter_sequence_5prime="CGT",
    )
    assert shorter.pairing_pattern == "MMM"


def test_literal_pair_record_rejects_a_pair_class_that_disagrees_with_its_bases() -> None:
    with pytest.raises(ValidationError, match="derive from the literal bases"):
        BasalPairRecord(
            position_from_ligation=0,
            source_index=0,
            adapter_index=0,
            source_base="A",
            adapter_base="T",
            pair_class=BasalPairClass.WOBBLE,
            compact_symbol="W",
        )


def test_authored_pairing_constraints_do_not_accept_realized_literal_bases() -> None:
    with pytest.raises(ValidationError):
        BasalPairConstraint.model_validate(
            {
                "position_from_ligation": 0,
                "allowed_class": "match",
                "source_base": "A",
                "adapter_base": "T",
            }
        )


def test_basal_local_discovery_accepts_only_the_pcr_intermediate() -> None:
    pcr = discover_basal_neighborhood(_request(ConstructionEndpoint.HAIRPIN_PCR_DUPLEX))
    invalid = pcr.discovery.request.model_dump(mode="python")
    invalid["endpoint"] = ConstructionEndpoint.SSDNA_HAIRPIN
    with pytest.raises(ValidationError, match="hairpin_pcr_duplex intermediate"):
        LocalNeighborhoodRequest.model_validate(invalid)

    projection = pcr.realizations[0].projection
    assert projection.pairing_state is not None
    assert projection.pairing_state.pairs[0].pair_class is BasalPairClass.MATCH
    assert projection.pairing_state.adapter_span == Span(
        start=Boundary(offset=0),
        end=Boundary(offset=4),
    )
    assert projection.pcr_reference_sequence is not None
    assert projection.pcr_complement_sequence is not None
    assert projection.pcr_complement_sequence == reverse_complement_iupac(
        projection.pcr_reference_sequence
    )
    assert "cohesive_ends" not in type(projection).model_fields
    assert "asymmetric_end_encoding" not in type(projection).model_fields
    assert "restriction_digest_product" not in type(pcr.realizations[0]).model_fields


def test_proximal_mismatch_is_rejected_but_distal_mismatch_is_copied_exactly() -> None:
    with pytest.raises(ValidationError, match="payload-proximal basal pair must be a match"):
        BasalTarget(
            nick_strand=Strand.TOP,
            nick_offset_nt=0,
            pairing_constraints=(
                BasalPairConstraint(
                    position_from_ligation=0,
                    allowed_class=BasalPairAllowance.MISMATCH,
                ),
            ),
            ligation_proximal_match_required=True,
        )
    distal = discover_basal_neighborhood(
        _request(
            ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
            pairing_constraints=_pairing_constraints(
                (
                    BasalPairAllowance.MATCH,
                    BasalPairAllowance.MATCH,
                    BasalPairAllowance.MISMATCH,
                    BasalPairAllowance.MATCH,
                )
            ),
        )
    )

    assert distal.discovery.disposition.completion is SearchCompletionStatus.COMPLETE
    assert distal.discovery.disposition.feasibility is SearchFeasibilityStatus.FEASIBLE
    pairing_state = distal.realizations[0].projection.pairing_state
    assert pairing_state is not None
    assert pairing_state.pairs[2].pair_class is BasalPairClass.MISMATCH
    assert distal.realizations[0].projection.pcr_reference_sequence is not None
    assert distal.realizations[0].projection.pcr_complement_sequence == reverse_complement_iupac(
        distal.realizations[0].projection.pcr_reference_sequence
    )


def test_realization_contains_exact_route_evidence_and_payload_conditioning() -> None:
    record = discover_basal_neighborhood(
        _request(ConstructionEndpoint.HAIRPIN_PCR_DUPLEX)
    ).realizations[0]

    assert record.payload_sequence == "CCCC"
    segment = record.payload_source_map.segments[0]
    assert (
        record.source_precursor_sequence[
            segment.source_span.start.offset : segment.source_span.end.offset
        ]
        == "CCCC"
    )
    assert tuple(binding.binding_id for binding in record.enzyme_bindings) == (
        *record.local_realization.enzyme_binding_ids,
    )
    assert {item.enzyme_id for item in record.enzyme_definitions} == {
        binding.enzyme_id for binding in record.enzyme_bindings
    }
    assert (
        tuple(stage.stage_id for program in record.reaction_programs for stage in program.stages)
        == record.local_realization.stage_ids
    )
    assert all(not assessment.report.has_errors for assessment in record.stage_assessments)
    assert record.nicked_duplex is not None
    assert record.adapter_annealed_complex is not None
    assert isinstance(record.adapter_ligated_product, BasalAdapterLigatedProduct)
    assert record.hairpin_pcr_duplex is not None
    assert record.retained_overhead.neighborhood == "basal"
    assert record.retained_overhead.retained_overhead_nt == 8
    assert tuple(position.position for position in record.retained_overhead.positions) == (
        0,
        1,
        2,
        3,
        8,
        9,
        10,
        11,
    )
    assert record.material_accounting.retained_nt > 0
    assert record.material_accounting.transient_nt == 0
    assert record.material_accounting.auxiliary_nt > 0


def test_basal_result_identity_seals_details_and_binds_exact_request_payload() -> None:
    result = discover_basal_neighborhood(_request(ConstructionEndpoint.HAIRPIN_PCR_DUPLEX))

    assert result.result_id.startswith("hop:basal-neighborhood-result/")
    assert BasalNeighborhoodDiscoveryResult.model_validate_json(result.model_dump_json()) == result
    changed = result.model_dump(mode="python")
    changed["result_id"] = "hop:basal-neighborhood-result/" + "0" * 64 + "@1"
    with pytest.raises(ValidationError, match="result_id"):
        BasalNeighborhoodDiscoveryResult.model_validate(changed)

    mixed = discover_basal_neighborhood(
        _request(
            ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
            payload=DegeneratePayload(sequence="CYCC"),
        )
    )
    exact_request = mixed.discovery.request.model_copy(
        update={
            "payload": mixed.discovery.request.payload.model_copy(
                update={"payload": ExactPayload(sequence="CTCC")}
            )
        }
    )
    changed_execution = mixed.discovery.execution.model_copy(
        update={"problem_id": problem_id(exact_request)}
    )
    changed_discovery = mixed.discovery.model_copy(
        update={
            "request": exact_request,
            "problem_id": problem_id(exact_request),
            "execution": changed_execution,
            "execution_id": changed_execution.execution_id,
        }
    )
    with pytest.raises(ValidationError, match="request payload"):
        BasalNeighborhoodDiscoveryResult.create(
            discovery=changed_discovery,
            realizations=mixed.realizations,
        )


def test_complete_basal_result_rejects_compatibility_count_drift() -> None:
    result = discover_basal_neighborhood(
        _request(
            ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
            payload=DegeneratePayload(sequence="CMAC"),
        )
    )
    drifted_accounting = result.discovery.payload_compatibility.model_copy(
        update={
            "compatible_assignments": 2,
            "excluded_assignments": 0,
            "conflict_counts": (),
        }
    )
    drifted_discovery = result.discovery.model_copy(
        update={"payload_compatibility": drifted_accounting}
    )

    with pytest.raises(ValidationError, match="compatible payload"):
        BasalNeighborhoodDiscoveryResult.create(
            discovery=drifted_discovery,
            realizations=result.realizations,
        )


def test_non_require_all_infeasible_result_requires_zero_compatible_payloads() -> None:
    request = _request(
        ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
        payload=DegeneratePayload(sequence="CMAC"),
    )
    require_all = request.model_copy(
        update={
            "hard_constraints": request.hard_constraints.model_copy(
                update={"require_all_members_compatible": True}
            )
        }
    )
    result = discover_basal_neighborhood(require_all)
    non_require_all_request = result.discovery.request.model_copy(
        update={
            "hard_constraints": result.discovery.request.hard_constraints.model_copy(
                update={"require_all_members_compatible": False}
            )
        }
    )
    changed_execution = result.discovery.execution.model_copy(
        update={"problem_id": problem_id(non_require_all_request)}
    )
    drifted_discovery = result.discovery.model_copy(
        update={
            "request": non_require_all_request,
            "problem_id": problem_id(non_require_all_request),
            "execution": changed_execution,
            "execution_id": changed_execution.execution_id,
        }
    )

    with pytest.raises(ValidationError, match="infeasible payload accounting"):
        BasalNeighborhoodDiscoveryResult.create(
            discovery=drifted_discovery,
            realizations=(),
        )


def test_basal_result_accepts_the_exact_one_operation_local_program_limit() -> None:
    result = discover_basal_neighborhood(
        _request(ConstructionEndpoint.HAIRPIN_PCR_DUPLEX, max_operations=3)
    )
    request = result.discovery.request.model_copy(
        update={
            "enzyme_provisioning": result.discovery.request.enzyme_provisioning.model_copy(
                update={"max_operations": 1}
            )
        }
    )
    execution = result.discovery.execution.model_copy(update={"max_operations": 1})
    discovery = NeighborhoodDiscoveryResult.model_validate(
        {
            **result.discovery.model_dump(mode="python"),
            "request": request,
            "execution": execution,
            "execution_id": execution.execution_id,
        }
    )

    rebuilt = BasalNeighborhoodDiscoveryResult.create(
        discovery=discovery,
        realizations=result.realizations,
    )
    assert all(len(record.reaction_programs) == 1 for record in rebuilt.realizations)


def test_require_all_infeasible_result_may_suppress_compatible_payload_records() -> None:
    request = _request(
        ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
        payload=DegeneratePayload(sequence="CMAC"),
    )
    require_all = request.model_copy(
        update={
            "hard_constraints": request.hard_constraints.model_copy(
                update={"require_all_members_compatible": True}
            )
        }
    )

    result = discover_basal_neighborhood(require_all)

    assert result.discovery.disposition.feasibility is SearchFeasibilityStatus.INFEASIBLE
    assert result.discovery.payload_compatibility.compatible_assignments == 1
    assert result.realizations == ()


def test_resealed_basal_result_rejects_corrupted_shell_accounting() -> None:
    request = _request(
        ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
        payload=DegeneratePayload(sequence="CMAC"),
    )
    require_all = request.model_copy(
        update={
            "hard_constraints": request.hard_constraints.model_copy(
                update={"require_all_members_compatible": True}
            )
        }
    )
    result = discover_basal_neighborhood(require_all)
    level = result.discovery.overhead_levels[-1]
    corrupted_level = level.model_copy(update={"candidate_count": level.candidate_count + 1})
    corrupted_discovery = result.discovery.model_copy(
        update={"overhead_levels": (*result.discovery.overhead_levels[:-1], corrupted_level)}
    )

    with pytest.raises(ValidationError, match="candidate count"):
        BasalNeighborhoodDiscoveryResult.create(
            discovery=corrupted_discovery,
            realizations=result.realizations,
        )


def test_basal_family_identity_ignores_presentation_and_vendor_metadata() -> None:
    request = _request(ConstructionEndpoint.HAIRPIN_PCR_DUPLEX)
    renamed_request = request.model_copy(update={"name": "renamed basal search"})
    enzymes = tuple(
        enzyme.model_copy(
            update={"vendor_metadata": (VendorMetadata(vendor_name="Example Vendor"),)}
        )
        for enzyme in request.enzyme_provisioning.catalog.enzymes
    )
    vendor_catalog = request.enzyme_provisioning.catalog.model_copy(update={"enzymes": enzymes})
    vendor_provisioning = request.enzyme_provisioning.model_copy(update={"catalog": vendor_catalog})
    vendor_request = request.model_copy(update={"enzyme_provisioning": vendor_provisioning})

    base = discover_basal_neighborhood(request)
    renamed = discover_basal_neighborhood(renamed_request)
    vendor = discover_basal_neighborhood(vendor_request)

    assert base.discovery.result_id == renamed.discovery.result_id == vendor.discovery.result_id
    assert base.result_id == renamed.result_id == vendor.result_id


def test_basal_degenerate_payload_accounting_is_exhaustive_and_require_all_is_enforced() -> None:
    request = _request(
        ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
        payload=DegeneratePayload(sequence="CMAC"),
    )
    result = discover_basal_neighborhood(request)

    assert result.discovery.disposition.completion is SearchCompletionStatus.COMPLETE
    assert result.discovery.payload_compatibility.total_assignments == 2
    assert result.discovery.payload_compatibility.compatible_assignments == 1
    assert result.discovery.payload_compatibility.excluded_assignments == 1
    assert {record.payload_sequence for record in result.realizations} == {"CCAC"}

    require_all = request.model_copy(
        update={
            "hard_constraints": request.hard_constraints.model_copy(
                update={"require_all_members_compatible": True}
            )
        }
    )
    blocked = discover_basal_neighborhood(require_all)
    assert blocked.discovery.disposition.feasibility is SearchFeasibilityStatus.INFEASIBLE
    assert blocked.realizations == ()
    assert all(not level.realization_ids for level in blocked.discovery.overhead_levels)
    assert all(level.complete for level in blocked.discovery.overhead_levels)
    assert all(
        level.candidate_count == level.rejected_count
        and sum(reason.count for reason in level.failure_reasons) == level.rejected_count
        for level in blocked.discovery.overhead_levels
    )
    assert any(
        reason.code == "all-members-compatibility-required"
        for level in blocked.discovery.overhead_levels
        for reason in level.failure_reasons
    )


def test_basal_degenerate_payload_over_bound_is_truthfully_uncomputed() -> None:
    result = discover_basal_neighborhood(
        _request(
            ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
            payload=DegeneratePayload(sequence="NNNN"),
            max_nodes=1,
        )
    )

    assert result.discovery.disposition.completion is SearchCompletionStatus.TRUNCATED
    assert result.discovery.payload_compatibility.status == "not_computed"
    assert result.discovery.payload_compatibility.total_assignments == 256
    assert result.discovery.payload_compatibility.warning


def test_any_nick_strand_enumerates_both_exact_strands_deterministically() -> None:
    request = _request(
        ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
        payload=DegeneratePayload(sequence="YTCC"),
    )
    assert isinstance(request.geometry_domain, BasalGeometryDomain)
    request = request.model_copy(
        update={
            "geometry_domain": request.geometry_domain.model_copy(
                update={"nick_strand": NickStrandSelection.ANY}
            )
        }
    )

    result = discover_basal_neighborhood(request)

    observed = tuple(record.basal_nick.strand for record in result.realizations)
    assert set(observed) == {Strand.TOP, Strand.BOTTOM}
    assert observed.index(Strand.TOP) < observed.index(Strand.BOTTOM)
    assert {
        record.local_realization.achieved_geometry.nick_strand for record in result.realizations
    } == {Strand.TOP, Strand.BOTTOM}


def test_exact_basal_realization_helpers_reject_unexpanded_nick_strand() -> None:
    request = _request(ConstructionEndpoint.HAIRPIN_PCR_DUPLEX)
    exact_target = _exact_target(request)
    any_target = exact_target.model_copy(update={"nick_strand": NickStrandSelection.ANY})
    program = iter_basal_programs(
        request.enzyme_provisioning,
        target=exact_target,
        endpoint=request.endpoint,
    )[0]

    with pytest.raises(ValueError, match="exact nick strand"):
        list(
            iter_basal_program_solutions(
                payload_sequence="CCCC",
                target=any_target,
                endpoint=request.endpoint,
                program=program,
            )
        )

    solution = next(
        candidate
        for candidate in iter_basal_program_solutions(
            payload_sequence="CCCC",
            target=exact_target,
            endpoint=request.endpoint,
            program=program,
        )
        if not isinstance(candidate, BasalPlacementFailure)
    )
    with pytest.raises(ValueError, match="exact nick strand"):
        _nicked_duplex(solution, any_target)


def test_basal_realization_rejects_non_pcr_endpoint_before_materialization() -> None:
    request = _request(ConstructionEndpoint.HAIRPIN_PCR_DUPLEX)
    target = _exact_target(request)
    route = iter_basal_programs(
        request.enzyme_provisioning,
        target=target,
        endpoint=request.endpoint,
    )[0]
    solution = next(
        candidate
        for candidate in iter_basal_program_solutions(
            payload_sequence="CCCC",
            target=target,
            endpoint=request.endpoint,
            program=route,
        )
        if not isinstance(candidate, BasalPlacementFailure)
    )
    wrong_endpoint = request.model_copy(update={"endpoint": ConstructionEndpoint.SSDNA_HAIRPIN})

    with pytest.raises(ValueError, match="hairpin PCR duplex endpoint"):
        _realization(
            request=wrong_endpoint,
            payload_sequence="CCCC",
            target=target,
            route=route,
            solution=solution,
        )


def test_basal_realization_rejects_unresolved_target_and_pairing_state() -> None:
    request = _request(ConstructionEndpoint.HAIRPIN_PCR_DUPLEX)
    target = _exact_target(request)
    route = iter_basal_programs(
        request.enzyme_provisioning,
        target=target,
        endpoint=request.endpoint,
    )[0]
    solution = next(
        candidate
        for candidate in iter_basal_program_solutions(
            payload_sequence="CCCC",
            target=target,
            endpoint=request.endpoint,
            program=route,
        )
        if not isinstance(candidate, BasalPlacementFailure)
    )
    any_target = target.model_copy(update={"nick_strand": NickStrandSelection.ANY})

    with pytest.raises(ValueError, match="exact nick strand"):
        _realization(
            request=request,
            payload_sequence="CCCC",
            target=any_target,
            route=route,
            solution=solution,
        )
    with pytest.raises(ValueError, match="exact pairing state"):
        _realization(
            request=request,
            payload_sequence="CCCC",
            target=target,
            route=route,
            solution=replace(solution, pairing_state=None),
        )


@pytest.mark.parametrize(
    ("diagnostic_codes", "failure_code"),
    (
        (("HOP-STAGE-004",), "unintended-actionable-site"),
        (("HOP-PROGRAM-001",), "operation-limit"),
        (("HOP-STAGE-003",), "intended-site-not-actionable"),
        (("HOP-STAGE-999",), "reaction-program-conflict"),
    ),
)
def test_basal_reaction_diagnostics_map_to_stable_local_failure_codes(
    diagnostic_codes: tuple[str, ...],
    failure_code: str,
) -> None:
    assert _failure_code(diagnostic_codes) == failure_code


def test_nick_offset_and_strand_change_exact_binding_geometry() -> None:
    base = discover_basal_neighborhood(
        _request(ConstructionEndpoint.HAIRPIN_PCR_DUPLEX)
    ).realizations[0]
    offset_domain = BasalGeometryDomain(
        nick_strand=Strand.TOP,
        nick_offsets_nt=(1,),
        pairing_constraints=_pairing_constraints(),
    )
    offset = discover_basal_neighborhood(
        _request(
            ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
            domain=offset_domain,
        )
    ).realizations[0]
    bottom_request = _request(ConstructionEndpoint.HAIRPIN_PCR_DUPLEX, payload="TTCC")
    assert isinstance(bottom_request.geometry_domain, BasalGeometryDomain)
    bottom_request = bottom_request.model_copy(
        update={
            "geometry_domain": bottom_request.geometry_domain.model_copy(
                update={"nick_strand": Strand.BOTTOM}
            )
        }
    )
    bottom = discover_basal_neighborhood(bottom_request).realizations[0]

    assert base.basal_nick.boundary != offset.basal_nick.boundary
    assert base.basal_nick.binding_id != offset.basal_nick.binding_id
    assert base.basal_nick.strand is Strand.TOP
    assert bottom.basal_nick.strand is Strand.BOTTOM
    assert base.basal_nick.binding_id != bottom.basal_nick.binding_id


def test_basal_operation_accounting_contains_only_the_local_nick() -> None:
    result = discover_basal_neighborhood(
        _request(ConstructionEndpoint.HAIRPIN_PCR_DUPLEX, max_operations=2)
    )

    assert result.discovery.disposition.completion is SearchCompletionStatus.COMPLETE
    assert all(len(record.reaction_programs) == 1 for record in result.realizations)


def test_payload_and_boundary_sites_are_scanned_in_the_exact_precursor() -> None:
    result = discover_basal_neighborhood(
        _request(ConstructionEndpoint.HAIRPIN_PCR_DUPLEX, payload="CAAC")
    )

    assert result.discovery.disposition.feasibility is SearchFeasibilityStatus.INFEASIBLE
    assert "unintended-actionable-site" in {
        reason.code for reason in result.discovery.failure_reasons
    }


def test_basal_realization_identity_seals_the_exact_endpoint_projection() -> None:
    record = discover_basal_neighborhood(
        _request(ConstructionEndpoint.HAIRPIN_PCR_DUPLEX)
    ).realizations[0]

    assert record.basal_realization_id.startswith("hop:basal-realization/")
    changed = record.model_dump(mode="json")
    source = changed["source_precursor_sequence"]
    changed["source_precursor_sequence"] = ("A" if source[0] != "A" else "C") + source[1:]
    with pytest.raises(ValidationError, match="basal_realization_id"):
        BasalRealizationRecord.model_validate_json(json.dumps(changed))


def test_basal_realization_rejects_a_resealed_non_derivable_nick_transition() -> None:
    record = discover_basal_neighborhood(
        _request(ConstructionEndpoint.HAIRPIN_PCR_DUPLEX)
    ).realizations[0]
    program = record.reaction_programs[0]
    post = program.states[1]
    molecule = post.molecules[0]
    changed_sequence = (
        "C" if molecule.reference_sequence_5prime[0] == "A" else "A"
    ) + molecule.reference_sequence_5prime[1:]
    changed_molecule = molecule.model_copy(update={"reference_sequence_5prime": changed_sequence})
    changed_post = post.model_copy(update={"molecules": (changed_molecule,)})
    changed_program = program.model_copy(update={"states": (program.states[0], changed_post)})
    content = {
        name: getattr(record, name)
        for name in BasalRealizationRecord.model_fields
        if name != "basal_realization_id"
    }
    content["reaction_programs"] = (changed_program,)

    with pytest.raises(ValidationError, match="nick program post-state"):
        BasalRealizationRecord.create(**content)


def test_basal_realization_replays_embedded_enzyme_definitions_against_exact_bindings() -> None:
    record = discover_basal_neighborhood(
        _request(ConstructionEndpoint.HAIRPIN_PCR_DUPLEX)
    ).realizations[0]
    changed_definition = record.enzyme_definitions[0]
    changed_enzyme = changed_definition.enzyme.model_copy(update={"cut_offset_reference_strand": 5})
    changed_definition = changed_definition.model_copy(
        update={
            "enzyme": changed_enzyme,
            "digest": characterized_enzyme_digest(changed_enzyme),
        }
    )
    content = {
        name: getattr(record, name)
        for name in BasalRealizationRecord.model_fields
        if name != "basal_realization_id"
    }
    content["enzyme_definitions"] = (changed_definition,)

    with pytest.raises(ValidationError, match="binding cuts must replay"):
        BasalRealizationRecord.create(**content)


def test_basal_realization_replays_stored_stage_assessments_against_program_operations() -> None:
    record = discover_basal_neighborhood(
        _request(ConstructionEndpoint.HAIRPIN_PCR_DUPLEX)
    ).realizations[0]
    assessment = record.stage_assessments[0]
    intended = assessment.intended_bindings[0]
    assert intended.reference_cut is not None
    changed_intended = intended.model_copy(
        update={"reference_cut": Boundary(offset=intended.reference_cut.offset + 1)}
    )
    changed_assessment = assessment.model_copy(
        update={
            "intended_bindings": (
                changed_intended,
                *assessment.intended_bindings[1:],
            )
        }
    )
    content = {
        name: getattr(record, name)
        for name in BasalRealizationRecord.model_fields
        if name != "basal_realization_id"
    }
    content["stage_assessments"] = (changed_assessment,)

    with pytest.raises(ValidationError, match="replay exact binding evidence"):
        BasalRealizationRecord.create(**content)


def _basal_record_content(record: BasalRealizationRecord) -> dict[str, object]:
    return {
        name: getattr(record, name)
        for name in BasalRealizationRecord.model_fields
        if name != "basal_realization_id"
    }


@pytest.mark.parametrize(
    ("corruption", "message"),
    (
        ("local-sequence", "exact endpoint-bearing state"),
        ("local-bindings", "preserve every exact binding"),
        ("local-stages", "preserve every exact reaction stage"),
        ("assessment-stages", "cover every reaction stage"),
        ("rejected-stage", "cannot contain a rejected reaction stage"),
        ("basal-nick-binding", "reference one exact local binding"),
        ("pairing-constraints", "retain the authored pairing constraints"),
        ("literal-pairing", "satisfy authored class constraints"),
        ("enzyme-definitions", "cover every binding exactly"),
        ("binding-role", "only basal-nick bindings"),
        ("duplicate-binding", "bijectively to unique bindings"),
        ("operation-binding", "bijectively to embedded enzyme bindings"),
        ("assessment-pre-state", "replay its exact pre-state"),
        ("undeclared-binding", "cannot retain undeclared bindings"),
        ("assessment-operations", "replay every declared operation"),
        ("material-accounting", "derive from exact materials"),
        ("payload-map", "Retained overhead"),
        ("precursor-state", "act on the exact source precursor"),
        ("nicked-duplex", "replay the exact basal binding"),
        ("ligated-product", "concatenate the exact source and adapter"),
        ("pcr-sequence", "copy the complete adapter-ligated duplex"),
        ("pcr-lineage", "replay exact adapter-ligated lineage and ends"),
    ),
)
def test_basal_realization_rejects_resealed_authority_corruption(
    corruption: str,
    message: str,
) -> None:
    record = discover_basal_neighborhood(
        _request(ConstructionEndpoint.HAIRPIN_PCR_DUPLEX)
    ).realizations[0]
    content = _basal_record_content(record)
    local = record.local_realization
    program = record.reaction_programs[0]
    assessment = record.stage_assessments[0]

    if corruption == "local-sequence":
        content["local_realization"] = type(local).create(
            local_sequence="A",
            enzyme_binding_ids=local.enzyme_binding_ids,
            stage_ids=local.stage_ids,
            achieved_geometry=local.achieved_geometry,
        )
    elif corruption == "local-bindings":
        content["local_realization"] = type(local).create(
            local_sequence=local.local_sequence,
            enzyme_binding_ids=(),
            stage_ids=local.stage_ids,
            achieved_geometry=local.achieved_geometry,
        )
    elif corruption == "local-stages":
        content["local_realization"] = type(local).create(
            local_sequence=local.local_sequence,
            enzyme_binding_ids=local.enzyme_binding_ids,
            stage_ids=(),
            achieved_geometry=local.achieved_geometry,
        )
    elif corruption == "assessment-stages":
        content["stage_assessments"] = (
            assessment.model_copy(update={"stage_id": "unrelated-stage"}),
        )
    elif corruption == "rejected-stage":
        content["stage_assessments"] = (
            assessment.model_copy(
                update={
                    "report": CheckReport(
                        diagnostics=(
                            Diagnostic(
                                code="HOP-STAGE-004",
                                severity=Severity.ERROR,
                                path="reaction.stages[0]",
                                message="The stored stage is not accepted.",
                            ),
                        )
                    )
                }
            ),
        )
    elif corruption == "basal-nick-binding":
        content["basal_nick"] = record.basal_nick.model_copy(
            update={"binding_id": "hop:enzyme-binding/" + "0" * 64 + "@1"}
        )
    elif corruption == "pairing-constraints":
        content["pairing_constraints"] = (
            BasalPairAllowance.ANY,
            *record.pairing_constraints[1:],
        )
    elif corruption == "literal-pairing":
        changed_constraints = list(record.local_realization.achieved_geometry.pairing_constraints)
        changed_constraints[2] = changed_constraints[2].model_copy(
            update={"allowed_class": BasalPairAllowance.WOBBLE}
        )
        changed_geometry = record.local_realization.achieved_geometry.model_copy(
            update={"pairing_constraints": tuple(changed_constraints)}
        )
        content["local_realization"] = type(local).create(
            local_sequence=local.local_sequence,
            enzyme_binding_ids=local.enzyme_binding_ids,
            stage_ids=local.stage_ids,
            achieved_geometry=changed_geometry,
        )
        changed_allowances = list(record.pairing_constraints)
        changed_allowances[2] = BasalPairAllowance.WOBBLE
        content["pairing_constraints"] = tuple(changed_allowances)
    elif corruption == "enzyme-definitions":
        content["enzyme_definitions"] = ()
    elif corruption == "binding-role":
        binding = record.enzyme_bindings[0]
        changed_binding = type(binding).create(
            enzyme_id=binding.enzyme_id,
            role=EnzymeRole.FOLDBACK_NICK,
            strand=binding.strand,
            recognition_span=binding.recognition_span,
            orientation=binding.orientation,
            reference_cut=binding.reference_cut,
            complement_cut=binding.complement_cut,
        )
        content["enzyme_bindings"] = (changed_binding,)
        content["local_realization"] = type(local).create(
            local_sequence=local.local_sequence,
            enzyme_binding_ids=(changed_binding.binding_id,),
            stage_ids=local.stage_ids,
            achieved_geometry=local.achieved_geometry,
        )
        content["basal_nick"] = record.basal_nick.model_copy(
            update={"binding_id": changed_binding.binding_id}
        )
    elif corruption == "duplicate-binding":
        binding = record.enzyme_bindings[0]
        content["enzyme_bindings"] = (binding, binding)
        content["local_realization"] = type(local).create(
            local_sequence=local.local_sequence,
            enzyme_binding_ids=(binding.binding_id, binding.binding_id),
            stage_ids=local.stage_ids,
            achieved_geometry=local.achieved_geometry,
        )
    elif corruption == "operation-binding":
        operation = program.stages[0].operations[0]
        intended = operation.intended_binding.model_copy(
            update={"recognition_span": Span(start=Boundary(offset=1), end=Boundary(offset=4))}
        )
        changed_operation = operation.model_copy(update={"intended_binding": intended})
        changed_stage = program.stages[0].model_copy(update={"operations": (changed_operation,)})
        content["reaction_programs"] = (program.model_copy(update={"stages": (changed_stage,)}),)
    elif corruption == "assessment-pre-state":
        content["stage_assessments"] = (
            assessment.model_copy(update={"resolved_against_state_id": "unrelated-state"}),
        )
    elif corruption == "undeclared-binding":
        content["stage_assessments"] = (
            assessment.model_copy(update={"undeclared_bindings": assessment.intended_bindings}),
        )
    elif corruption == "assessment-operations":
        content["stage_assessments"] = (assessment.model_copy(update={"intended_bindings": ()}),)
    elif corruption == "material-accounting":
        content["material_accounting"] = record.material_accounting.model_copy(
            update={"retained_nt": record.material_accounting.retained_nt + 1}
        )
    elif corruption == "payload-map":
        segment = record.payload_source_map.segments[0]
        shifted = segment.model_copy(
            update={
                "source_span": Span(
                    start=Boundary(offset=segment.source_span.start.offset - 1),
                    end=Boundary(offset=segment.source_span.end.offset - 1),
                )
            }
        )
        content["payload_source_map"] = record.payload_source_map.model_copy(
            update={"segments": (shifted,)}
        )
    elif corruption == "precursor-state":
        molecule = program.states[0].molecules[0]
        changed_molecule = molecule.model_copy(
            update={
                "reference_sequence_5prime": "C" + molecule.reference_sequence_5prime[1:],
                "complement_sequence_5prime": "G" + molecule.complement_sequence_5prime[1:],
            }
        )
        changed_states = tuple(
            state.model_copy(update={"molecules": (changed_molecule,)}) for state in program.states
        )
        content["reaction_programs"] = (program.model_copy(update={"states": changed_states}),)
    elif corruption == "nicked-duplex":
        nick_site = record.nicked_duplex.sites[0]
        changed_site = nick_site.model_copy(
            update={
                "nick": nick_site.nick.model_copy(
                    update={"boundary": Boundary(offset=nick_site.nick.boundary.offset + 1)}
                )
            }
        )
        content["nicked_duplex"] = record.nicked_duplex.model_copy(
            update={"sites": (changed_site,)}
        )
    elif corruption == "ligated-product":
        product = record.adapter_ligated_product
        changed_source = product.source_strand.model_copy(
            update={"sequence": "C" + product.source_strand.sequence[1:]}
        )
        changed_strand = product.strand.model_copy(
            update={"sequence": changed_source.sequence + product.adapter_strand.sequence}
        )
        content["adapter_ligated_product"] = record.adapter_ligated_product.model_copy(
            update={
                "source_strand": changed_source,
                "strand": changed_strand,
            }
        )
    elif corruption == "pcr-sequence":
        top = record.hairpin_pcr_duplex.top_strand
        bottom = record.hairpin_pcr_duplex.bottom_strand
        changed_top_sequence = "C" + top.sequence[1:]
        content["hairpin_pcr_duplex"] = record.hairpin_pcr_duplex.model_copy(
            update={
                "top_strand": top.model_copy(update={"sequence": changed_top_sequence}),
                "bottom_strand": bottom.model_copy(
                    update={"sequence": reverse_complement_iupac(changed_top_sequence)}
                ),
            }
        )
    elif corruption == "pcr-lineage":
        strand = record.hairpin_pcr_duplex.top_strand
        changed_lineage = strand.lineage[0].model_copy(update={"origin_id": "unrelated-source"})
        content["hairpin_pcr_duplex"] = record.hairpin_pcr_duplex.model_copy(
            update={
                "top_strand": strand.model_copy(
                    update={"lineage": (changed_lineage, *strand.lineage[1:])}
                )
            }
        )
    else:
        raise AssertionError(f"Unhandled corruption case: {corruption}")

    with pytest.raises(ValidationError, match=message):
        BasalRealizationRecord.create(**content)


def test_basal_local_authority_contains_only_the_nick_program_and_binding() -> None:
    record = discover_basal_neighborhood(
        _request(ConstructionEndpoint.HAIRPIN_PCR_DUPLEX)
    ).realizations[0]
    assert len(record.reaction_programs) == 1
    assert len(record.enzyme_bindings) == 1
    assert record.enzyme_bindings[0].role is EnzymeRole.BASAL_NICK


def test_pcr_projection_does_not_invent_primers_or_strands_and_preserves_ligation_lineage() -> None:
    record = discover_basal_neighborhood(
        _request(ConstructionEndpoint.HAIRPIN_PCR_DUPLEX)
    ).realizations[0]

    assert record.adapter_annealed_complex is not None
    assert record.adapter_ligated_product is not None
    assert record.hairpin_pcr_duplex is not None
    assert record.adapter_annealed_complex.strand_ids == (
        "source-fragment",
        "ligation-adapter",
    )
    assert not {
        "pcr-forward-primer",
        "pcr-reverse-primer",
    } & {item.material_id for item in record.materials}
    assert record.hairpin_pcr_duplex.primer_bindings == ()
    source_length = len(record.adapter_ligated_product.source_strand.sequence)
    assert {
        item.origin_id for item in record.adapter_ligated_product.strand.lineage[:source_length]
    } == {"source-precursor"}
    assert {
        item.origin_id for item in record.adapter_ligated_product.strand.lineage[source_length:]
    } == {"ligation-adapter"}


def test_basal_pcr_intermediate_serializes_exact_strands_and_lineage() -> None:
    record = discover_basal_neighborhood(
        _request(ConstructionEndpoint.HAIRPIN_PCR_DUPLEX)
    ).realizations[0]
    assert record.hairpin_pcr_duplex is not None
    top = record.hairpin_pcr_duplex.top_strand
    bottom = record.hairpin_pcr_duplex.bottom_strand
    assert bottom.sequence == reverse_complement_iupac(top.sequence)
    assert len(top.lineage) == len(top.sequence)
    assert len(bottom.lineage) == len(bottom.sequence)
    assert BasalRealizationRecord.model_validate_json(record.model_dump_json()) == record


@pytest.mark.parametrize("strand_name", ("top_strand", "bottom_strand"))
def test_basal_pcr_intermediate_rejects_resealed_lineage_corruption(
    strand_name: str,
) -> None:
    record = discover_basal_neighborhood(
        _request(ConstructionEndpoint.HAIRPIN_PCR_DUPLEX)
    ).realizations[0]
    assert record.hairpin_pcr_duplex is not None
    product = record.hairpin_pcr_duplex
    strand = getattr(product, strand_name)
    changed_first = strand.lineage[0].model_copy(update={"origin_id": "corrupt-parent"})
    changed_strand = strand.model_copy(update={"lineage": (changed_first, *strand.lineage[1:])})
    changed_product = product.model_copy(update={strand_name: changed_strand})
    content = {
        name: getattr(record, name)
        for name in BasalRealizationRecord.model_fields
        if name != "basal_realization_id"
    }
    content["hairpin_pcr_duplex"] = changed_product

    with pytest.raises(ValidationError, match=r"PCR|lineage|identity"):
        BasalRealizationRecord.create(**content)


def test_endpoint_relative_material_accounting_partitions_retained_and_transient_sequence() -> None:
    pcr = discover_basal_neighborhood(
        _request(ConstructionEndpoint.HAIRPIN_PCR_DUPLEX)
    ).realizations[0]

    pcr_retained = next(item for item in pcr.materials if item.role.value == "retained")
    assert pcr.hairpin_pcr_duplex is not None
    assert pcr_retained.sequence_5prime == pcr.hairpin_pcr_duplex.top_strand.sequence
    assert pcr.material_accounting.transient_nt == 0


def test_basal_pcr_material_accounting_rejects_invented_transient_bases() -> None:
    record = discover_basal_neighborhood(
        _request(ConstructionEndpoint.HAIRPIN_PCR_DUPLEX)
    ).realizations[0]
    assert record.hairpin_pcr_duplex is not None
    changed_materials = (
        *record.materials,
        BasalMaterialRecord(
            material_id="invented-transient",
            role=BasalMaterialRole.TRANSIENT,
            sequence_5prime=record.hairpin_pcr_duplex.top_strand.sequence,
        ),
    )
    content = {
        name: getattr(record, name)
        for name in BasalRealizationRecord.model_fields
        if name != "basal_realization_id"
    }
    content["materials"] = changed_materials
    content["material_accounting"] = BasalMaterialAccounting(
        retained_nt=sum(
            len(item.sequence_5prime)
            for item in changed_materials
            if item.role is BasalMaterialRole.RETAINED
        ),
        transient_nt=sum(
            len(item.sequence_5prime)
            for item in changed_materials
            if item.role is BasalMaterialRole.TRANSIENT
        ),
        auxiliary_nt=sum(
            len(item.sequence_5prime)
            for item in changed_materials
            if item.role is BasalMaterialRole.AUXILIARY
        ),
    )

    with pytest.raises(ValidationError, match=r"material|partition|transient"):
        BasalRealizationRecord.create(**content)


def test_overhead_coverage_and_geometry_groups_are_complete_and_lossless() -> None:
    domain = BasalGeometryDomain(
        nick_strand=Strand.TOP,
        nick_offsets_nt=(0, 1),
        pairing_constraints=_pairing_constraints(),
    )
    complete = discover_basal_neighborhood(
        _request(
            ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
            domain=domain,
            extra_nickase=True,
        )
    )
    truncated = discover_basal_neighborhood(
        _request(
            ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
            domain=domain,
            extra_nickase=True,
            max_nodes=1,
        )
    )

    assert complete.discovery.disposition.completion is SearchCompletionStatus.COMPLETE
    assert tuple(
        level.retained_overhead_nt for level in complete.discovery.overhead_levels
    ) == tuple(range(9))
    ids = {item.local_realization.local_realization_id for item in complete.realizations}
    grouped_ids = {
        realization_id
        for group in complete.discovery.achieved_geometry_groups
        for realization_id in group.realization_ids
    }
    assert grouped_ids == ids
    assert len(ids) == len(complete.realizations)
    assert len(ids) > 4
    assert truncated.discovery.disposition.completion is SearchCompletionStatus.TRUNCATED
    assert (
        truncated.discovery.disposition.termination_reason is SearchTerminationReason.EVALUATION_CAP
    )
    assert truncated.discovery.overhead_levels[-1].complete is False
    assert all(
        level.candidate_count == len(level.realization_ids) + level.rejected_count
        and sum(reason.count for reason in level.failure_reasons) == level.rejected_count
        for level in truncated.discovery.overhead_levels
    )

    with pytest.raises(ValidationError, match="canonical key order"):
        NeighborhoodDiscoveryResult.model_validate(
            complete.discovery.model_dump(mode="python")
            | {
                "achieved_geometry_groups": tuple(
                    reversed(complete.discovery.achieved_geometry_groups)
                )
            }
        )
    member_group = next(
        group
        for group in complete.discovery.achieved_geometry_groups
        if len(group.realization_ids) > 1
    )
    changed_groups = tuple(
        group.model_copy(update={"realization_ids": tuple(reversed(group.realization_ids))})
        if group.group_key == member_group.group_key
        else group
        for group in complete.discovery.achieved_geometry_groups
    )
    with pytest.raises(ValidationError, match="preserve realization order"):
        NeighborhoodDiscoveryResult.model_validate(
            complete.discovery.model_dump(mode="python")
            | {"achieved_geometry_groups": changed_groups}
        )


def test_basal_bounds_at_an_overhead_boundary_do_not_emit_an_unentered_level() -> None:
    exact = discover_basal_neighborhood(_request(ConstructionEndpoint.HAIRPIN_PCR_DUPLEX))
    active_level = exact.discovery.overhead_levels[-1]
    domain = BasalGeometryDomain(
        nick_strand=Strand.TOP,
        nick_offsets_nt=(0, 1),
        pairing_constraints=_pairing_constraints(),
    )

    for limits in (
        {"max_nodes": active_level.candidate_count, "max_realizations": 100},
        {"max_nodes": 100, "max_realizations": len(active_level.realization_ids)},
    ):
        result = discover_basal_neighborhood(
            _request(
                ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
                domain=domain,
                **limits,
            )
        )

        assert result.discovery.disposition.completion is SearchCompletionStatus.TRUNCATED
        assert result.discovery.overhead_levels[-1].retained_overhead_nt == 8
        assert result.discovery.overhead_levels[-1].complete is False


def test_exact_basal_domain_is_complete_when_a_bound_equals_exhaustive_count() -> None:
    exhaustive = discover_basal_neighborhood(
        _request(
            ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
            max_nodes=10_000,
            max_realizations=10_000,
        )
    )
    examined = sum(level.candidate_count for level in exhaustive.discovery.overhead_levels)
    realized = len(exhaustive.realizations)

    node_bounded = discover_basal_neighborhood(
        _request(
            ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
            max_nodes=examined,
            max_realizations=10_000,
        )
    )
    realization_bounded = discover_basal_neighborhood(
        _request(
            ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
            max_nodes=10_000,
            max_realizations=realized,
        )
    )

    assert node_bounded.discovery.disposition.completion is SearchCompletionStatus.COMPLETE
    assert realization_bounded.discovery.disposition.completion is SearchCompletionStatus.COMPLETE


def test_basal_verification_rejects_self_asserted_execution_environment() -> None:
    raw = discover_basal_neighborhood(_request(ConstructionEndpoint.HAIRPIN_PCR_DUPLEX))
    execution = raw.discovery.execution.model_copy(update={"environment": {"forged": "true"}})
    discovery = raw.discovery.model_copy(
        update={"execution": execution, "execution_id": execution.execution_id}
    )
    forged = BasalNeighborhoodDiscoveryResult.create(
        discovery=discovery,
        realizations=raw.realizations,
    )

    with pytest.raises(ConstructionVerificationError, match="deterministic discovery replay"):
        verify_basal_neighborhood_result(forged)
    with pytest.raises(ConstructionVerificationError, match="deterministic discovery replay"):
        VerifiedBasalNeighborhoodResult(result=forged)


def test_basal_wrapper_rejects_partial_final_level_resealed_as_complete() -> None:
    result = discover_basal_neighborhood(
        _request(
            ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
            max_nodes=1,
            max_realizations=100,
        )
    )
    level = result.discovery.overhead_levels[-1]
    assert level.complete is False
    corrupted_level = level.model_copy(update={"complete": True})
    corrupted_discovery = result.discovery.model_copy(
        update={"overhead_levels": (*result.discovery.overhead_levels[:-1], corrupted_level)}
    )

    with pytest.raises(ValidationError, match="Truncated coverage"):
        BasalNeighborhoodDiscoveryResult.create(
            discovery=corrupted_discovery,
            realizations=result.realizations,
        )
