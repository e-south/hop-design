"""
--------------------------------------------------------------------------------
HOP Design
tests/integration/test_complete_construction_discovery.py

Tests exact whole-route composition against verified local and design authorities.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from pydantic import ValidationError

import hop_design as hop
from hop_design.design.bundle import load_verified_bundle
from hop_design.design.construction.basal import discover_basal_neighborhood
from hop_design.design.construction.complete import discover_constructions
from hop_design.design.construction.complete.direct import direct_realization
from hop_design.design.construction.complete.discovery import (
    VerifiedConstructionSpaceResult,
    verify_construction_space_result,
)
from hop_design.design.construction.complete.lineage import (
    final_hairpin_strand,
    foldback_occurrences,
    whole_source_occurrences,
)
from hop_design.design.construction.foldback import discover_foldback_neighborhood
from hop_design.design.construction.verification import (
    ConstructionVerificationError,
    VerifiedFoldbackNeighborhoodResult,
    verify_basal_neighborhood_result,
    verify_foldback_neighborhood_result,
)
from hop_design.models.construction import (
    BasalPairAllowance,
    BasalPairingConstraint,
    BasalTarget,
    CompleteConstructionRealization,
    ConstructionConstraints,
    ConstructionEndpoint,
    EnumerationPolicy,
    FinalPayloadReference,
    FoldbackTarget,
    LocalNeighborhoodFamily,
    LocalNeighborhoodRequest,
    MethodResolutionStatus,
    PayloadSourceMap,
    PayloadSourceSegment,
    RelaxationCoordinate,
    RelaxationMode,
    RelaxationPolicy,
    RouteFamily,
    SearchCompletionStatus,
    SourceOrientation,
)
from hop_design.models.construction.complete import (
    CompositionAccounting,
    CompositionDispositionStatus,
    CompositionEnumerationPolicy,
    CompositionPruningMode,
    ConstructionDiscoveryRequest,
    ConstructionProgram,
    ConstructionState,
    ConstructionTransition,
    DesignAuthorityReference,
    ExactConstructionMaterial,
    ExactStateRelation,
    LinearSourceMaterializationSpec,
    MaterializedConstructionRealization,
    MaterializedFinalProduct,
    MaterialOrigin,
    ReactionBoundaryMapping,
    WholeRouteConstraints,
)
from hop_design.models.construction.complete.evaluation import (
    CompositionRejectionCode,
    evaluate_combination,
)
from hop_design.models.construction.complete.materials import validate_initial_material_state
from hop_design.models.construction.complete.validation import (
    validate_accepted_realization,
    validate_payload_source_map,
)
from hop_design.models.construction.payload import _content_id
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
)
from hop_design.models.junction import Strand
from hop_design.models.molecular_state import EndChemistry
from hop_design.models.payload import DegeneratePayload, ExactPayload
from hop_design.models.references import ExternalRef
from tests.contract.test_foldback_construction_discovery import (
    _nickase,
    _request,
    _terminus_enzyme,
)
from tests.integration.test_resolved_compile import _component_spec


def _basal_result(
    payload: FinalPayloadReference,
    endpoint: ConstructionEndpoint = ConstructionEndpoint.SSDNA_HAIRPIN,
    nick_strand: Strand = Strand.TOP,
    nick_offset_nt: int = 0,
    pairing_allowances: tuple[BasalPairAllowance, ...] | None = None,
    recognition_pattern: str | None = None,
    cut_offset_reference_strand: int | None = None,
):
    enzyme = CharacterizedEnzyme(
        enzyme_id="example:enzyme/complete-basal@1",
        canonical_name="complete-basal",
        enzyme_class=EnzymeClass.NICKASE,
        target_molecule=TargetMolecule.DNA,
        recognition_pattern=(
            recognition_pattern or ("TTTT" if nick_strand is Strand.BOTTOM else "AAAA")
        ),
        recognition_orientation_semantics=(
            RecognitionOrientationSemantics.BOTH_ORIENTATIONS
            if nick_strand is Strand.BOTTOM
            else RecognitionOrientationSemantics.DECLARED_ONLY
        ),
        recognition_length=4,
        substrate_requirement=SubstrateRequirement.DUPLEX_DNA,
        cut_offset_reference_strand=(
            cut_offset_reference_strand
            if cut_offset_reference_strand is not None
            else (0 if nick_strand is Strand.BOTTOM else 4)
        ),
        cut_offset_complement_strand=None,
        resulting_end_model=ResultingEndModel.NICK,
        characterization_source=ExternalRef(
            system="literature",
            kind="synthetic-characterization-fixture",
            id="complete-basal",
        ),
    )
    provisioning = EnzymeProvisioningPolicy(
        catalog=CharacterizedEnzymeCatalog(
            catalog_id="example:enzyme-catalog/complete-basal@1",
            enzymes=(enzyme,),
        ),
        allowed_enzyme_ids=(enzyme.enzyme_id,),
        forbidden_enzyme_ids=(),
        reserved_enzyme_ids=(),
        max_operations=2,
        role_restrictions=(
            EnzymeRoleRestriction(
                role=EnzymeRole.BASAL_NICK,
                allowed_enzyme_ids=(enzyme.enzyme_id,),
            ),
        ),
    )
    return discover_basal_neighborhood(
        LocalNeighborhoodRequest(
            payload=payload,
            family=LocalNeighborhoodFamily.BASAL,
            route_family=RouteFamily.LINEAR_SOURCE_V1,
            endpoint=endpoint,
            target=BasalTarget(
                nick_strand=nick_strand,
                nick_offset_nt=nick_offset_nt,
                pairing_constraints=(
                    ()
                    if endpoint is ConstructionEndpoint.SSDNA_HAIRPIN
                    else tuple(
                        BasalPairingConstraint(
                            profile_position=index,
                            allowed_class=allowed,
                        )
                        for index, allowed in enumerate(
                            pairing_allowances or (BasalPairAllowance.MATCH,) * 4
                        )
                    )
                ),
                ligation_proximal_match_required=(
                    endpoint is ConstructionEndpoint.HAIRPIN_PCR_DUPLEX
                ),
            ),
            hard_constraints=ConstructionConstraints(),
            enzyme_provisioning=provisioning,
            relaxation=RelaxationPolicy(mode=RelaxationMode.EXACT_ONLY, max_radius=0),
            enumeration=EnumerationPolicy(max_search_nodes=100, max_realizations=100),
        )
    )


def _material(material_id: str, sequence: str) -> ExactConstructionMaterial:
    return ExactConstructionMaterial(
        material_id=material_id,
        origin=MaterialOrigin.SYNTHESIZED,
        sequence_5prime=sequence,
        five_prime_end=EndChemistry.PHOSPHATE,
        three_prime_end=EndChemistry.HYDROXYL,
    )


def _verified_design(tmp_path: Path, payload: str = "GACA"):
    spec = _component_spec().model_copy(update={"payload": ExactPayload(sequence=payload)})
    return load_verified_bundle(hop.compile(spec).write(tmp_path / "design"))


def _construction_request(
    *,
    payload: FinalPayloadReference,
    foldback,
    basal,
    design,
    complement_five_prime_end: EndChemistry = EndChemistry.PHOSPHATE,
    require_all: bool = False,
    endpoint: ConstructionEndpoint = ConstructionEndpoint.SSDNA_HAIRPIN,
    adapter: ExactConstructionMaterial | None = None,
    forward_primer: ExactConstructionMaterial | None = None,
    reverse_primer: ExactConstructionMaterial | None = None,
) -> ConstructionDiscoveryRequest:
    encoding = design.plan.hairpin_encoding_insert
    return ConstructionDiscoveryRequest(
        payload=payload,
        route_family=RouteFamily.LINEAR_SOURCE_V1,
        endpoint=endpoint,
        foldback_result_id=foldback.result_id,
        basal_result_id=None if basal is None else basal.result_id,
        materialization=LinearSourceMaterializationSpec(
            source_origin=MaterialOrigin.SYNTHESIZED,
            source_five_prime_end=EndChemistry.HYDROXYL,
            source_three_prime_end=EndChemistry.HYDROXYL,
            source_complement_origin=MaterialOrigin.SYNTHESIZED,
            source_complement_five_prime_end=complement_five_prime_end,
            source_complement_three_prime_end=EndChemistry.HYDROXYL,
            adapter=adapter,
            forward_primer=forward_primer,
            reverse_primer=reverse_primer,
        ),
        design=DesignAuthorityReference(
            bundle=design.bundle,
            spec=design.spec,
            plan=design.plan,
            plan_id=design.plan.plan_id,
            design_id=design.plan.design_id,
            payload_sequence=payload.payload.sequence,
            encoding_sequence=encoding.sequence,
            encoding_digest=encoding.sequence_digest,
        ),
        whole_route_constraints=WholeRouteConstraints(require_all_combinations_valid=require_all),
        enumeration=CompositionEnumerationPolicy(
            pruning=CompositionPruningMode.DISABLED,
            max_combinations=100,
            max_realizations=100,
        ),
    )


def _discover_raw(request, *, foldback, basal, design):
    return discover_constructions(
        request,
        foldback=verify_foldback_neighborhood_result(foldback),
        basal=None if basal is None else verify_basal_neighborhood_result(basal),
        design=design,
    ).result


def test_complete_composition_filters_a_multi_payload_local_authority(
    tmp_path: Path,
) -> None:
    local_request = _request(
        _nickase(
            motif="AAA",
            orientation_semantics=RecognitionOrientationSemantics.DECLARED_ONLY,
        ),
        relaxation=RelaxationPolicy(
            mode=RelaxationMode.FIRST_FEASIBLE_SHELL,
            max_radius=1,
            coordinates=(
                RelaxationCoordinate(
                    name="nick_offset_within_foldback_nt",
                    minimum=0,
                    maximum=1,
                ),
            ),
        ),
        max_search_nodes=1000,
        max_realizations=1000,
    )
    local_data = local_request.model_dump(mode="python")
    local_data["payload"]["payload"] = DegeneratePayload(sequence="GACW")
    local_data["hard_constraints"]["require_all_members_compatible"] = True
    foldback = discover_foldback_neighborhood(LocalNeighborhoodRequest.model_validate(local_data))
    assert {item.payload_sequence for item in foldback.realizations} == {"GACA", "GACT"}

    design = _verified_design(tmp_path, payload="GACA")
    payload = FinalPayloadReference(
        payload=ExactPayload(sequence="GACA"),
        basal_boundary=Boundary(offset=0),
        foldback_boundary=Boundary(offset=4),
    )
    request = ConstructionDiscoveryRequest(
        payload=payload,
        route_family=RouteFamily.LINEAR_SOURCE_V1,
        endpoint=ConstructionEndpoint.SSDNA_HAIRPIN,
        foldback_result_id=foldback.result_id,
        materialization=LinearSourceMaterializationSpec(
            source_origin=MaterialOrigin.SYNTHESIZED,
            source_five_prime_end=EndChemistry.HYDROXYL,
            source_three_prime_end=EndChemistry.HYDROXYL,
            source_complement_origin=MaterialOrigin.SYNTHESIZED,
            source_complement_five_prime_end=EndChemistry.PHOSPHATE,
            source_complement_three_prime_end=EndChemistry.HYDROXYL,
        ),
        design=DesignAuthorityReference(
            bundle=design.bundle,
            spec=design.spec,
            plan=design.plan,
            plan_id=design.plan.plan_id,
            design_id=design.plan.design_id,
            payload_sequence="GACA",
            encoding_sequence=design.plan.hairpin_encoding_insert.sequence,
            encoding_digest=design.plan.hairpin_encoding_insert.sequence_digest,
        ),
        whole_route_constraints=WholeRouteConstraints(),
        enumeration=CompositionEnumerationPolicy(
            max_combinations=100,
            max_realizations=100,
        ),
    )

    with pytest.raises(TypeError, match="verified local construction authorities"):
        discover_constructions(
            request,
            foldback=foldback,  # type: ignore[arg-type]
            basal=None,
            design=design,
        )

    verified_foldback = verify_foldback_neighborhood_result(foldback)
    forged_foldback = object.__new__(VerifiedFoldbackNeighborhoodResult)
    object.__setattr__(
        forged_foldback,
        "result",
        foldback.model_copy(
            update={
                "neighborhood": foldback.neighborhood.model_copy(
                    update={"projection_inventory": ()}
                )
            }
        ),
    )
    with pytest.raises(ConstructionVerificationError, match="deterministic discovery replay"):
        discover_constructions(
            request,
            foldback=forged_foldback,
            basal=None,
            design=design,
        )
    result = discover_constructions(
        request,
        foldback=verified_foldback,
        basal=None,
        design=design,
    )

    assert isinstance(result, VerifiedConstructionSpaceResult)
    raw_result = result.result
    assert raw_result.provenance.foldback_realization_ids == tuple(
        item.foldback_realization_id
        for item in foldback.realizations
        if item.payload_sequence == "GACA"
    )
    assert raw_result.accounting.nominal_combinations == len(
        raw_result.provenance.foldback_realization_ids
    )
    with pytest.raises(ValueError, match="deterministic composition replay"):
        verify_construction_space_result(
            raw_result.model_copy(update={"projection_inventory": ()}),
            foldback=verified_foldback,
            basal=None,
            design=design,
        )
    with pytest.raises(ValueError, match="deterministic composition replay"):
        VerifiedConstructionSpaceResult(
            result=raw_result.model_copy(update={"projection_inventory": ()}),
            foldback=verified_foldback,
            basal=None,
            design=design,
        )


def test_direct_composition_materializes_complete_precursor_and_verified_encoding(
    tmp_path: Path,
) -> None:
    payload = FinalPayloadReference(
        payload=ExactPayload(sequence="GACA"),
        basal_boundary=Boundary(offset=0),
        foldback_boundary=Boundary(offset=4),
    )
    foldback = discover_foldback_neighborhood(
        _request(
            _nickase(
                motif="TCAGATGCTGA",
                cut_offset=0,
                orientation_semantics=RecognitionOrientationSemantics.DECLARED_ONLY,
            ),
            _terminus_enzyme(),
            target=FoldbackTarget(
                nick_offset_within_foldback_nt=0,
                loop_length_nt=3,
                annealing_arm_length_bp=4,
            ),
        )
    )
    basal = _basal_result(payload)
    design = _verified_design(tmp_path)
    precursor = "AAAA" + foldback.realizations[0].source_reference_sequence
    encoding = design.plan.hairpin_encoding_insert
    request = ConstructionDiscoveryRequest(
        payload=payload,
        route_family=RouteFamily.LINEAR_SOURCE_V1,
        endpoint=ConstructionEndpoint.SSDNA_HAIRPIN,
        foldback_result_id=foldback.result_id,
        basal_result_id=basal.result_id,
        materialization=LinearSourceMaterializationSpec(
            source_origin=MaterialOrigin.SYNTHESIZED,
            source_five_prime_end=EndChemistry.HYDROXYL,
            source_three_prime_end=EndChemistry.HYDROXYL,
            source_complement_origin=MaterialOrigin.SYNTHESIZED,
            source_complement_five_prime_end=EndChemistry.PHOSPHATE,
            source_complement_three_prime_end=EndChemistry.HYDROXYL,
        ),
        design=DesignAuthorityReference(
            bundle=design.bundle,
            spec=design.spec,
            plan=design.plan,
            plan_id=design.plan.plan_id,
            design_id=design.plan.design_id,
            payload_sequence="GACA",
            encoding_sequence=encoding.sequence,
            encoding_digest=encoding.sequence_digest,
        ),
        whole_route_constraints=WholeRouteConstraints(),
        enumeration=CompositionEnumerationPolicy(
            pruning=CompositionPruningMode.DISABLED,
            max_combinations=10,
            max_realizations=10,
        ),
    )

    result = _discover_raw(
        request,
        foldback=foldback,
        basal=basal,
        design=design,
    )
    sequential = next(
        item for item in foldback.realizations if len(item.reaction_program.stages) > 1
    )
    limited = evaluate_combination(
        request,
        foldback=sequential,
        basal=None,
        foldback_policy=foldback.neighborhood.request.enzyme_provisioning.model_copy(
            update={"max_operations": 1}
        ),
        basal_policy=None,
    )
    assert limited.rejection_reason is CompositionRejectionCode.GLOBAL_ACTIONABLE_SITE_CONFLICT
    basal_policy = basal.discovery.request.enzyme_provisioning
    basal_enzyme_id = basal_policy.catalog.enzymes[0].enzyme_id
    conflicting_policy = basal_policy.model_copy(
        update={
            "role_restrictions": (
                *basal_policy.role_restrictions,
                EnzymeRoleRestriction(
                    role=EnzymeRole.FOLDBACK_NICK,
                    allowed_enzyme_ids=(basal_enzyme_id,),
                ),
            )
        }
    )
    with pytest.raises(ValueError, match="conflicting role restrictions"):
        evaluate_combination(
            request,
            foldback=foldback.realizations[0],
            basal=basal.realizations[0],
            foldback_policy=foldback.neighborhood.request.enzyme_provisioning,
            basal_policy=conflicting_policy,
        )

    design_prefix = precursor[:4]
    basal_record = basal.realizations[0]
    incompatible_segment = basal_record.payload_source_map.segments[0].model_copy(
        update={"orientation": SourceOrientation.REVERSE_COMPLEMENT}
    )
    incompatible_basal = basal_record.model_copy(
        update={
            "payload_source_map": basal_record.payload_source_map.model_copy(
                update={"segments": (incompatible_segment,)}
            )
        }
    )
    assert (
        direct_realization(
            request,
            foldback=foldback.realizations[0],
            basal=incompatible_basal,
            foldback_result=foldback,
            basal_result=basal,
        )
        == "basal-source-map-incompatible"
    )
    hydroxyl_source_request = request.model_copy(
        update={
            "materialization": request.materialization.model_copy(
                update={"source_complement_five_prime_end": EndChemistry.HYDROXYL}
            )
        }
    )
    assert (
        direct_realization(
            hydroxyl_source_request,
            foldback=foldback.realizations[0],
            basal=basal_record,
            foldback_result=foldback,
            basal_result=basal,
        )
        == "source-end-chemistry-mismatch"
    )
    partially_compatible = _discover_raw(
        hydroxyl_source_request,
        foldback=foldback,
        basal=basal,
        design=design,
    )
    assert partially_compatible.status is SearchCompletionStatus.COMPLETE
    assert tuple(item.status for item in partially_compatible.combination_dispositions) == (
        CompositionDispositionStatus.REJECTED,
        CompositionDispositionStatus.ACCEPTED,
    )
    changed_reason = partially_compatible.combination_dispositions[0].model_copy(
        update={"rejection_reason": CompositionRejectionCode.GLOBAL_ACTIONABLE_SITE_CONFLICT}
    )
    with pytest.raises(ValidationError, match="reason must equal exact combination evaluation"):
        type(partially_compatible).model_validate(
            partially_compatible.model_dump(mode="python")
            | {
                "combination_dispositions": (
                    changed_reason,
                    partially_compatible.combination_dispositions[1],
                ),
                "failure_reasons": (
                    {
                        "code": CompositionRejectionCode.GLOBAL_ACTIONABLE_SITE_CONFLICT,
                        "count": 1,
                    },
                ),
            }
        )
    require_all_request = hydroxyl_source_request.model_copy(
        update={
            "whole_route_constraints": WholeRouteConstraints(require_all_combinations_valid=True)
        }
    )
    require_all_result = _discover_raw(
        require_all_request,
        foldback=foldback,
        basal=basal,
        design=design,
    )
    assert require_all_result.status is SearchCompletionStatus.INFEASIBLE
    assert require_all_result.realizations == ()
    assert tuple(item.status for item in require_all_result.combination_dispositions) == (
        CompositionDispositionStatus.REJECTED,
        CompositionDispositionStatus.REJECTED,
    )
    assert {item.code for item in require_all_result.failure_reasons} == {
        "all-combinations-valid-required",
        "source-end-chemistry-mismatch",
    }
    wrong_encoding = "A" * len(request.design.encoding_sequence)
    encoding_mismatch_request = request.model_copy(
        update={
            "design": request.design.model_copy(
                update={
                    "encoding_sequence": wrong_encoding,
                    "encoding_digest": "sha256:"
                    + hashlib.sha256(wrong_encoding.encode()).hexdigest(),
                }
            )
        }
    )
    assert (
        direct_realization(
            encoding_mismatch_request,
            foldback=foldback.realizations[0],
            basal=basal_record,
            foldback_result=foldback,
            basal_result=basal,
        )
        == "design-encoding-mismatch"
    )

    with pytest.raises(ValueError, match="exact verified HOP design bundle"):
        _discover_raw(
            request.model_copy(
                update={
                    "design": request.design.model_copy(
                        update={
                            "bundle": request.design.bundle.model_copy(
                                update={"bundle_id": "fake:bundle/design@1"}
                            )
                        }
                    )
                }
            ),
            foldback=foldback,
            basal=basal,
            design=design,
        )
    with pytest.raises(ValueError, match="Foldback detailed result identity"):
        _discover_raw(
            request.model_copy(
                update={"foldback_result_id": "hop:foldback-neighborhood-result/" + "f" * 64 + "@1"}
            ),
            foldback=foldback,
            basal=basal,
            design=design,
        )
    with pytest.raises(ValueError, match="Basal detailed result identity"):
        _discover_raw(
            request.model_copy(
                update={"basal_result_id": "hop:basal-neighborhood-result/" + "f" * 64 + "@1"}
            ),
            foldback=foldback,
            basal=basal,
            design=design,
        )
    with pytest.raises(ValueError, match="requires one exact basal authority"):
        _discover_raw(
            request.model_copy(
                update={
                    "endpoint": ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
                    "basal_result_id": None,
                }
            ),
            foldback=foldback,
            basal=None,
            design=design,
        )

    assert result.status is SearchCompletionStatus.COMPLETE
    assert result.schema_id == "hop.construction-space-result/v2"
    assert result.model_dump(mode="json")["result_id"] == result.result_id
    assert result.problem_id.startswith("hop:construction-problem/")
    assert result.execution_id.startswith("hop:construction-execution/")
    assert result.provenance.foldback_result_id == foldback.result_id
    assert result.provenance.basal_result_id == basal.result_id
    assert result.provenance.design_bundle_id == design.bundle.bundle_id
    assert result.claim_boundary.method == "resolved_under_declared_molecular_model"
    assert result.material_accounting.source_material_nt == sum(
        len(item.sequence_5prime)
        for realization in result.realizations
        for item in realization.materials[:2]
    )
    assert result.material_accounting.endpoint_product_nt == len(encoding.sequence) * 2
    assert result.accounting.nominal_combinations == 2
    assert result.accounting.pruned_before_execution == 0
    assert result.accounting.executed_combinations == 2
    assert result.accounting.examined_combinations == 2
    assert result.accounting.rejected_after_execution == 0
    assert result.accounting.rejected_combinations == 0
    assert result.accounting.candidate_enzyme_programs == 4
    assert result.accounting.recognition_placements_attempted == 5
    assert result.accounting.constraint_systems_attempted == 6
    for metric in (
        "candidate_enzyme_programs",
        "recognition_placements_attempted",
        "constraint_systems_attempted",
    ):
        changed_metrics = (
            result.combination_dispositions[0].model_copy(
                update={metric: getattr(result.combination_dispositions[0], metric) + 1}
            ),
            result.combination_dispositions[1],
        )
        with pytest.raises(ValidationError, match="combination evaluation"):
            type(result).model_validate(
                result.model_dump(mode="python")
                | {
                    "combination_dispositions": changed_metrics,
                    "accounting": result.accounting.model_copy(
                        update={metric: getattr(result.accounting, metric) + 1}
                    ),
                }
            )
    assert tuple(item.ordinal for item in result.combination_dispositions) == (0, 1)
    assert tuple(item.status for item in result.combination_dispositions) == (
        "accepted",
        "accepted",
    )
    assert result.model_copy(update={"projection_inventory": ()}).result_id == result.result_id
    forged_result = result.model_dump(mode="python")
    forged_result["result_id"] = "hop:construction-space-result/" + "0" * 64 + "@1"
    with pytest.raises(ValidationError, match="result_id"):
        type(result).model_validate(forged_result)
    changed_rejection = result.combination_dispositions[1].model_copy(
        update={"rejection_reason": CompositionRejectionCode.GLOBAL_ACTIONABLE_SITE_CONFLICT}
    )
    changed_result = result.model_copy(
        update={
            "combination_dispositions": (
                result.combination_dispositions[0],
                changed_rejection,
            )
        }
    )
    with pytest.raises(ValidationError, match="fields must match its exact status"):
        type(result).model_validate(changed_result.model_dump(mode="python"))
    renamed_request = request.model_copy(
        update={
            "payload": request.payload.model_copy(update={"display_name": "presentation-only-name"})
        }
    )
    renamed_result = _discover_raw(
        renamed_request,
        foldback=foldback,
        basal=basal,
        design=design,
    )
    assert renamed_result.problem_id == result.problem_id
    assert renamed_result.result_id == result.result_id
    assert result.combination_dispositions[0].materialized_realization_id is not None
    assert result.combination_dispositions[1].rejection_reason is None
    assert result.failure_reasons == ()
    assert len(result.realizations) == 2
    assert len({item.realization.precursor_sequence for item in result.realizations}) == 2
    assert len(result.final_product_groups) == 1
    assert result.final_product_groups[0].multiplicity == 2
    arbitrary_group = result.geometry_groups[0].model_copy(
        update={"group_key": "hop:geometry/" + "a" * 64 + "@1"}
    )
    with pytest.raises(ValidationError, match="replay member semantics"):
        type(result).model_validate(
            result.model_dump(mode="python") | {"geometry_groups": (arbitrary_group,)}
        )
    convergent = result.final_product_groups[0]
    split_groups = (
        convergent.model_copy(
            update={"realization_ids": (convergent.realization_ids[0],), "multiplicity": 1}
        ),
        convergent.model_copy(
            update={"realization_ids": (convergent.realization_ids[1],), "multiplicity": 1}
        ),
    )
    with pytest.raises(ValidationError, match="group keys must be unique"):
        type(result).model_validate(
            result.model_dump(mode="python")
            | {
                "final_product_groups": split_groups,
                "accounting": result.accounting.model_copy(update={"distinct_final_products": 2}),
            }
        )
    realization = result.realizations[0]
    source, source_complement = realization.materials[:2]
    local_foldback = foldback.realizations[0]
    for reaction_state in local_foldback.reaction_program.states:
        occurrences = foldback_occurrences(
            reaction_state.molecules,
            fragments=local_foldback.molecular_fragments,
            prefix_length=len(design_prefix),
            source=source,
            source_complement=source_complement,
        )
        assert tuple(occurrences) == tuple(
            molecule.molecule_id for molecule in reaction_state.molecules
        )
    initial_reaction_state = realization.construction_program.reaction_programs[0].states[0]
    source_occurrences = whole_source_occurrences(
        initial_reaction_state.molecules,
        source=source,
        source_complement=source_complement,
    )
    assert tuple(source_occurrences) == tuple(
        molecule.molecule_id for molecule in initial_reaction_state.molecules
    )

    def resealed_result_with(
        replacement: MaterializedConstructionRealization,
        *,
        foldback_id: str | None = None,
    ) -> dict[str, object]:
        accepted = result.combination_dispositions[0].model_copy(
            update={
                "foldback_realization_id": foldback_id
                or result.combination_dispositions[0].foldback_realization_id,
                "materialized_realization_id": replacement.materialized_realization_id,
            }
        )
        replaced_id = realization.materialized_realization_id
        return result.model_dump(mode="python") | {
            "realizations": (replacement, *result.realizations[1:]),
            "combination_dispositions": (accepted, result.combination_dispositions[1]),
            "geometry_groups": tuple(
                item.model_copy(
                    update={
                        "realization_ids": tuple(
                            replacement.materialized_realization_id
                            if member == replaced_id
                            else member
                            for member in item.realization_ids
                        )
                    }
                )
                for item in result.geometry_groups
            ),
            "final_product_groups": tuple(
                item.model_copy(
                    update={
                        "realization_ids": tuple(
                            replacement.materialized_realization_id
                            if member == replaced_id
                            else member
                            for member in item.realization_ids
                        )
                    }
                )
                for item in result.final_product_groups
            ),
        }

    def resealed_realization(**updates: object) -> MaterializedConstructionRealization:
        content = {
            "realization": realization.realization,
            "foldback_authority": realization.foldback_authority,
            "basal_authority": realization.basal_authority,
            "payload_source_map": realization.payload_source_map,
            "foldback_realization_id": realization.foldback_realization_id,
            "basal_realization_id": realization.basal_realization_id,
            "materials": realization.materials,
            "construction_program": realization.construction_program,
            "final_product": realization.final_product,
            "design": realization.design,
            "geometry_ids": realization.geometry_ids,
            "relaxation_radii": realization.relaxation_radii,
            "claim_boundary": realization.claim_boundary,
        }
        content.update(updates)
        return MaterializedConstructionRealization.create(**content)

    fake_design = realization.design.model_copy(
        update={
            "bundle": realization.design.bundle.model_copy(
                update={"bundle_id": "fake:bundle/design@1"}
            )
        }
    )
    with pytest.raises(ValidationError, match="manifest and root identity"):
        resealed_realization(design=fake_design)

    fake_material = realization.materials[0].model_copy(update={"material_id": "fake-source"})
    with pytest.raises(ValidationError, match="material lineage"):
        resealed_realization(materials=(fake_material, *realization.materials[1:]))

    fake_foldback_id = "hop:foldback-realization/" + "f" * 64 + "@1"
    fake_complete = CompleteConstructionRealization.create(
        precursor_sequence=realization.realization.precursor_sequence,
        local_realization_ids=(realization.basal_realization_id, fake_foldback_id),
        stage_ids=realization.realization.stage_ids,
        final_product_id=realization.realization.final_product_id,
    )
    with pytest.raises(ValidationError, match="embed its exact foldback authority"):
        resealed_realization(
            realization=fake_complete,
            foldback_realization_id=fake_foldback_id,
        )

    changed_materialization = request.materialization.model_copy(
        update={"source_five_prime_end": EndChemistry.PHOSPHATE}
    )
    with pytest.raises(ValidationError, match="problem identity"):
        type(result).model_validate(
            result.model_dump(mode="python")
            | {"request": request.model_copy(update={"materialization": changed_materialization})}
        )
    with pytest.raises(ValidationError, match="execution identity"):
        type(result).model_validate(
            result.model_dump(mode="python")
            | {
                "request": request.model_copy(
                    update={
                        "enumeration": request.enumeration.model_copy(
                            update={"max_combinations": 11}
                        )
                    }
                )
            }
        )
    incomplete_complete = result.model_dump(mode="python") | {
        "accounting": result.accounting.model_copy(
            update={
                "executed_combinations": 1,
                "examined_combinations": 1,
                "rejected_combinations": 0,
                "valid_realizations": 1,
            }
        ),
        "realizations": (result.realizations[0],),
        "geometry_groups": tuple(
            item.model_copy(
                update={
                    "realization_ids": (result.realizations[0].materialized_realization_id,),
                    "multiplicity": 1,
                }
            )
            for item in result.geometry_groups
        ),
        "final_product_groups": tuple(
            item.model_copy(
                update={
                    "realization_ids": (result.realizations[0].materialized_realization_id,),
                    "multiplicity": 1,
                }
            )
            for item in result.final_product_groups
        ),
        "failure_reasons": (),
        "combination_dispositions": (
            result.combination_dispositions[0],
            result.combination_dispositions[1].model_copy(
                update={
                    "status": "unexamined",
                    "rejection_reason": None,
                }
            ),
        ),
    }
    with pytest.raises(ValidationError, match="examine the complete nominal product"):
        type(result).model_validate(incomplete_complete)
    assert realization.realization.precursor_sequence == precursor
    assert realization.foldback_realization_id == foldback.realizations[0].foldback_realization_id
    assert realization.basal_realization_id == basal.realizations[0].basal_realization_id
    assert realization.final_product.encoding_projection.sequence == encoding.sequence
    with pytest.raises(ValidationError, match="single-strand endpoint"):
        MaterializedFinalProduct.model_validate(
            realization.final_product.model_dump(mode="python")
            | {
                "strands": (
                    *realization.final_product.strands,
                    realization.final_product.strands[0].model_copy(
                        update={"strand_id": "unsupported-second-strand"}
                    ),
                )
            }
        )
    changed_terminal_strand = realization.final_product.strands[0].model_copy(
        update={"five_prime_end": EndChemistry.PHOSPHATE}
    )
    changed_terminal_product = realization.final_product.model_copy(
        update={"strands": (changed_terminal_strand,)}
    )
    with pytest.raises(ValidationError, match="exact strand-end chemistry"):
        MaterializedConstructionRealization.create(
            realization=realization.realization,
            foldback_authority=realization.foldback_authority,
            basal_authority=realization.basal_authority,
            payload_source_map=realization.payload_source_map,
            foldback_realization_id=realization.foldback_realization_id,
            basal_realization_id=realization.basal_realization_id,
            materials=realization.materials,
            construction_program=realization.construction_program,
            final_product=changed_terminal_product,
            design=realization.design,
            geometry_ids=realization.geometry_ids,
            relaxation_radii=realization.relaxation_radii,
            claim_boundary=realization.claim_boundary,
        )
    with pytest.raises(ValidationError, match="reference must equal"):
        MaterializedFinalProduct.model_validate(
            realization.final_product.model_dump(mode="python")
            | {
                "reference": type(realization.final_product.reference).create(
                    endpoint=realization.final_product.reference.endpoint,
                    sequence=realization.final_product.reference.sequence + "A",
                    topology=realization.final_product.reference.topology,
                    end_descriptors=realization.final_product.reference.end_descriptors,
                )
            }
        )
    selected_strands = realization.construction_program.states[3].molecules
    shortened = selected_strands[0].model_copy(
        update={
            "sequence": selected_strands[0].sequence[:-1],
            "lineage": selected_strands[0].lineage[:-1],
        }
    )
    with pytest.raises(ValueError, match="concatenate to the exact hairpin product"):
        final_hairpin_strand(
            foldback=local_foldback,
            prefix=design_prefix,
            return_arm=design_prefix[::-1].translate(str.maketrans("ACGT", "TGCA")),
            source=source,
            source_complement=source_complement,
            selected_strands=(shortened, *selected_strands[1:]),
        )
    assert realization.final_product.encoding_projection.sequence_digest == hashlib.sha256(
        encoding.sequence.encode()
    ).hexdigest().join(("sha256:", ""))
    final_lineage = realization.final_product.strands[0].lineage
    source_id = realization.materials[0].material_id
    source_complement_id = realization.materials[1].material_id
    assert {item.origin_id for item in final_lineage} == {
        source_id,
        source_complement_id,
    }
    assert tuple(item.origin_id for item in final_lineage[:8]) == (source_id,) * 8
    assert tuple(item.origin_index for item in final_lineage[:8]) == tuple(range(8))
    assert tuple(item.origin_id for item in final_lineage[8:]) == (source_complement_id,) * (
        len(final_lineage) - 8
    )
    assert tuple(item.origin_index for item in final_lineage[8:]) == tuple(
        range(len(final_lineage) - 8)
    )
    foldback_phase = realization.construction_program.reaction_programs[-1]
    assert foldback_phase.states[0].molecules != foldback_phase.states[-1].molecules
    assert len(realization.construction_program.reaction_programs) == 1
    assert len(foldback_phase.stages) == 1
    assert {item.role for item in foldback_phase.stages[0].operations} == {
        EnzymeRole.BASAL_NICK,
        EnzymeRole.FOLDBACK_NICK,
    }
    sequential_program = result.realizations[1].construction_program.reaction_programs[0]
    assert tuple(
        tuple(operation.role for operation in stage.operations)
        for stage in sequential_program.stages
    ) == (
        (EnzymeRole.TERMINUS_DEFINITION,),
        (EnzymeRole.BASAL_NICK, EnzymeRole.FOLDBACK_NICK),
    )
    assert sequential_program.stages[1].pre_state_id == (sequential_program.stages[0].post_state_id)
    transition_kinds = tuple(item.kind for item in realization.construction_program.transitions)
    foldback_phase_index = transition_kinds.index("enzyme_phase")
    assert transition_kinds[foldback_phase_index + 1] == "denaturation"
    assert transition_kinds[foldback_phase_index + 2] == "fragment_selection"
    program_states = realization.construction_program.states
    assert tuple(item.phase for item in program_states) == (
        "duplex",
        "cleaved_duplex",
        "denatured_fragments",
        "selected_fragments",
        "annealed_complex",
        "ligated_product",
    )
    assert program_states[0].pairings
    assert program_states[1].pairings
    assert program_states[2].pairings == ()
    assert program_states[3].pairings == ()
    assert program_states[4].pairings
    assert program_states[5].pairings
    assert program_states[5].formed_bonds
    program = realization.construction_program

    def program_with_state(
        state_index: int,
        replacement: ConstructionState,
    ) -> ConstructionProgram:
        states = (*program.states[:state_index], replacement, *program.states[state_index + 1 :])
        transitions = list(program.transitions)
        for transition_index in (state_index - 1, state_index):
            if transition_index < 0 or transition_index >= len(transitions):
                continue
            transition = transitions[transition_index]
            if transition.reaction_program_id is not None:
                continue
            pre_state = states[transition_index]
            post_state = states[transition_index + 1]
            transitions[transition_index] = ConstructionTransition.create(
                kind=transition.kind,
                pre_state_id=pre_state.state_id,
                post_state_id=post_state.state_id,
                exact_relation=ExactStateRelation.create(
                    pre_state_id=pre_state.state_id,
                    post_state_id=post_state.state_id,
                ),
            )
        return ConstructionProgram.create(
            states=states,
            transitions=tuple(transitions),
            reaction_programs=program.reaction_programs,
            stage_assessments=program.stage_assessments,
        )

    def rebuild_program(states: tuple[ConstructionState, ...]) -> ConstructionProgram:
        transitions = []
        for index, transition in enumerate(program.transitions):
            pre_state = states[index]
            post_state = states[index + 1]
            if transition.reaction_program_id is not None:
                transitions.append(
                    ConstructionTransition.create(
                        kind=transition.kind,
                        pre_state_id=pre_state.state_id,
                        post_state_id=post_state.state_id,
                        reaction_program_id=transition.reaction_program_id,
                        reaction_boundary_mapping=ReactionBoundaryMapping.create(
                            reaction_program_id=transition.reaction_program_id,
                            pre_state_id=pre_state.state_id,
                            post_state_id=post_state.state_id,
                            pre_strands=pre_state.molecules,
                            post_strands=post_state.molecules,
                            pre_pairings=pre_state.pairings,
                            post_pairings=post_state.pairings,
                            pre_bonds=pre_state.formed_bonds,
                            post_bonds=post_state.formed_bonds,
                        ),
                    )
                )
            else:
                transitions.append(
                    ConstructionTransition.create(
                        kind=transition.kind,
                        pre_state_id=pre_state.state_id,
                        post_state_id=post_state.state_id,
                        exact_relation=ExactStateRelation.create(
                            pre_state_id=pre_state.state_id,
                            post_state_id=post_state.state_id,
                        ),
                    )
                )
        return ConstructionProgram.create(
            states=states,
            transitions=tuple(transitions),
            reaction_programs=program.reaction_programs,
            stage_assessments=program.stage_assessments,
        )

    reduced_duplex = ConstructionState.create(
        molecules=program.states[0].molecules,
        phase=program.states[0].phase,
        pairings=program.states[0].pairings[:1],
    )
    with pytest.raises(ValueError, match="complete complement pairing"):
        validate_initial_material_state(reduced_duplex, realization.materials)

    changed_assessment = program.stage_assessments[0].model_copy(
        update={"resolved_against_state_id": "arbitrary-state"}
    )
    with pytest.raises(ValidationError, match="pre-state"):
        ConstructionProgram.create(
            states=program.states,
            transitions=program.transitions,
            reaction_programs=program.reaction_programs,
            stage_assessments=(changed_assessment, *program.stage_assessments[1:]),
        )
    first_assessment = program.stage_assessments[0]
    first_binding = first_assessment.intended_bindings[0]
    alternate_enzyme = next(
        operation.enzyme_id
        for operation in program.reaction_programs[0].stages[0].operations
        if operation.enzyme_id != first_binding.enzyme_id
    )
    changed_binding_assessment = first_assessment.model_copy(
        update={
            "intended_bindings": (
                first_binding.model_copy(update={"enzyme_id": alternate_enzyme}),
                *first_assessment.intended_bindings[1:],
            )
        }
    )
    with pytest.raises(ValidationError, match="evidence must replay"):
        ConstructionProgram.create(
            states=program.states,
            transitions=program.transitions,
            reaction_programs=program.reaction_programs,
            stage_assessments=(
                changed_binding_assessment,
                *program.stage_assessments[1:],
            ),
        )
    binding_span = first_binding.recognition_span
    shifted_binding = first_binding.model_copy(
        update={
            "recognition_span": Span(
                start=Boundary(offset=binding_span.start.offset + 1),
                end=Boundary(offset=binding_span.end.offset + 1),
            )
        }
    )
    shifted_assessment = first_assessment.model_copy(
        update={
            "intended_bindings": (
                shifted_binding,
                *first_assessment.intended_bindings[1:],
            )
        }
    )
    with pytest.raises(ValidationError, match="evidence must replay"):
        ConstructionProgram.create(
            states=program.states,
            transitions=program.transitions,
            reaction_programs=program.reaction_programs,
            stage_assessments=(shifted_assessment, *program.stage_assessments[1:]),
        )

    selected_state = program.states[3]
    selected_strand = selected_state.molecules[0]
    tampered_base = "C" if selected_strand.sequence[0] == "A" else "A"
    tampered_selected = ConstructionState.create(
        molecules=(
            selected_strand.model_copy(
                update={"sequence": tampered_base + selected_strand.sequence[1:]}
            ),
            *selected_state.molecules[1:],
        ),
        phase=selected_state.phase,
    )
    tampered_states = (*program.states[:3], tampered_selected, *program.states[4:])
    tampered_transitions = list(program.transitions)
    for transition_index in (2, 3):
        pre_state = tampered_states[transition_index]
        post_state = tampered_states[transition_index + 1]
        tampered_transitions[transition_index] = ConstructionTransition.create(
            kind=program.transitions[transition_index].kind,
            pre_state_id=pre_state.state_id,
            post_state_id=post_state.state_id,
            exact_relation=ExactStateRelation.create(
                pre_state_id=pre_state.state_id,
                post_state_id=post_state.state_id,
            ),
        )
    with pytest.raises(ValidationError, match="Fragment selection"):
        ConstructionProgram.create(
            states=tampered_states,
            transitions=tuple(tampered_transitions),
            reaction_programs=program.reaction_programs,
            stage_assessments=program.stage_assessments,
        )

    denatured_state = program.states[2]
    changed_denatured_strand = denatured_state.molecules[0].model_copy(
        update={
            "five_prime_end": (
                EndChemistry.HYDROXYL
                if denatured_state.molecules[0].five_prime_end is EndChemistry.PHOSPHATE
                else EndChemistry.PHOSPHATE
            )
        }
    )
    changed_denatured = ConstructionState.create(
        molecules=(changed_denatured_strand, *denatured_state.molecules[1:]),
        phase=denatured_state.phase,
    )
    with pytest.raises(ValidationError, match="Denaturation"):
        program_with_state(2, changed_denatured)

    annealed_state = program.states[4]
    changed_annealed_strand = annealed_state.molecules[0].model_copy(
        update={
            "three_prime_end": (
                EndChemistry.HYDROXYL
                if annealed_state.molecules[0].three_prime_end is EndChemistry.PHOSPHATE
                else EndChemistry.PHOSPHATE
            )
        }
    )
    changed_annealed = ConstructionState.create(
        molecules=(changed_annealed_strand, *annealed_state.molecules[1:]),
        phase=annealed_state.phase,
        pairings=annealed_state.pairings,
    )
    with pytest.raises(ValidationError, match="Annealing"):
        program_with_state(4, changed_annealed)

    ligated_state = program.states[5]
    changed_ligated_strand = ligated_state.molecules[0].model_copy(
        update={
            "five_prime_end": (
                EndChemistry.HYDROXYL
                if ligated_state.molecules[0].five_prime_end is EndChemistry.PHOSPHATE
                else EndChemistry.PHOSPHATE
            )
        }
    )
    changed_ligated = ConstructionState.create(
        molecules=(changed_ligated_strand,),
        phase=ligated_state.phase,
        pairings=ligated_state.pairings,
        formed_bonds=ligated_state.formed_bonds,
    )
    with pytest.raises(ValidationError, match="Ligation product"):
        program_with_state(5, changed_ligated)
    missing_ligated_pair = ConstructionState.create(
        molecules=ligated_state.molecules,
        phase=ligated_state.phase,
        pairings=ligated_state.pairings[:-1],
        formed_bonds=ligated_state.formed_bonds,
    )
    with pytest.raises(ValidationError, match="preserve exact annealed"):
        program_with_state(5, missing_ligated_pair)

    reduced_annealed = ConstructionState.create(
        molecules=annealed_state.molecules,
        phase=annealed_state.phase,
        pairings=annealed_state.pairings[:1],
    )
    reduced_ligated = ConstructionState.create(
        molecules=ligated_state.molecules,
        phase=ligated_state.phase,
        pairings=ligated_state.pairings[:1],
        formed_bonds=ligated_state.formed_bonds,
    )
    reduced_states = (*program.states[:4], reduced_annealed, reduced_ligated)
    reduced_transitions = list(program.transitions)
    for transition_index in (3, 4):
        pre_state = reduced_states[transition_index]
        post_state = reduced_states[transition_index + 1]
        reduced_transitions[transition_index] = ConstructionTransition.create(
            kind=program.transitions[transition_index].kind,
            pre_state_id=pre_state.state_id,
            post_state_id=post_state.state_id,
            exact_relation=ExactStateRelation.create(
                pre_state_id=pre_state.state_id,
                post_state_id=post_state.state_id,
            ),
        )
    reduced_program = ConstructionProgram.create(
        states=reduced_states,
        transitions=tuple(reduced_transitions),
        reaction_programs=program.reaction_programs,
        stage_assessments=program.stage_assessments,
    )
    with pytest.raises(ValidationError, match="annealing associations"):
        resealed_realization(construction_program=reduced_program)
    changed_foldback_authority = realization.foldback_authority.model_copy(
        update={"annealing_pairs": realization.foldback_authority.annealing_pairs[:1]}
    )
    with pytest.raises(ValidationError, match="identity must seal"):
        resealed_realization(foldback_authority=changed_foldback_authority)

    ligation_bond = ligated_state.formed_bonds[0].bond
    upstream = next(
        item
        for item in selected_state.molecules
        if item.strand_id == ligation_bond.upstream_strand_id
    )
    chemistry_states = list(program.states)
    for state_index in range(1, 5):
        state = chemistry_states[state_index]
        molecules = tuple(
            strand.model_copy(update={"three_prime_end": EndChemistry.PHOSPHATE})
            if strand.lineage == upstream.lineage
            else strand
            for strand in state.molecules
        )
        chemistry_states[state_index] = ConstructionState.create(
            molecules=molecules,
            phase=state.phase,
            pairings=state.pairings,
            formed_bonds=state.formed_bonds,
        )
    with pytest.raises(ValidationError, match="upstream hydroxyl"):
        rebuild_program(tuple(chemistry_states))

    lineage_states = [program.states[0]]
    for state in program.states[1:]:
        molecules = tuple(
            strand.model_copy(
                update={
                    "lineage": tuple(
                        item.model_copy(update={"origin_id": "invented-material"})
                        if item.origin_id == source.material_id
                        else item
                        for item in strand.lineage
                    )
                }
            )
            for strand in state.molecules
        )
        lineage_states.append(
            ConstructionState.create(
                molecules=molecules,
                phase=state.phase,
                pairings=state.pairings,
                formed_bonds=state.formed_bonds,
            )
        )
    invented_program = rebuild_program(tuple(lineage_states))
    invented_product = realization.final_product.model_copy(
        update={"strands": invented_program.states[-1].molecules}
    )
    with pytest.raises(ValidationError, match="fragment chemistry and lineage"):
        resealed_realization(
            construction_program=invented_program,
            final_product=invented_product,
        )

    unspecified_selected = ConstructionState.create(
        molecules=selected_state.molecules,
        phase=type(selected_state.phase).UNSPECIFIED,
    )
    unspecified_states = (*program.states[:3], unspecified_selected, *program.states[4:])
    unspecified_transitions = list(program.transitions)
    for transition_index in (2, 3):
        pre_state = unspecified_states[transition_index]
        post_state = unspecified_states[transition_index + 1]
        unspecified_transitions[transition_index] = ConstructionTransition.create(
            kind=program.transitions[transition_index].kind,
            pre_state_id=pre_state.state_id,
            post_state_id=post_state.state_id,
            exact_relation=ExactStateRelation.create(
                pre_state_id=pre_state.state_id,
                post_state_id=post_state.state_id,
            ),
        )
    with pytest.raises(ValidationError, match="fully typed phases"):
        ConstructionProgram.create(
            states=unspecified_states,
            transitions=tuple(unspecified_transitions),
            reaction_programs=program.reaction_programs,
            stage_assessments=program.stage_assessments,
        )
    with pytest.raises(ValidationError, match="identity must seal"):
        ConstructionProgram.model_validate(
            program.model_dump(mode="python")
            | {"program_id": "hop:construction-program/" + "0" * 64 + "@1"}
        )
    invalid_programs = (
        (
            {
                "states": (
                    program.states[0],
                    program.states[0],
                    *program.states[2:],
                )
            },
            "state identities must be unique",
        ),
        ({"transitions": program.transitions[:-1]}, "connect consecutive states exactly"),
        (
            {"reaction_programs": (program.reaction_programs[0],) * 2},
            "ReactionProgram ids must be unique",
        ),
        ({"reaction_programs": ()}, "referenced exactly once"),
        ({"stage_assessments": ()}, "cover all embedded enzyme phases"),
    )
    for updates, message in invalid_programs:
        with pytest.raises(ValidationError, match=message):
            ConstructionProgram.create(
                states=updates.get("states", program.states),
                transitions=updates.get("transitions", program.transitions),
                reaction_programs=updates.get("reaction_programs", program.reaction_programs),
                stage_assessments=updates.get("stage_assessments", program.stage_assessments),
            )
    enzyme_transitions = tuple(
        item
        for item in realization.construction_program.transitions
        if item.reaction_program_id is not None
    )
    assert all(item.reaction_boundary_mapping is not None for item in enzyme_transitions)
    enzyme_transition = enzyme_transitions[0]
    assert enzyme_transition.reaction_boundary_mapping is not None
    initial_state = realization.construction_program.states[0]
    changed_chemistry = initial_state.molecules[0].model_copy(
        update={"five_prime_end": EndChemistry.PHOSPHATE}
    )
    changed_lineage = initial_state.molecules[0].model_copy(
        update={
            "lineage": (
                initial_state.molecules[0]
                .lineage[0]
                .model_copy(update={"origin_id": "different-source"}),
                *initial_state.molecules[0].lineage[1:],
            )
        }
    )
    for changed_strand in (changed_chemistry, changed_lineage):
        changed_initial = ConstructionState.create(
            molecules=(changed_strand, *initial_state.molecules[1:]),
        )
        with pytest.raises(ValidationError, match="boundary mapping"):
            ConstructionTransition.create(
                kind=enzyme_transition.kind,
                pre_state_id=changed_initial.state_id,
                post_state_id=enzyme_transition.post_state_id,
                reaction_program_id=enzyme_transition.reaction_program_id,
                reaction_boundary_mapping=enzyme_transition.reaction_boundary_mapping,
            )
    changed_initial = ConstructionState.create(
        molecules=(changed_chemistry, *initial_state.molecules[1:]),
        phase=initial_state.phase,
        pairings=initial_state.pairings,
    )
    original_mapping = enzyme_transition.reaction_boundary_mapping
    assert original_mapping is not None
    changed_mapping = ReactionBoundaryMapping.create(
        reaction_program_id=original_mapping.reaction_program_id,
        pre_state_id=changed_initial.state_id,
        post_state_id=original_mapping.post_state_id,
        pre_strands=changed_initial.molecules,
        post_strands=original_mapping.post_strands,
        pre_pairings=changed_initial.pairings,
        post_pairings=original_mapping.post_pairings,
        pre_bonds=changed_initial.formed_bonds,
        post_bonds=original_mapping.post_bonds,
    )
    changed_transition = ConstructionTransition.create(
        kind=enzyme_transition.kind,
        pre_state_id=changed_initial.state_id,
        post_state_id=enzyme_transition.post_state_id,
        reaction_program_id=enzyme_transition.reaction_program_id,
        reaction_boundary_mapping=changed_mapping,
    )
    changed_program = ConstructionProgram.create(
        states=(changed_initial, *realization.construction_program.states[1:]),
        transitions=(changed_transition, *realization.construction_program.transitions[1:]),
        reaction_programs=realization.construction_program.reaction_programs,
        stage_assessments=realization.construction_program.stage_assessments,
    )
    changed_draft = realization.model_copy(update={"construction_program": changed_program})
    changed_realization = changed_draft.model_dump(mode="python")
    changed_realization["materialized_realization_id"] = _content_id(
        "materialized-construction",
        1,
        changed_draft.model_dump(mode="json", exclude={"materialized_realization_id"}),
    )
    with pytest.raises(ValidationError, match="material chemistry"):
        type(result).model_validate(
            result.model_dump(mode="python")
            | {"realizations": (changed_realization, *result.realizations[1:])}
        )
    enzyme_post = realization.construction_program.states[1]
    expected_enzyme_post_sequences = tuple(
        sequence
        for molecule in foldback_phase.states[-1].molecules
        for sequence in (
            molecule.reference_sequence_5prime,
            molecule.complement_sequence_5prime,
        )
        if sequence is not None
    )
    assert tuple(strand.sequence for strand in enzyme_post.molecules) == (
        expected_enzyme_post_sequences
    )
    changed_post_molecule = (
        foldback_phase.states[-1]
        .molecules[0]
        .model_copy(
            update={
                "reference_sequence_5prime": "T"
                + foldback_phase.states[-1].molecules[0].reference_sequence_5prime[1:]
            }
        )
    )
    changed_post = foldback_phase.states[-1].model_copy(
        update={"molecules": (changed_post_molecule, *foldback_phase.states[-1].molecules[1:])}
    )
    changed_phase = foldback_phase.model_copy(
        update={"states": (*foldback_phase.states[:-1], changed_post)}
    )
    with pytest.raises(ValidationError, match="ReactionProgram boundaries"):
        ConstructionProgram.create(
            states=realization.construction_program.states,
            transitions=realization.construction_program.transitions,
            reaction_programs=(changed_phase,),
            stage_assessments=realization.construction_program.stage_assessments,
        )
    released_state = realization.construction_program.states[-4]
    selected_state = realization.construction_program.states[-3]
    released_fragment = foldback.realizations[0].molecular_fragments[1].sequence
    for fragment in foldback.realizations[0].molecular_fragments:
        lifted = next(
            strand
            for strand in released_state.molecules
            if f"-{fragment.fragment_id}-" in strand.strand_id
        )
        assert lifted.five_prime_end is fragment.five_prime_end
        assert lifted.three_prime_end is fragment.three_prime_end
    assert released_fragment in {strand.sequence for strand in released_state.molecules}
    assert released_fragment not in {strand.sequence for strand in selected_state.molecules}
    assert (
        realization.final_product.strands[0].five_prime_end
        is realization.materials[0].five_prime_end
    )
    assert (
        realization.final_product.strands[0].three_prime_end
        is realization.materials[1].three_prime_end
    )
    assert tuple(
        member for group in result.geometry_groups for member in group.realization_ids
    ) == tuple(item.materialized_realization_id for item in result.realizations)

    proof_safe = _discover_raw(
        request.model_copy(
            update={
                "enumeration": request.enumeration.model_copy(
                    update={"pruning": CompositionPruningMode.PROOF_SAFE}
                )
            }
        ),
        foldback=foldback,
        basal=basal,
        design=design,
    )
    assert tuple(item.materialized_realization_id for item in proof_safe.realizations) == (
        *(item.materialized_realization_id for item in result.realizations),
    )

    truncated = _discover_raw(
        request.model_copy(
            update={"enumeration": request.enumeration.model_copy(update={"max_combinations": 1})}
        ),
        foldback=foldback,
        basal=basal,
        design=design,
    )
    assert truncated.status is SearchCompletionStatus.TRUNCATED
    assert truncated.accounting.nominal_combinations == 2
    assert truncated.accounting.examined_combinations == 1
    assert truncated.truncation_reasons == ("max_combinations",)
    assert truncated.result_id != result.result_id
    assert tuple(item.status for item in truncated.combination_dispositions) == ("accepted",)

    realization_limited = _discover_raw(
        request.model_copy(
            update={"enumeration": request.enumeration.model_copy(update={"max_realizations": 1})}
        ),
        foldback=foldback,
        basal=basal,
        design=design,
    )
    assert realization_limited.status is SearchCompletionStatus.TRUNCATED
    assert realization_limited.accounting.examined_combinations == 1
    assert realization_limited.accounting.valid_realizations == 1
    assert realization_limited.accounting.rejected_combinations == 0
    assert realization_limited.failure_reasons == ()
    assert tuple(item.status for item in realization_limited.combination_dispositions) == (
        "accepted",
    )

    all_required = _discover_raw(
        request.model_copy(
            update={
                "whole_route_constraints": request.whole_route_constraints.model_copy(
                    update={"require_all_combinations_valid": True}
                )
            }
        ),
        foldback=foldback,
        basal=basal,
        design=design,
    )
    assert all_required.status is SearchCompletionStatus.COMPLETE
    assert all_required.realizations == result.realizations
    assert tuple(item.status for item in all_required.combination_dispositions) == (
        "accepted",
        "accepted",
    )

    no_basal = _discover_raw(
        request.model_copy(update={"basal_result_id": None}),
        foldback=foldback,
        basal=None,
        design=design,
    )
    assert no_basal.status is SearchCompletionStatus.COMPLETE
    assert no_basal.realizations[0].basal_realization_id is None

    other_payload = FinalPayloadReference(
        payload=ExactPayload(sequence="GACT"),
        basal_boundary=Boundary(offset=0),
        foldback_boundary=Boundary(offset=4),
    )
    other_foldback = foldback.model_copy(
        update={
            "neighborhood": foldback.neighborhood.model_copy(
                update={
                    "request": foldback.neighborhood.request.model_copy(
                        update={"payload": other_payload}
                    )
                }
            )
        }
    )
    with pytest.raises(ValueError, match=r"problem_id|payload authority|deterministic discovery"):
        _discover_raw(
            request.model_copy(update={"foldback_result_id": other_foldback.result_id}),
            foldback=other_foldback,
            basal=basal,
            design=design,
        )

    wrong_payload_map = PayloadSourceMap(
        segments=(
            PayloadSourceSegment(
                payload_span=Span(start=Boundary(offset=0), end=Boundary(offset=4)),
                source_material_id=realization.materials[0].material_id,
                source_span=Span(start=Boundary(offset=0), end=Boundary(offset=4)),
                orientation=SourceOrientation.FORWARD,
            ),
        )
    )
    with pytest.raises(ValidationError, match="exact lifted local authority"):
        resealed_realization(payload_source_map=wrong_payload_map)
    missing_material_map = PayloadSourceMap(
        segments=(
            realization.payload_source_map.segments[0].model_copy(
                update={"source_material_id": "missing-source"}
            ),
        )
    )
    with pytest.raises(ValueError, match="reference exact route material"):
        validate_payload_source_map(
            request,
            realization.model_copy(update={"payload_source_map": missing_material_map}),
        )

    accepted_disposition = result.combination_dispositions[0]
    changed_origin_material = realization.materials[0].model_copy(
        update={"origin": MaterialOrigin.PURIFIED}
    )
    validation_cases = (
        (
            {
                "realization": realization.model_copy(
                    update={"materials": (changed_origin_material, *realization.materials[1:])}
                )
            },
            "exact result request policy",
        ),
        (
            {
                "disposition": accepted_disposition.model_copy(
                    update={
                        "foldback_realization_id": result.combination_dispositions[
                            1
                        ].foldback_realization_id
                    }
                )
            },
            "exact disposition",
        ),
        (
            {"provenance": result.provenance.model_copy(update={"foldback_realization_ids": ()})},
            "verified foldback authority",
        ),
        (
            {"provenance": result.provenance.model_copy(update={"basal_realization_ids": ()})},
            "verified basal authority",
        ),
        (
            {
                "realization": realization.model_copy(
                    update={
                        "realization": realization.realization.model_copy(
                            update={"local_realization_ids": (realization.foldback_realization_id,)}
                        )
                    }
                )
            },
            "preserve its exact local authorities",
        ),
    )
    for updates, message in validation_cases:
        with pytest.raises(ValueError, match=message):
            validate_accepted_realization(
                request=request,
                provenance=updates.get("provenance", result.provenance),
                disposition=updates.get("disposition", accepted_disposition),
                realization=updates.get("realization", realization),
            )

    invalid_identity = realization.model_dump(mode="python") | {
        "materialized_realization_id": "hop:materialized-construction/" + "0" * 64 + "@1"
    }
    with pytest.raises(ValidationError, match="identity must seal"):
        MaterializedConstructionRealization.model_validate(invalid_identity)

    mismatched_precursor = CompleteConstructionRealization.create(
        precursor_sequence=realization.realization.precursor_sequence + "A",
        local_realization_ids=realization.realization.local_realization_ids,
        stage_ids=realization.realization.stage_ids,
        final_product_id=realization.realization.final_product_id,
    )
    with pytest.raises(ValidationError, match="precursor must equal"):
        resealed_realization(realization=mismatched_precursor)

    mismatched_product = CompleteConstructionRealization.create(
        precursor_sequence=realization.realization.precursor_sequence,
        local_realization_ids=realization.realization.local_realization_ids,
        stage_ids=realization.realization.stage_ids,
        final_product_id="hop:final-product/" + "0" * 64 + "@1",
    )
    with pytest.raises(ValidationError, match="bind the exact final product"):
        resealed_realization(realization=mismatched_product)

    mismatched_stages = CompleteConstructionRealization.create(
        precursor_sequence=realization.realization.precursor_sequence,
        local_realization_ids=realization.realization.local_realization_ids,
        stage_ids=("fake-stage",),
        final_product_id=realization.realization.final_product_id,
    )
    with pytest.raises(ValidationError, match="preserve every global enzyme stage"):
        resealed_realization(realization=mismatched_stages)

    changed_encoding = (
        "C" if realization.design.encoding_sequence[0] == "A" else "A"
    ) + realization.design.encoding_sequence[1:]
    changed_design = realization.design.model_copy(
        update={
            "encoding_sequence": changed_encoding,
            "encoding_digest": "sha256:" + hashlib.sha256(changed_encoding.encode()).hexdigest(),
        }
    )
    with pytest.raises(ValidationError, match=r"model-layer HOP plan|encoding projection"):
        resealed_realization(design=changed_design)

    unresolved_claim = realization.claim_boundary.model_copy(
        update={"method": MethodResolutionStatus.NOT_RESOLVED}
    )
    with pytest.raises(ValidationError, match="resolved digital method"):
        resealed_realization(claim_boundary=unresolved_claim)

    with pytest.raises(ValidationError, match="geometry identities and radii"):
        resealed_realization(relaxation_radii=(0,))

    for field in (
        "source_material_nt",
        "candidate_enzyme_programs",
        "recognition_placements_attempted",
        "constraint_systems_attempted",
    ):
        replacement = (
            result.material_accounting.model_copy(
                update={field: getattr(result.material_accounting, field, 0) + 1}
            )
            if field == "source_material_nt"
            else result.accounting.model_copy(update={field: getattr(result.accounting, field) + 1})
        )
        key = "material_accounting" if field == "source_material_nt" else "accounting"
        with pytest.raises(ValidationError, match="accounting"):
            type(result).model_validate(result.model_dump(mode="python") | {key: replacement})

    with pytest.raises(ValidationError, match="HOP version"):
        type(result).model_validate(
            result.model_dump(mode="python")
            | {
                "provenance": result.provenance.model_copy(
                    update={"hop_version": "different-version"}
                )
            }
        )

    invalid_result_cases = (
        (
            {
                "provenance": result.provenance.model_copy(
                    update={
                        "foldback_result_id": "hop:foldback-neighborhood-result/" + "0" * 64 + "@1"
                    }
                )
            },
            "bind every requested upstream authority",
        ),
        ({"realizations": (realization, realization)}, "must not repeat realizations"),
        ({"realizations": ()}, "require exact realizations"),
        (
            {"status": SearchCompletionStatus.INFEASIBLE},
            "must not contain realizations",
        ),
        ({"truncation_reasons": ("unexpected",)}, "Local truncation reasons"),
        (
            {
                "accounting": result.accounting.model_copy(
                    update={
                        "valid_realizations": 1,
                        "rejected_combinations": 1,
                        "rejected_after_execution": 1,
                    }
                )
            },
            "match exact realization count",
        ),
        (
            {"accounting": result.accounting.model_copy(update={"distinct_geometry_groups": 2})},
            "match reversible grouping counts",
        ),
        (
            {"combination_dispositions": (result.combination_dispositions[0],)},
            "cover the exact examined prefix",
        ),
        (
            {
                "combination_dispositions": (
                    result.combination_dispositions[0].model_copy(update={"ordinal": 1}),
                    result.combination_dispositions[1].model_copy(update={"ordinal": 0}),
                )
            },
            "preserve canonical Cartesian order",
        ),
    )
    for updates, message in invalid_result_cases:
        with pytest.raises(ValidationError, match=message):
            type(result).model_validate(result.model_dump(mode="python") | updates)

    fully_examined_truncation = result.model_dump(mode="python") | {
        "status": SearchCompletionStatus.TRUNCATED,
        "truncation_reasons": ("max_combinations",),
        "claim_boundary": result.claim_boundary.model_copy(update={"method": "not_resolved"}),
    }
    with pytest.raises(ValidationError, match="Local truncation reasons"):
        type(result).model_validate(fully_examined_truncation)

    resolved_truncation = truncated.model_dump(mode="python") | {
        "claim_boundary": truncated.claim_boundary.model_copy(
            update={"method": MethodResolutionStatus.RESOLVED}
        )
    }
    with pytest.raises(ValidationError, match="method claim"):
        type(result).model_validate(resolved_truncation)

    with pytest.raises(ValidationError, match="Upstream truncation reasons"):
        type(result).model_validate(
            result.model_dump(mode="python")
            | {"upstream_truncation_reasons": ("foldback:max_search_nodes",)}
        )
    with pytest.raises(ValidationError, match="failure-reason codes must be unique"):
        type(partially_compatible).model_validate(
            partially_compatible.model_dump(mode="python")
            | {
                "failure_reasons": (
                    partially_compatible.failure_reasons[0],
                    partially_compatible.failure_reasons[0],
                )
            }
        )
    with pytest.raises(ValidationError, match="truncation-reason codes must be unique"):
        type(truncated).model_validate(
            truncated.model_dump(mode="python")
            | {"truncation_reasons": ("max_combinations", "max_combinations")}
        )
    with pytest.raises(ValidationError, match="ordered upstream domains"):
        type(result).model_validate(
            result.model_dump(mode="python")
            | {
                "combination_dispositions": (
                    result.combination_dispositions[0].model_copy(
                        update={
                            "foldback_realization_id": result.combination_dispositions[
                                1
                            ].foldback_realization_id
                        }
                    ),
                    result.combination_dispositions[1],
                )
            }
        )
    with pytest.raises(ValidationError, match="status must derive"):
        type(result).model_validate(
            result.model_dump(mode="python")
            | {
                "status": SearchCompletionStatus.TRUNCATED,
                "claim_boundary": result.claim_boundary.model_copy(
                    update={"method": MethodResolutionStatus.NOT_RESOLVED}
                ),
            }
        )
    with pytest.raises(ValidationError, match="method claim must derive"):
        type(result).model_validate(
            result.model_dump(mode="python")
            | {
                "claim_boundary": result.claim_boundary.model_copy(
                    update={"method": MethodResolutionStatus.NOT_RESOLVED}
                )
            }
        )
    relaxed_enumeration = truncated.request.enumeration.model_copy(
        update={"max_combinations": 2, "max_realizations": 10}
    )
    relaxed_request = truncated.request.model_copy(update={"enumeration": relaxed_enumeration})
    relaxed_execution = truncated.execution.model_copy(update={"enumeration": relaxed_enumeration})
    with pytest.raises(ValidationError, match="partial composition prefix"):
        type(truncated).model_validate(
            truncated.model_dump(mode="python")
            | {
                "request": relaxed_request,
                "execution": relaxed_execution,
                "execution_id": relaxed_execution.execution_id,
            }
        )

    kept = all_required.realizations[0]
    rejected_disposition = type(all_required.combination_dispositions[1]).model_validate(
        all_required.combination_dispositions[1].model_dump(mode="python")
        | {
            "status": CompositionDispositionStatus.REJECTED,
            "materialized_realization_id": None,
            "rejection_reason": CompositionRejectionCode.GLOBAL_ACTIONABLE_SITE_CONFLICT,
        }
    )
    partial_accounting = CompositionAccounting(
        **(
            all_required.accounting.model_dump(mode="python")
            | {
                "rejected_after_execution": 1,
                "rejected_combinations": 1,
                "valid_realizations": 1,
                "distinct_geometry_groups": 1,
                "distinct_final_products": 1,
            }
        )
    )
    partial_groups = tuple(
        group.model_copy(
            update={
                "realization_ids": (kept.materialized_realization_id,),
                "multiplicity": 1,
            }
        )
        for group in all_required.geometry_groups
        if kept.materialized_realization_id in group.realization_ids
    )
    partial_product_groups = tuple(
        group.model_copy(
            update={
                "realization_ids": (kept.materialized_realization_id,),
                "multiplicity": 1,
            }
        )
        for group in all_required.final_product_groups
        if kept.materialized_realization_id in group.realization_ids
    )
    partial_material_accounting = all_required.material_accounting.model_copy(
        update={
            "source_material_nt": sum(len(item.sequence_5prime) for item in kept.materials[:2]),
            "auxiliary_material_nt": sum(len(item.sequence_5prime) for item in kept.materials[2:]),
            "endpoint_product_nt": len(kept.final_product.reference.sequence),
        }
    )
    partial_result = result.model_dump(mode="python") | {
        "realizations": (kept,),
        "geometry_groups": partial_groups,
        "final_product_groups": partial_product_groups,
        "accounting": partial_accounting,
        "material_accounting": partial_material_accounting,
        "combination_dispositions": (
            result.combination_dispositions[0],
            rejected_disposition,
        ),
    }
    with pytest.raises(ValidationError, match="account for every rejected combination"):
        type(result).model_validate(partial_result | {"failure_reasons": ()})
    with pytest.raises(ValidationError, match="reconcile exact failure counts"):
        type(result).model_validate(
            partial_result | {"failure_reasons": ({"code": "different-rejection", "count": 1},)}
        )

    swapped_dispositions = (
        result.combination_dispositions[0].model_copy(
            update={
                "materialized_realization_id": result.combination_dispositions[
                    1
                ].materialized_realization_id
            }
        ),
        result.combination_dispositions[1].model_copy(
            update={
                "materialized_realization_id": result.combination_dispositions[
                    0
                ].materialized_realization_id
            }
        ),
    )
    with pytest.raises(ValidationError, match="reconcile examined and accepted"):
        type(result).model_validate(
            result.model_dump(mode="python") | {"combination_dispositions": swapped_dispositions}
        )

    with pytest.raises(ValidationError, match=r"combination evaluation|all combinations"):
        type(result).model_validate(
            all_required.model_dump(mode="python")
            | {
                "realizations": (kept,),
                "geometry_groups": partial_groups,
                "final_product_groups": partial_product_groups,
                "accounting": partial_accounting,
                "failure_reasons": (
                    {
                        "code": CompositionRejectionCode.GLOBAL_ACTIONABLE_SITE_CONFLICT,
                        "count": 1,
                    },
                ),
                "material_accounting": partial_material_accounting,
                "combination_dispositions": (
                    all_required.combination_dispositions[0],
                    rejected_disposition,
                ),
            }
        )


def test_require_all_preserves_intrinsic_failures_when_every_combination_rejects(
    tmp_path: Path,
) -> None:
    payload = FinalPayloadReference(
        payload=ExactPayload(sequence="GACA"),
        basal_boundary=Boundary(offset=0),
        foldback_boundary=Boundary(offset=4),
    )
    foldback = discover_foldback_neighborhood(
        _request(
            _nickase(
                motif="TCAGATGCTGA",
                cut_offset=0,
                orientation_semantics=RecognitionOrientationSemantics.DECLARED_ONLY,
            ),
            target=FoldbackTarget(
                nick_offset_within_foldback_nt=0,
                loop_length_nt=3,
                annealing_arm_length_bp=4,
            ),
        )
    )
    design = _verified_design(tmp_path)
    request = _construction_request(
        payload=payload,
        foldback=foldback,
        basal=None,
        design=design,
        complement_five_prime_end=EndChemistry.HYDROXYL,
        require_all=True,
    )

    result = _discover_raw(request, foldback=foldback, basal=None, design=design)

    assert result.status is SearchCompletionStatus.INFEASIBLE
    assert result.realizations == ()
    assert tuple((item.code, item.count) for item in result.failure_reasons) == (
        (CompositionRejectionCode.SOURCE_END_CHEMISTRY_MISMATCH, len(foldback.realizations)),
    )


def test_complete_materialization_preserves_exact_optional_stem_extension(
    tmp_path: Path,
) -> None:
    payload = FinalPayloadReference(
        payload=ExactPayload(sequence="GACA"),
        basal_boundary=Boundary(offset=0),
        foldback_boundary=Boundary(offset=4),
    )
    foldback = discover_foldback_neighborhood(
        _request(
            _nickase(
                motif="TCAGATGCTGA",
                cut_offset=0,
                orientation_semantics=RecognitionOrientationSemantics.DECLARED_ONLY,
            ),
            _terminus_enzyme(),
            target=FoldbackTarget(
                nick_offset_within_foldback_nt=0,
                loop_length_nt=3,
                annealing_arm_length_bp=4,
            ),
        )
    )
    basal = _basal_result(payload)
    spec = _component_spec().model_copy(
        update={
            "payload": ExactPayload(sequence="GACA"),
            "stem_extension": hop.PairedStemExtensionRequest(
                left_arm="GCTA",
                right_arm="TAAC",
            ),
        }
    )
    design = load_verified_bundle(hop.compile(spec).write(tmp_path / "stem-design"))
    request = _construction_request(
        payload=payload,
        foldback=foldback,
        basal=basal,
        design=design,
    )

    result = _discover_raw(request, foldback=foldback, basal=basal, design=design)

    assert result.status is SearchCompletionStatus.COMPLETE
    assert result.realizations
    assert all(
        item.final_product.encoding_projection.sequence == request.design.encoding_sequence
        for item in result.realizations
    )
    assert all(
        item.materials[0].sequence_5prime.startswith("AAAAGCTA")
        and item.materials[1].sequence_5prime.endswith("TAACTTTT")
        for item in result.realizations
    )
    assert all(
        item.payload_source_map.segments[0].source_span.start.offset == 8
        for item in result.realizations
    )


def test_require_all_does_not_reclassify_a_truncated_upstream_search(
    tmp_path: Path,
) -> None:
    payload = FinalPayloadReference(
        payload=ExactPayload(sequence="GACA"),
        basal_boundary=Boundary(offset=0),
        foldback_boundary=Boundary(offset=4),
    )
    foldback = discover_foldback_neighborhood(
        _request(
            _nickase(
                motif="TCAGATGCTGA",
                cut_offset=0,
                orientation_semantics=RecognitionOrientationSemantics.DECLARED_ONLY,
            ),
            _terminus_enzyme(),
            target=FoldbackTarget(
                nick_offset_within_foldback_nt=0,
                loop_length_nt=3,
                annealing_arm_length_bp=4,
            ),
            relaxation=RelaxationPolicy(
                mode=RelaxationMode.THROUGH_RADIUS,
                max_radius=1,
                coordinates=(
                    RelaxationCoordinate(
                        name="nick_offset_within_foldback_nt",
                        minimum=0,
                        maximum=1,
                    ),
                ),
            ),
            max_search_nodes=2,
            max_realizations=100,
        )
    )
    assert foldback.neighborhood.status is SearchCompletionStatus.TRUNCATED
    assert foldback.neighborhood.truncation_reasons == ("max_search_nodes",)
    design = _verified_design(tmp_path)
    request = _construction_request(
        payload=payload,
        foldback=foldback,
        basal=None,
        design=design,
        complement_five_prime_end=EndChemistry.HYDROXYL,
        require_all=True,
    )

    result = _discover_raw(request, foldback=foldback, basal=None, design=design)

    assert result.status is SearchCompletionStatus.TRUNCATED
    assert result.truncation_reasons == ()
    assert result.upstream_truncation_reasons == ("foldback:max_search_nodes",)
    assert len(result.realizations) == 1
    assert tuple(item.status for item in result.combination_dispositions) == (
        CompositionDispositionStatus.REJECTED,
        CompositionDispositionStatus.ACCEPTED,
    )
    assert tuple((item.code, item.count) for item in result.failure_reasons) == (
        (CompositionRejectionCode.SOURCE_END_CHEMISTRY_MISMATCH, 1),
    )
