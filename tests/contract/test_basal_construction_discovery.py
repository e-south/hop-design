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

import pytest
from pydantic import ValidationError

from hop_design.design.construction.basal import discover_basal_neighborhood
from hop_design.design.construction.basal.reactions import _nicked_duplex
from hop_design.design.construction.verification import (
    ConstructionVerificationError,
    VerifiedBasalNeighborhoodResult,
    verify_basal_neighborhood_result,
)
from hop_design.kernel.construction.basal import (
    BasalPlacementFailure,
    iter_basal_program_solutions,
    iter_basal_programs,
    resolve_basal_pairing_profile,
)
from hop_design.models.construction import (
    BasalNickStrand,
    BasalPairAllowance,
    BasalPairClass,
    BasalPairingConstraint,
    BasalTarget,
    ConstructionConstraints,
    ConstructionEndpoint,
    EndGenerationRequest,
    EnumerationPolicy,
    FinalPayloadReference,
    LocalNeighborhoodFamily,
    LocalNeighborhoodRequest,
    NeighborhoodDiscoveryResult,
    RelaxationCoordinate,
    RelaxationMode,
    RelaxationPolicy,
    RouteFamily,
    SearchCompletionStatus,
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
    restrictions = [
        EnzymeRoleRestriction(
            role=EnzymeRole.BASAL_NICK,
            allowed_enzyme_ids=tuple(
                enzyme.enzyme_id for enzyme in enzymes if enzyme.enzyme_class is EnzymeClass.NICKASE
            ),
        )
    ]
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
) -> tuple[BasalPairingConstraint, ...]:
    return tuple(
        BasalPairingConstraint(
            profile_position=position,
            allowed_class=allowance,
        )
        for position, allowance in enumerate(allowances)
    )


def _request(
    endpoint: ConstructionEndpoint,
    *,
    payload: str | ExactPayload | DegeneratePayload = "CCCC",
    pairing_constraints: tuple[BasalPairingConstraint, ...] | None = None,
    requested_overhangs: tuple[str, ...] = (),
    type_iis_cut_offset_nt: int = 0,
    max_nodes: int = 10000,
    max_realizations: int = 10000,
    relaxation: RelaxationPolicy | None = None,
    extra_nickase: bool = False,
    max_operations: int = 3,
    type_iis_pattern: str = "GGTCTC",
) -> LocalNeighborhoodRequest:
    enzymes = [_nickase()]
    if extra_nickase:
        enzymes.append(_nickase("example:enzyme/basal-nick-b@1"))
    if endpoint is ConstructionEndpoint.CLONE_READY_DUPLEX:
        enzymes.append(_type_iis(pattern=type_iis_pattern))
    target = BasalTarget(
        nick_strand=Strand.TOP,
        nick_offset_nt=0,
        pairing_constraints=(
            ()
            if endpoint is ConstructionEndpoint.SSDNA_HAIRPIN
            else pairing_constraints or _pairing_constraints()
        ),
        ligation_proximal_match_required=(endpoint is not ConstructionEndpoint.SSDNA_HAIRPIN),
        end_generation=(
            EndGenerationRequest(
                type_iis_cut_offset_nt=type_iis_cut_offset_nt,
                requested_overhangs=requested_overhangs,
            )
            if endpoint is ConstructionEndpoint.CLONE_READY_DUPLEX
            else None
        ),
    )
    return LocalNeighborhoodRequest(
        payload=FinalPayloadReference(
            payload=(ExactPayload(sequence=payload) if isinstance(payload, str) else payload),
            basal_boundary=Boundary(offset=0),
            foldback_boundary=Boundary(offset=4),
        ),
        family=LocalNeighborhoodFamily.BASAL,
        route_family=RouteFamily.LINEAR_SOURCE_V1,
        endpoint=endpoint,
        target=target,
        hard_constraints=ConstructionConstraints(),
        enzyme_provisioning=_provisioning(*enzymes, max_operations=max_operations),
        relaxation=relaxation or RelaxationPolicy(mode=RelaxationMode.EXACT_ONLY, max_radius=0),
        enumeration=EnumerationPolicy(
            max_search_nodes=max_nodes,
            max_realizations=max_realizations,
        ),
    )


def test_literal_pairing_is_variable_length_proximal_outward_and_projects_mwx() -> None:
    profile = resolve_basal_pairing_profile(
        source_sequence_5prime="AGCA",
        adapter_sequence_5prime="TATT",
        end_projection_positions=(2,),
    )

    assert [pair.profile_position for pair in profile.pairs] == [0, 1, 2, 3]
    assert [(pair.source_index, pair.adapter_index) for pair in profile.pairs] == [
        (3, 0),
        (2, 1),
        (1, 2),
        (0, 3),
    ]
    assert profile.compact_profile == "MXWM"
    assert profile.pairs[2].participates_in_end_projection

    shorter = resolve_basal_pairing_profile(
        source_sequence_5prime="ACG",
        adapter_sequence_5prime="CGT",
    )
    assert shorter.compact_profile == "MMM"


def test_literal_pair_record_rejects_a_pair_class_that_disagrees_with_its_bases() -> None:
    with pytest.raises(ValidationError, match="derive from the literal bases"):
        BasalPairRecord(
            profile_position=0,
            source_index=0,
            adapter_index=0,
            source_base="A",
            adapter_base="T",
            pair_class=BasalPairClass.WOBBLE,
            compact_symbol="W",
        )


def test_authored_pairing_constraints_do_not_accept_realized_literal_bases() -> None:
    with pytest.raises(ValidationError):
        BasalPairingConstraint.model_validate(
            {
                "profile_position": 0,
                "allowed_class": "match",
                "source_base": "A",
                "adapter_base": "T",
            }
        )


def test_direct_and_pcr_endpoints_have_distinct_material_obligations() -> None:
    direct = discover_basal_neighborhood(_request(ConstructionEndpoint.SSDNA_HAIRPIN))
    pcr = discover_basal_neighborhood(_request(ConstructionEndpoint.HAIRPIN_PCR_DUPLEX))

    assert direct.discovery.status == "complete"
    assert direct.realizations[0].projection.pairing_profile is None
    assert direct.realizations[0].projection.pcr_reference_sequence is None
    assert direct.realizations[0].projection.cohesive_ends == ()
    assert direct.realizations[0].adapter_annealed_complex is None
    assert direct.realizations[0].adapter_ligated_product is None
    assert direct.realizations[0].hairpin_pcr_duplex is None
    assert direct.realizations[0].restriction_digest_product is None

    projection = pcr.realizations[0].projection
    assert projection.pairing_profile is not None
    assert projection.pairing_profile.pairs[0].pair_class is BasalPairClass.MATCH
    assert projection.pairing_profile.adapter_span == Span(
        start=Boundary(offset=0),
        end=Boundary(offset=4),
    )
    assert projection.pcr_reference_sequence is not None
    assert projection.pcr_complement_sequence is not None
    assert projection.pcr_complement_sequence == reverse_complement_iupac(
        projection.pcr_reference_sequence
    )
    assert projection.cohesive_ends == ()
    assert pcr.realizations[0].restriction_digest_product is None


def test_proximal_mismatch_is_rejected_but_distal_mismatch_is_copied_exactly() -> None:
    with pytest.raises(ValidationError, match="payload-proximal basal pair must be a match"):
        BasalTarget(
            nick_strand=Strand.TOP,
            nick_offset_nt=0,
            pairing_constraints=(
                BasalPairingConstraint(
                    profile_position=0,
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

    assert distal.discovery.status == "complete"
    profile = distal.realizations[0].projection.pairing_profile
    assert profile is not None
    assert profile.pairs[2].pair_class is BasalPairClass.MISMATCH
    assert distal.realizations[0].projection.pcr_reference_sequence is not None
    assert distal.realizations[0].projection.pcr_complement_sequence == reverse_complement_iupac(
        distal.realizations[0].projection.pcr_reference_sequence
    )


def test_realization_contains_exact_route_evidence_and_payload_conditioning() -> None:
    record = discover_basal_neighborhood(
        _request(ConstructionEndpoint.CLONE_READY_DUPLEX)
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
    assert record.restriction_digest_product is not None
    assert record.material_accounting.retained_nt > 0
    assert record.material_accounting.transient_nt > 0
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


def test_basal_result_enforces_its_own_program_operation_limit() -> None:
    result = discover_basal_neighborhood(
        _request(ConstructionEndpoint.CLONE_READY_DUPLEX, max_operations=3)
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

    with pytest.raises(ValidationError, match="operation limit"):
        BasalNeighborhoodDiscoveryResult.create(
            discovery=discovery,
            realizations=result.realizations,
        )


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

    assert result.discovery.status == "infeasible"
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
    shell = result.discovery.shells[0]
    corrupted_shell = shell.model_copy(update={"candidate_count": shell.candidate_count + 1})
    corrupted_discovery = result.discovery.model_copy(update={"shells": (corrupted_shell,)})

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

    assert result.discovery.status == "complete"
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
    assert blocked.discovery.status == "infeasible"
    assert blocked.realizations == ()
    assert all(not shell.realization_ids for shell in blocked.discovery.shells)
    assert all(shell.complete for shell in blocked.discovery.shells)
    assert all(
        shell.candidate_count == shell.rejected_count
        and sum(reason.count for reason in shell.failure_reasons) == shell.rejected_count
        for shell in blocked.discovery.shells
    )
    assert any(
        reason.code == "all-members-compatibility-required"
        for shell in blocked.discovery.shells
        for reason in shell.failure_reasons
    )


def test_basal_degenerate_payload_over_bound_is_truthfully_uncomputed() -> None:
    result = discover_basal_neighborhood(
        _request(
            ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
            payload=DegeneratePayload(sequence="NNNN"),
            max_nodes=1,
        )
    )

    assert result.discovery.status == "truncated"
    assert result.discovery.payload_compatibility.status == "not_computed"
    assert result.discovery.payload_compatibility.total_assignments == 256
    assert result.discovery.payload_compatibility.warning


def test_any_nick_strand_enumerates_both_exact_strands_deterministically() -> None:
    request = _request(
        ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
        payload=DegeneratePayload(sequence="YTCC"),
    )
    request = request.model_copy(
        update={"target": request.target.model_copy(update={"nick_strand": BasalNickStrand.ANY})}
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
    assert isinstance(request.target, BasalTarget)
    exact_target = request.target
    any_target = exact_target.model_copy(update={"nick_strand": BasalNickStrand.ANY})
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


def test_nick_offset_and_strand_change_exact_binding_geometry() -> None:
    base = discover_basal_neighborhood(
        _request(ConstructionEndpoint.HAIRPIN_PCR_DUPLEX)
    ).realizations[0]
    offset = discover_basal_neighborhood(
        _request(
            ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
            relaxation=RelaxationPolicy(
                mode=RelaxationMode.THROUGH_RADIUS,
                max_radius=1,
                coordinates=(RelaxationCoordinate(name="nick_offset_nt", minimum=0, maximum=1),),
            ),
        )
    ).realizations[-1]
    bottom_request = _request(ConstructionEndpoint.HAIRPIN_PCR_DUPLEX, payload="TTCC")
    bottom_request = bottom_request.model_copy(
        update={"target": bottom_request.target.model_copy(update={"nick_strand": Strand.BOTTOM})}
    )
    bottom = discover_basal_neighborhood(bottom_request).realizations[0]

    assert base.basal_nick.boundary != offset.basal_nick.boundary
    assert base.basal_nick.binding_id != offset.basal_nick.binding_id
    assert base.basal_nick.strand is Strand.TOP
    assert bottom.basal_nick.strand is Strand.BOTTOM
    assert base.basal_nick.binding_id != bottom.basal_nick.binding_id


def test_clone_ready_derives_exact_ends_and_filters_requested_overhangs() -> None:
    discovered = discover_basal_neighborhood(_request(ConstructionEndpoint.CLONE_READY_DUPLEX))

    assert discovered.discovery.status == "complete"
    projection = discovered.realizations[0].projection
    assert tuple(end.product_end for end in projection.cohesive_ends) == ("left", "right")
    record = discovered.realizations[0]
    end_bindings = tuple(
        binding for binding in record.enzyme_bindings if binding.role is EnzymeRole.END_GENERATION
    )
    assert tuple(end.primary_cut for end in projection.cohesive_ends) == tuple(
        binding.reference_cut for binding in end_bindings
    )

    exact_ends = tuple(end.sequence for end in projection.cohesive_ends)
    constrained = discover_basal_neighborhood(
        _request(
            ConstructionEndpoint.CLONE_READY_DUPLEX,
            requested_overhangs=exact_ends,
        )
    )
    impossible = discover_basal_neighborhood(
        _request(
            ConstructionEndpoint.CLONE_READY_DUPLEX,
            requested_overhangs=("AA",),
        )
    )
    assert constrained.discovery.status == "complete"
    assert impossible.discovery.status == "infeasible"
    assert impossible.realizations == ()


def test_clone_ready_enumerates_every_exact_allowed_degenerate_recognition_assignment() -> None:
    result = discover_basal_neighborhood(
        _request(
            ConstructionEndpoint.CLONE_READY_DUPLEX,
            type_iis_pattern="YGTCTC",
        )
    )

    assert result.discovery.status == "complete"
    forward_first_bases = {
        record.hairpin_pcr_duplex.top_strand.sequence[binding.recognition_span.start.offset]
        for record in result.realizations
        for binding in record.enzyme_bindings
        if binding.role is EnzymeRole.END_GENERATION and binding.orientation.value == "forward"
    }
    reverse_last_bases = {
        record.hairpin_pcr_duplex.top_strand.sequence[binding.recognition_span.end.offset - 1]
        for record in result.realizations
        for binding in record.enzyme_bindings
        if binding.role is EnzymeRole.END_GENERATION and binding.orientation.value == "reverse"
    }
    assert forward_first_bases == {"C", "T"}
    assert reverse_last_bases == {"A", "G"}
    assert len({record.source_precursor_sequence for record in result.realizations}) > 1


def test_clone_ready_relaxed_cut_offset_changes_placement_and_exact_ends() -> None:
    result = discover_basal_neighborhood(
        _request(
            ConstructionEndpoint.CLONE_READY_DUPLEX,
            type_iis_cut_offset_nt=1,
        )
    )

    assert result.discovery.status == "complete"
    exact = discover_basal_neighborhood(
        _request(ConstructionEndpoint.CLONE_READY_DUPLEX)
    ).realizations[0]
    relaxed = result.realizations[0]
    assert tuple(binding.recognition_span for binding in exact.enzyme_bindings[1:]) != tuple(
        binding.recognition_span for binding in relaxed.enzyme_bindings[1:]
    )
    assert tuple(end.sequence for end in exact.projection.cohesive_ends) != tuple(
        end.sequence for end in relaxed.projection.cohesive_ends
    )


def test_clone_ready_counts_nick_and_both_type_iis_operations() -> None:
    result = discover_basal_neighborhood(
        _request(ConstructionEndpoint.CLONE_READY_DUPLEX, max_operations=2)
    )

    assert result.discovery.status == "infeasible"
    assert "operation-limit" in {reason.code for reason in result.discovery.failure_reasons}
    assert all(
        shell.candidate_count == len(shell.realization_ids) + shell.rejected_count
        and sum(reason.count for reason in shell.failure_reasons) == shell.rejected_count
        for shell in result.discovery.shells
    )


def test_payload_and_boundary_sites_are_scanned_in_the_exact_precursor() -> None:
    result = discover_basal_neighborhood(
        _request(ConstructionEndpoint.HAIRPIN_PCR_DUPLEX, payload="CAAC")
    )

    assert result.discovery.status == "infeasible"
    assert "unintended-actionable-site" in {
        reason.code for reason in result.discovery.failure_reasons
    }


def test_basal_realization_identity_seals_the_exact_endpoint_projection() -> None:
    record = discover_basal_neighborhood(
        _request(ConstructionEndpoint.CLONE_READY_DUPLEX)
    ).realizations[0]

    assert record.basal_realization_id.startswith("hop:basal-realization/")
    changed = record.model_dump(mode="json")
    original_end = changed["projection"]["cohesive_ends"][0]["sequence"]
    replacement = ("C" if original_end[0] == "A" else "A") + original_end[1:]
    changed["projection"]["cohesive_ends"][0]["sequence"] = replacement
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
        _request(ConstructionEndpoint.CLONE_READY_DUPLEX)
    ).realizations[0]
    changed_definition = record.enzyme_definitions[1]
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
    content["enzyme_definitions"] = (
        record.enzyme_definitions[0],
        changed_definition,
    )

    with pytest.raises(ValidationError, match="binding cuts must replay"):
        BasalRealizationRecord.create(**content)


def test_basal_realization_replays_stored_stage_assessments_against_program_operations() -> None:
    record = discover_basal_neighborhood(
        _request(ConstructionEndpoint.CLONE_READY_DUPLEX)
    ).realizations[0]
    assessment = record.stage_assessments[1]
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
    content["stage_assessments"] = (
        record.stage_assessments[0],
        changed_assessment,
    )

    with pytest.raises(ValidationError, match="replay exact binding evidence"):
        BasalRealizationRecord.create(**content)


def test_resealed_program_and_assessment_cannot_reassign_an_embedded_binding() -> None:
    record = discover_basal_neighborhood(
        _request(ConstructionEndpoint.CLONE_READY_DUPLEX)
    ).realizations[0]
    end_program = record.reaction_programs[1]
    stage = end_program.stages[0]
    left_operation, right_operation = stage.operations
    changed_left = left_operation.model_copy(
        update={"intended_binding": right_operation.intended_binding}
    )
    changed_stage = stage.model_copy(update={"operations": (changed_left, right_operation)})
    changed_program = end_program.model_copy(update={"stages": (changed_stage,)})
    assessment = record.stage_assessments[1]
    left_assessment, right_assessment = assessment.intended_bindings
    changed_left_assessment = left_assessment.model_copy(
        update={
            "recognition_span": right_assessment.recognition_span,
            "orientation": right_assessment.orientation,
            "reference_cut": right_assessment.reference_cut,
            "complement_cut": right_assessment.complement_cut,
        }
    )
    changed_assessment = assessment.model_copy(
        update={
            "intended_bindings": (
                changed_left_assessment,
                right_assessment,
            )
        }
    )
    content = {
        name: getattr(record, name)
        for name in BasalRealizationRecord.model_fields
        if name != "basal_realization_id"
    }
    content["reaction_programs"] = (record.reaction_programs[0], changed_program)
    content["stage_assessments"] = (
        record.stage_assessments[0],
        changed_assessment,
    )

    with pytest.raises(ValidationError, match="bijectively"):
        BasalRealizationRecord.create(**content)


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


def test_clone_restriction_strands_serialize_with_exact_parent_spans_and_lineage() -> None:
    record = discover_basal_neighborhood(
        _request(ConstructionEndpoint.CLONE_READY_DUPLEX)
    ).realizations[0]
    assert record.hairpin_pcr_duplex is not None
    assert record.restriction_digest_product is not None
    product = record.restriction_digest_product
    top = record.hairpin_pcr_duplex.top_strand
    bottom = record.hairpin_pcr_duplex.bottom_strand
    complement_start = product.complementary_parent_span.start.offset
    complement_end = product.complementary_parent_span.end.offset

    assert (
        product.primary_strand.sequence
        == top.sequence[
            product.primary_parent_span.start.offset : product.primary_parent_span.end.offset
        ]
    )
    assert product.complementary_strand.sequence == bottom.sequence[complement_start:complement_end]
    assert tuple(item.origin_id for item in product.primary_strand.lineage) == tuple(
        item.origin_id
        for item in top.lineage[
            product.primary_parent_span.start.offset : product.primary_parent_span.end.offset
        ]
    )
    assert tuple(item.origin_id for item in product.complementary_strand.lineage) == tuple(
        item.origin_id for item in bottom.lineage[complement_start:complement_end]
    )
    assert BasalRealizationRecord.model_validate_json(record.model_dump_json()) == record


@pytest.mark.parametrize("strand_name", ("primary_strand", "complementary_strand"))
def test_clone_restriction_strands_reject_resealed_parent_lineage_corruption(
    strand_name: str,
) -> None:
    record = discover_basal_neighborhood(
        _request(ConstructionEndpoint.CLONE_READY_DUPLEX)
    ).realizations[0]
    assert record.restriction_digest_product is not None
    product = record.restriction_digest_product
    strand = getattr(product, strand_name)
    changed_first = strand.lineage[0].model_copy(update={"origin_id": "corrupt-parent"})
    changed_strand = strand.model_copy(update={"lineage": (changed_first, *strand.lineage[1:])})
    changed_product = product.model_copy(update={strand_name: changed_strand})
    content = {
        name: getattr(record, name)
        for name in BasalRealizationRecord.model_fields
        if name != "basal_realization_id"
    }
    content["restriction_digest_product"] = changed_product

    with pytest.raises(ValidationError, match=r"restriction product.*parent"):
        BasalRealizationRecord.create(**content)


def test_endpoint_relative_material_accounting_partitions_retained_and_transient_sequence() -> None:
    direct = discover_basal_neighborhood(_request(ConstructionEndpoint.SSDNA_HAIRPIN)).realizations[
        0
    ]
    pcr = discover_basal_neighborhood(
        _request(ConstructionEndpoint.HAIRPIN_PCR_DUPLEX)
    ).realizations[0]
    clone = discover_basal_neighborhood(
        _request(ConstructionEndpoint.CLONE_READY_DUPLEX)
    ).realizations[0]

    direct_retained = next(item for item in direct.materials if item.role.value == "retained")
    assert direct_retained.sequence_5prime == direct.source_precursor_sequence
    assert direct.material_accounting.transient_nt == 0

    pcr_retained = next(item for item in pcr.materials if item.role.value == "retained")
    assert pcr.hairpin_pcr_duplex is not None
    assert pcr_retained.sequence_5prime == pcr.hairpin_pcr_duplex.top_strand.sequence
    assert pcr.material_accounting.transient_nt == 0

    clone_retained = next(item for item in clone.materials if item.role.value == "retained")
    clone_transient = next(item for item in clone.materials if item.role.value == "transient")
    assert clone.hairpin_pcr_duplex is not None
    assert clone.restriction_digest_product is not None
    assert (
        clone_retained.sequence_5prime == clone.restriction_digest_product.primary_strand.sequence
    )
    assert len(clone_retained.sequence_5prime) + len(clone_transient.sequence_5prime) == len(
        clone.hairpin_pcr_duplex.top_strand.sequence
    )


def test_resealed_material_accounting_rejects_overlapping_clone_retained_and_transient_bases() -> (
    None
):
    record = discover_basal_neighborhood(
        _request(ConstructionEndpoint.CLONE_READY_DUPLEX)
    ).realizations[0]
    assert record.hairpin_pcr_duplex is not None
    changed_materials = tuple(
        BasalMaterialRecord(
            material_id=item.material_id,
            role=item.role,
            sequence_5prime=(
                record.hairpin_pcr_duplex.top_strand.sequence
                if item.role is BasalMaterialRole.TRANSIENT
                else item.sequence_5prime
            ),
        )
        for item in record.materials
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

    with pytest.raises(ValidationError, match="retained and transient partition"):
        BasalRealizationRecord.create(**content)


def test_relaxation_status_and_geometry_groups_are_exact_first_and_lossless() -> None:
    relaxation = RelaxationPolicy(
        mode=RelaxationMode.THROUGH_RADIUS,
        max_radius=1,
        coordinates=(RelaxationCoordinate(name="nick_offset_nt", minimum=0, maximum=1),),
    )
    complete = discover_basal_neighborhood(
        _request(
            ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
            relaxation=relaxation,
            extra_nickase=True,
        )
    )
    truncated = discover_basal_neighborhood(
        _request(
            ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
            relaxation=relaxation,
            extra_nickase=True,
            max_nodes=1,
        )
    )

    assert complete.discovery.status == "complete"
    assert [shell.radius for shell in complete.discovery.shells] == [0, 1]
    ids = {item.local_realization.local_realization_id for item in complete.realizations}
    grouped_ids = {
        realization_id
        for group in complete.discovery.achieved_geometry_groups
        for realization_id in group.realization_ids
    }
    assert grouped_ids == ids
    assert len(ids) == len(complete.realizations)
    assert len(ids) > 4
    assert truncated.discovery.status == "truncated"
    assert truncated.discovery.truncation_reasons == ("max_search_nodes",)
    assert truncated.discovery.shells[-1].complete is False
    assert all(shell.candidate_count > 0 for shell in truncated.discovery.shells)
    assert all(
        shell.candidate_count == len(shell.realization_ids) + shell.rejected_count
        and sum(reason.count for reason in shell.failure_reasons) == shell.rejected_count
        for shell in truncated.discovery.shells
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


def test_basal_bounds_at_a_shell_boundary_do_not_emit_an_unentered_shell() -> None:
    exact = discover_basal_neighborhood(_request(ConstructionEndpoint.SSDNA_HAIRPIN))
    shell = exact.discovery.shells[0]
    relaxation = RelaxationPolicy(
        mode=RelaxationMode.THROUGH_RADIUS,
        max_radius=1,
        coordinates=(RelaxationCoordinate(name="nick_offset_nt", minimum=0, maximum=1),),
    )

    for limits in (
        {"max_nodes": shell.candidate_count, "max_realizations": 100},
        {"max_nodes": 100, "max_realizations": len(shell.realization_ids)},
    ):
        result = discover_basal_neighborhood(
            _request(
                ConstructionEndpoint.SSDNA_HAIRPIN,
                relaxation=relaxation,
                **limits,
            )
        )

        assert result.discovery.status == "truncated"
        assert tuple(item.radius for item in result.discovery.shells) == (0,)
        assert result.discovery.shells[0].complete is True


def test_exact_basal_domain_is_complete_when_a_bound_equals_exhaustive_count() -> None:
    exhaustive = discover_basal_neighborhood(
        _request(
            ConstructionEndpoint.SSDNA_HAIRPIN,
            max_nodes=10_000,
            max_realizations=10_000,
        )
    )
    examined = sum(shell.candidate_count for shell in exhaustive.discovery.shells)
    realized = len(exhaustive.realizations)

    node_bounded = discover_basal_neighborhood(
        _request(
            ConstructionEndpoint.SSDNA_HAIRPIN,
            max_nodes=examined,
            max_realizations=10_000,
        )
    )
    realization_bounded = discover_basal_neighborhood(
        _request(
            ConstructionEndpoint.SSDNA_HAIRPIN,
            max_nodes=10_000,
            max_realizations=realized,
        )
    )

    assert node_bounded.discovery.status is SearchCompletionStatus.COMPLETE
    assert realization_bounded.discovery.status is SearchCompletionStatus.COMPLETE


def test_basal_verification_rejects_self_asserted_execution_environment() -> None:
    raw = discover_basal_neighborhood(_request(ConstructionEndpoint.SSDNA_HAIRPIN))
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


def test_basal_wrapper_rejects_partial_final_shell_resealed_as_complete() -> None:
    result = discover_basal_neighborhood(
        _request(
            ConstructionEndpoint.SSDNA_HAIRPIN,
            max_nodes=1,
            max_realizations=100,
        )
    )
    shell = result.discovery.shells[-1]
    assert shell.complete is False
    corrupted_shell = shell.model_copy(update={"complete": True})
    corrupted_discovery = result.discovery.model_copy(
        update={"shells": (*result.discovery.shells[:-1], corrupted_shell)}
    )

    with pytest.raises(ValidationError, match="unentered later shell"):
        BasalNeighborhoodDiscoveryResult.create(
            discovery=corrupted_discovery,
            realizations=result.realizations,
        )


def test_type_iis_cut_offset_participates_in_exact_first_relaxation() -> None:
    result = discover_basal_neighborhood(
        _request(
            ConstructionEndpoint.CLONE_READY_DUPLEX,
            relaxation=RelaxationPolicy(
                mode=RelaxationMode.THROUGH_RADIUS,
                max_radius=1,
                coordinates=(
                    RelaxationCoordinate(
                        name="end_generation.type_iis_cut_offset_nt",
                        minimum=0,
                        maximum=1,
                    ),
                ),
            ),
        )
    )

    assert result.discovery.status == "complete"
    assert [shell.radius for shell in result.discovery.shells] == [0, 1]
    assert {
        record.local_realization.achieved_geometry.end_generation.type_iis_cut_offset_nt
        for record in result.realizations
    } == {0, 1}
    shell_ends = {
        radius: {
            tuple(end.sequence for end in record.projection.cohesive_ends)
            for record in result.realizations
            if record.relaxation_radius == radius
        }
        for radius in (0, 1)
    }
    assert shell_ends[0] != shell_ends[1]
