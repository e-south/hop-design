"""
--------------------------------------------------------------------------------
HOP Design
tests/integration/test_complete_construction_discovery.py

Tests exact whole-route composition against verified local and design authorities.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

import hop_design as hop
from hop_design.design.bundle import load_verified_bundle
from hop_design.design.construction.basal import discover_basal_neighborhood
from hop_design.design.construction.complete import discover_constructions
from hop_design.design.construction.complete.discovery import (
    VerifiedConstructionSpaceResult,
    verify_construction_space_result,
)
from hop_design.design.construction.foldback import discover_foldback_neighborhood
from hop_design.design.construction.verification import (
    ConstructionVerificationError,
    VerifiedFoldbackNeighborhoodResult,
    verify_basal_neighborhood_result,
    verify_foldback_neighborhood_result,
)
from hop_design.models.construction import (
    BasalGeometryDomain,
    BasalPairAllowance,
    BasalPairConstraint,
    ConstructionConstraints,
    ConstructionEndpoint,
    FinalPayloadReference,
    FoldbackGeometryDomain,
    FoldbackTarget,
    LocalNeighborhoodFamily,
    LocalNeighborhoodRequest,
    NeighborhoodSearchPlan,
    RouteFamily,
    SearchCompletionStatus,
    SourceOrientation,
)
from hop_design.models.construction.complete import (
    CompositionDispositionStatus,
    CompositionEnumerationPolicy,
    CompositionPruningMode,
    ConstructionDiscoveryRequest,
    DerivedPrimerPolicy,
    DerivedSourceSsdnaPolicy,
    DesignAuthorityReference,
    EndpointAuxiliaryPolicy,
    ExactConstructionMaterial,
    FixedAdapterPolicy,
    FixedEndpointPrimerPolicy,
    FixedPrimerPolicy,
    LinearSourceMaterializationSpec,
    MaterialResolutionMode,
    PcrPrimer,
    SourceDuplexPreparationPolicy,
    TypeIisReleaseRequest,
    WholeRouteConstraints,
)
from hop_design.models.construction.complete.evaluation import (
    CompositionRejectionCode,
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
)
from hop_design.models.junction import Strand
from hop_design.models.molecular_state import EndChemistry, LineageStrand
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
    minimum_adapter_annealing_nt: int = 4,
):
    endpoint = ConstructionEndpoint.HAIRPIN_PCR_DUPLEX
    motif = recognition_pattern or ("TTTT" if nick_strand is Strand.BOTTOM else "AAAA")
    enzyme = CharacterizedEnzyme(
        enzyme_id="example:enzyme/complete-basal@1",
        canonical_name="complete-basal",
        enzyme_class=EnzymeClass.NICKASE,
        target_molecule=TargetMolecule.DNA,
        recognition_pattern=motif,
        recognition_orientation_semantics=(
            RecognitionOrientationSemantics.BOTH_ORIENTATIONS
            if nick_strand is Strand.BOTTOM
            else RecognitionOrientationSemantics.DECLARED_ONLY
        ),
        recognition_length=len(motif),
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
            geometry_domain=BasalGeometryDomain(
                nick_strand=nick_strand,
                nick_offsets_nt=(nick_offset_nt,),
                minimum_adapter_annealing_nt=minimum_adapter_annealing_nt,
                pairing_constraints=(
                    tuple(
                        BasalPairConstraint(
                            position_from_ligation=index,
                            allowed_class=allowed,
                        )
                        for index, allowed in enumerate(
                            pairing_allowances or (BasalPairAllowance.MATCH,) * 4
                        )
                    )
                ),
            ),
            hard_constraints=ConstructionConstraints(),
            enzyme_provisioning=provisioning,
            search=NeighborhoodSearchPlan(
                max_retained_overhead_nt=(2 * len(pairing_allowances or (None,) * 4) + len(motif)),
                max_search_nodes=100,
                max_realizations=100,
            ),
        )
    )


def _material(
    _role: str,
    sequence: str,
    *,
    five_prime_end: EndChemistry = EndChemistry.PHOSPHATE,
    three_prime_end: EndChemistry = EndChemistry.HYDROXYL,
) -> ExactConstructionMaterial:
    return ExactConstructionMaterial(
        sequence_5prime=sequence,
        five_prime_end=five_prime_end,
        three_prime_end=three_prime_end,
    )


def _verified_design(tmp_path: Path, payload: str = "GACA"):
    spec = _component_spec().model_copy(update={"payload": ExactPayload(sequence=payload)})
    return load_verified_bundle(hop.compile(spec).write(tmp_path / "design"))


def _verified_asymmetric_foldback_design(tmp_path: Path):
    data = _component_spec().model_dump(mode="python", by_alias=True)
    data["payload"] = ExactPayload(sequence="GACA")
    data["foldback"] = {
        "precursor_sequence": "ACAAAA",
        "retained_tract_span": {"start": {"offset": 0}, "end": {"offset": 3}},
        "source_turn_span": {"start": {"offset": 3}, "end": {"offset": 6}},
        "protected_region": {"start": {"offset": 0}, "end": {"offset": 0}},
        "turn_extension": "",
        "foldback_arm": "TGT",
        "constraints": {
            "max_non_watson_crick_pairs": 0,
            "terminal_watson_crick_bp_min": 3,
            "terminal_watson_crick_bp_max": 3,
            "max_uninterrupted_watson_crick_bp": 3,
            "max_added_nt": 3,
            "required_turn_nt": 3,
            "allow_protected_region_non_watson_crick_pairs": False,
        },
    }
    spec = type(_component_spec()).model_validate(data)
    return load_verified_bundle(hop.compile(spec).write(tmp_path / "asymmetric-design"))


def _construction_request(
    *,
    payload: FinalPayloadReference,
    foldback,
    basal,
    design,
    require_all: bool = False,
    endpoint: ConstructionEndpoint = ConstructionEndpoint.SSDNA_HAIRPIN,
    adapter: ExactConstructionMaterial | None = None,
    forward_primer: ExactConstructionMaterial | PcrPrimer | None = None,
    reverse_primer: ExactConstructionMaterial | PcrPrimer | None = None,
    source_preparation: SourceDuplexPreparationPolicy | None = None,
    endpoint_auxiliaries: EndpointAuxiliaryPolicy | None = None,
    release: TypeIisReleaseRequest | None = None,
) -> ConstructionDiscoveryRequest:
    encoding = design.plan.hairpin_encoding_insert
    forward = (
        forward_primer
        if isinstance(forward_primer, PcrPrimer)
        else None
        if forward_primer is None
        else PcrPrimer(
            oligo=forward_primer,
            annealing_length_nt=len(forward_primer.sequence_5prime),
        )
    )
    reverse = (
        reverse_primer
        if isinstance(reverse_primer, PcrPrimer)
        else None
        if reverse_primer is None
        else PcrPrimer(
            oligo=reverse_primer,
            annealing_length_nt=len(reverse_primer.sequence_5prime),
        )
    )
    if endpoint_auxiliaries is not None and any(
        item is not None for item in (adapter, forward, reverse)
    ):
        raise ValueError("Test request must use policy or exact auxiliary inputs, not both.")
    if endpoint_auxiliaries is None and any(
        item is not None for item in (adapter, forward, reverse)
    ):
        if adapter is None or forward is None or reverse is None:
            raise ValueError("Exact test auxiliary inputs must be complete.")
        endpoint_auxiliaries = EndpointAuxiliaryPolicy(
            adapter=FixedAdapterPolicy(
                mode=MaterialResolutionMode.FIXED,
                material=adapter,
            ),
            forward_primer=FixedEndpointPrimerPolicy(
                mode=MaterialResolutionMode.FIXED,
                primer=forward,
            ),
            reverse_primer=FixedEndpointPrimerPolicy(
                mode=MaterialResolutionMode.FIXED,
                primer=reverse,
            ),
        )
    return ConstructionDiscoveryRequest(
        payload=payload,
        route_family=RouteFamily.LINEAR_SOURCE_V1,
        endpoint=endpoint,
        foldback_result_id=foldback.result_id,
        basal_result_id=(
            None
            if endpoint is ConstructionEndpoint.SSDNA_HAIRPIN or basal is None
            else basal.result_id
        ),
        materialization=LinearSourceMaterializationSpec(
            source_preparation=source_preparation
            or SourceDuplexPreparationPolicy(
                source_ssdna=DerivedSourceSsdnaPolicy(
                    mode=MaterialResolutionMode.DERIVE,
                    five_prime_end=EndChemistry.HYDROXYL,
                    three_prime_end=EndChemistry.HYDROXYL,
                ),
                forward_primer=DerivedPrimerPolicy(
                    mode=MaterialResolutionMode.DERIVE,
                    annealing_length_nt=1,
                ),
                reverse_primer=DerivedPrimerPolicy(
                    mode=MaterialResolutionMode.DERIVE,
                    annealing_length_nt=1,
                ),
            ),
            endpoint_auxiliaries=endpoint_auxiliaries,
        ),
        release=release,
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
        domain=FoldbackGeometryDomain(
            junction_offsets_nt=(0, 1),
            loop_lengths_nt=(3,),
            annealing_arm_lengths_bp=(3,),
        ),
        max_retained_overhead_nt=11,
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
            source_preparation=SourceDuplexPreparationPolicy(
                source_ssdna=DerivedSourceSsdnaPolicy(
                    mode=MaterialResolutionMode.DERIVE,
                    five_prime_end=EndChemistry.HYDROXYL,
                    three_prime_end=EndChemistry.HYDROXYL,
                ),
                forward_primer=DerivedPrimerPolicy(
                    mode=MaterialResolutionMode.DERIVE,
                    annealing_length_nt=1,
                ),
                reverse_primer=DerivedPrimerPolicy(
                    mode=MaterialResolutionMode.DERIVE,
                    annealing_length_nt=1,
                ),
            ),
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
                junction_offset_nt=0,
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
    )

    result = _discover_raw(request, foldback=foldback, basal=None, design=design)

    assert result.status is SearchCompletionStatus.COMPLETE
    assert result.schema_id == "hop.construction-space-result/v6"
    assert result.provenance.basal_result_id is None
    assert result.accounting.truncated_combinations == 0
    assert result.failure_reasons == ()
    assert result.realizations
    realization = result.realizations[0]
    assert (
        realization.source_preparation.produced_material_bindings[0].material
        == (realization.materials[0])
    )
    assert (
        realization.source_preparation.produced_material_bindings[1].material
        == (realization.materials[1])
    )
    assert realization.source_preparation.payload_source_span == (
        realization.payload_source_map.segments[0].source_span
    )
    assert result.material_accounting.source_material_nt == sum(
        len(item.source_preparation.source_ssdna.sequence_5prime) for item in result.realizations
    )
    assert result.material_accounting.auxiliary_material_nt == sum(
        len(item.source_preparation.forward_primer.oligo.sequence_5prime)
        + len(item.source_preparation.reverse_primer.oligo.sequence_5prime)
        + sum(len(material.sequence_5prime) for material in item.materials[2:])
        for item in result.realizations
    )
    assert all(
        item.final_product.reference.sequence == request.design.encoding_sequence
        for item in result.realizations
    )
    changed = result.combination_dispositions[0].model_copy(
        update={
            "candidate_enzyme_programs": (
                result.combination_dispositions[0].candidate_enzyme_programs + 1
            )
        }
    )
    with pytest.raises(ValidationError, match=r"accounting|combination evaluation"):
        type(result).model_validate(
            result.model_dump(mode="python")
            | {
                "combination_dispositions": (
                    changed,
                    *result.combination_dispositions[1:],
                )
            }
        )


def test_direct_composition_preserves_a_bottom_nick_source_orientation(
    tmp_path: Path,
) -> None:
    payload = FinalPayloadReference(
        payload=ExactPayload(sequence="GACA"),
        basal_boundary=Boundary(offset=0),
        foldback_boundary=Boundary(offset=4),
    )
    foldback = discover_foldback_neighborhood(
        _request(
            _nickase(motif="ACATTT"),
            target=FoldbackTarget(
                nick_strand=Strand.BOTTOM,
                junction_offset_nt=0,
                loop_length_nt=3,
                annealing_arm_length_bp=3,
            ),
        )
    )
    design = _verified_asymmetric_foldback_design(tmp_path)
    request = _construction_request(
        payload=payload,
        foldback=foldback,
        basal=None,
        design=design,
    )

    result = _discover_raw(request, foldback=foldback, basal=None, design=design)

    assert result.status is SearchCompletionStatus.COMPLETE
    assert len(result.realizations) == 1
    realization = result.realizations[0]
    assert tuple(item.sequence_5prime for item in realization.materials[:2]) == (
        "ACAAAATGTTGTCTTTT",
        "AAAAGACAACATTTTGT",
    )
    assert realization.realization.precursor_sequence == "ACAAAATGTTGTCTTTT"
    assert realization.payload_source_map.segments[0].source_span == Span(
        start=Boundary(offset=9),
        end=Boundary(offset=13),
    )
    assert realization.payload_source_map.segments[0].orientation is (
        SourceOrientation.REVERSE_COMPLEMENT
    )
    assert realization.final_product.reference.sequence == "AAAAGACAACAAAATGTTGTCTTTT"
    final = realization.final_product.strands[0]
    assert tuple(
        (item.origin_id, item.origin_strand, item.origin_index) for item in final.lineage[:4]
    ) == tuple(
        (
            realization.material_uses[1].use_id,
            LineageStrand.COMPLEMENTARY,
            index,
        )
        for index in range(4)
    )


def test_direct_composition_preserves_both_physical_source_trajectories(
    tmp_path: Path,
) -> None:
    payload = FinalPayloadReference(
        payload=ExactPayload(sequence="GACA"),
        basal_boundary=Boundary(offset=0),
        foldback_boundary=Boundary(offset=4),
    )
    foldback = discover_foldback_neighborhood(_request(_nickase(motif="ACATTT")))
    design = _verified_asymmetric_foldback_design(tmp_path)
    request = _construction_request(
        payload=payload,
        foldback=foldback,
        basal=None,
        design=design,
    )

    result = _discover_raw(request, foldback=foldback, basal=None, design=design)

    assert result.status is SearchCompletionStatus.COMPLETE
    assert len(result.realizations) == 2
    assert len({item.materialized_realization_id for item in result.realizations}) == 2
    assert {item.realization.precursor_sequence for item in result.realizations} == {
        "AAAA" + "GACAACATTTTGT",
        "ACAAAATGTTGTC" + "TTTT",
    }
    assert {item.final_product.reference.sequence for item in result.realizations} == {
        "AAAAGACAACAAAATGTTGTCTTTT"
    }
    assert {item.payload_source_map.segments[0].orientation for item in result.realizations} == {
        SourceOrientation.FORWARD,
        SourceOrientation.REVERSE_COMPLEMENT,
    }


def test_direct_realization_rejects_resealed_source_orientation_forgery(
    tmp_path: Path,
) -> None:
    payload = FinalPayloadReference(
        payload=ExactPayload(sequence="GACA"),
        basal_boundary=Boundary(offset=0),
        foldback_boundary=Boundary(offset=4),
    )
    foldback = discover_foldback_neighborhood(
        _request(
            _nickase(motif="ACATTT"),
            target=FoldbackTarget(
                nick_strand=Strand.BOTTOM,
                junction_offset_nt=0,
                loop_length_nt=3,
                annealing_arm_length_bp=3,
            ),
        )
    )
    design = _verified_asymmetric_foldback_design(tmp_path)
    request = _construction_request(
        payload=payload,
        foldback=foldback,
        basal=None,
        design=design,
    )
    realization = _discover_raw(
        request,
        foldback=foldback,
        basal=None,
        design=design,
    ).realizations[0]
    segment = realization.payload_source_map.segments[0]
    forged_map = realization.payload_source_map.model_copy(
        update={
            "segments": (segment.model_copy(update={"orientation": SourceOrientation.FORWARD}),)
        }
    )
    content = {
        name: getattr(realization, name)
        for name in type(realization).model_fields
        if name != "materialized_realization_id"
    }

    with pytest.raises(ValidationError, match="Payload source occurrence"):
        type(realization).create(**(content | {"payload_source_map": forged_map}))


def test_bottom_nick_direct_route_rejects_a_fixed_unphosphorylated_source_primer(
    tmp_path: Path,
) -> None:
    payload = FinalPayloadReference(
        payload=ExactPayload(sequence="GACA"),
        basal_boundary=Boundary(offset=0),
        foldback_boundary=Boundary(offset=4),
    )
    foldback = discover_foldback_neighborhood(
        _request(
            _nickase(motif="ACATTT"),
            target=FoldbackTarget(
                nick_strand=Strand.BOTTOM,
                junction_offset_nt=0,
                loop_length_nt=3,
                annealing_arm_length_bp=3,
            ),
        )
    )
    design = _verified_asymmetric_foldback_design(tmp_path)
    request = _construction_request(
        payload=payload,
        foldback=foldback,
        basal=None,
        design=design,
        source_preparation=SourceDuplexPreparationPolicy(
            source_ssdna=DerivedSourceSsdnaPolicy(
                mode=MaterialResolutionMode.DERIVE,
                five_prime_end=EndChemistry.HYDROXYL,
                three_prime_end=EndChemistry.HYDROXYL,
            ),
            forward_primer=FixedPrimerPolicy(
                mode=MaterialResolutionMode.FIXED,
                primer=PcrPrimer(
                    oligo=_material(
                        "fixed-unphosphorylated-forward",
                        "A",
                        five_prime_end=EndChemistry.HYDROXYL,
                    ),
                    annealing_length_nt=1,
                ),
            ),
            reverse_primer=DerivedPrimerPolicy(
                mode=MaterialResolutionMode.DERIVE,
                annealing_length_nt=1,
            ),
        ),
    )

    result = _discover_raw(request, foldback=foldback, basal=None, design=design)

    assert result.status is SearchCompletionStatus.INFEASIBLE
    assert tuple((item.code, item.count) for item in result.failure_reasons) == (
        (CompositionRejectionCode.SOURCE_PREPARATION_INCOMPATIBLE, 1),
    )


def test_complete_composition_rejects_a_fixed_source_primer_crossing_the_payload(
    tmp_path: Path,
) -> None:
    payload = FinalPayloadReference(
        payload=ExactPayload(sequence="GACA"),
        basal_boundary=Boundary(offset=0),
        foldback_boundary=Boundary(offset=4),
    )
    foldback = discover_foldback_neighborhood(
        _request(
            _nickase(motif="ACATTT"),
            target=FoldbackTarget(
                nick_strand=Strand.BOTTOM,
                junction_offset_nt=0,
                loop_length_nt=3,
                annealing_arm_length_bp=3,
            ),
        )
    )
    design = _verified_asymmetric_foldback_design(tmp_path)
    baseline = _discover_raw(
        _construction_request(
            payload=payload,
            foldback=foldback,
            basal=None,
            design=design,
        ),
        foldback=foldback,
        basal=None,
        design=design,
    ).realizations[0]
    source_preparation = baseline.source_preparation
    crossing_length = source_preparation.payload_source_span.start.offset + 1
    source_sequence = source_preparation.source_ssdna.sequence_5prime
    request = _construction_request(
        payload=payload,
        foldback=foldback,
        basal=None,
        design=design,
        source_preparation=SourceDuplexPreparationPolicy(
            source_ssdna=DerivedSourceSsdnaPolicy(
                mode=MaterialResolutionMode.DERIVE,
                five_prime_end=EndChemistry.HYDROXYL,
                three_prime_end=EndChemistry.HYDROXYL,
            ),
            forward_primer=FixedPrimerPolicy(
                mode=MaterialResolutionMode.FIXED,
                primer=PcrPrimer(
                    oligo=_material(
                        "fixed-payload-crossing-forward",
                        source_sequence[:crossing_length],
                    ),
                    annealing_length_nt=crossing_length,
                ),
            ),
            reverse_primer=DerivedPrimerPolicy(
                mode=MaterialResolutionMode.DERIVE,
                annealing_length_nt=1,
            ),
        ),
    )

    result = _discover_raw(request, foldback=foldback, basal=None, design=design)

    assert result.status is SearchCompletionStatus.INFEASIBLE
    assert tuple((item.code, item.count) for item in result.failure_reasons) == (
        (CompositionRejectionCode.SOURCE_PREPARATION_INCOMPATIBLE, 1),
    )


def test_complete_composition_rejects_fixed_source_primer_without_three_prime_hydroxyl(
    tmp_path: Path,
) -> None:
    payload = FinalPayloadReference(
        payload=ExactPayload(sequence="GACA"),
        basal_boundary=Boundary(offset=0),
        foldback_boundary=Boundary(offset=4),
    )
    foldback = discover_foldback_neighborhood(
        _request(
            _nickase(motif="ACATTT"),
            target=FoldbackTarget(
                nick_strand=Strand.BOTTOM,
                junction_offset_nt=0,
                loop_length_nt=3,
                annealing_arm_length_bp=3,
            ),
        )
    )
    design = _verified_asymmetric_foldback_design(tmp_path)
    baseline = _discover_raw(
        _construction_request(
            payload=payload,
            foldback=foldback,
            basal=None,
            design=design,
        ),
        foldback=foldback,
        basal=None,
        design=design,
    ).realizations[0]
    baseline_primer = baseline.source_preparation.forward_primer
    request = _construction_request(
        payload=payload,
        foldback=foldback,
        basal=None,
        design=design,
        source_preparation=SourceDuplexPreparationPolicy(
            source_ssdna=DerivedSourceSsdnaPolicy(
                mode=MaterialResolutionMode.DERIVE,
                five_prime_end=EndChemistry.HYDROXYL,
                three_prime_end=EndChemistry.HYDROXYL,
            ),
            forward_primer=FixedPrimerPolicy(
                mode=MaterialResolutionMode.FIXED,
                primer=PcrPrimer(
                    oligo=ExactConstructionMaterial(
                        sequence_5prime=baseline_primer.oligo.sequence_5prime,
                        five_prime_end=baseline_primer.oligo.five_prime_end,
                        three_prime_end=EndChemistry.PHOSPHATE,
                    ),
                    annealing_length_nt=baseline_primer.annealing_length_nt,
                ),
            ),
            reverse_primer=DerivedPrimerPolicy(
                mode=MaterialResolutionMode.DERIVE,
                annealing_length_nt=1,
            ),
        ),
    )

    result = _discover_raw(request, foldback=foldback, basal=None, design=design)

    assert result.status is SearchCompletionStatus.INFEASIBLE
    assert tuple((item.code, item.count) for item in result.failure_reasons) == (
        (CompositionRejectionCode.SOURCE_PREPARATION_INCOMPATIBLE, 1),
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
                junction_offset_nt=0,
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
        source_preparation=SourceDuplexPreparationPolicy(
            source_ssdna=DerivedSourceSsdnaPolicy(
                mode=MaterialResolutionMode.DERIVE,
                five_prime_end=EndChemistry.HYDROXYL,
                three_prime_end=EndChemistry.HYDROXYL,
            ),
            forward_primer=DerivedPrimerPolicy(
                mode=MaterialResolutionMode.DERIVE,
                annealing_length_nt=1,
            ),
            reverse_primer=FixedPrimerPolicy(
                mode=MaterialResolutionMode.FIXED,
                primer=PcrPrimer(
                    oligo=_material(
                        "fixed-unphosphorylated-reverse",
                        "A",
                        five_prime_end=EndChemistry.HYDROXYL,
                    ),
                    annealing_length_nt=1,
                ),
            ),
        ),
        require_all=True,
    )

    result = _discover_raw(request, foldback=foldback, basal=None, design=design)

    assert result.status is SearchCompletionStatus.INFEASIBLE
    assert result.realizations == ()
    assert tuple((item.code, item.count) for item in result.failure_reasons) == (
        (
            CompositionRejectionCode.SOURCE_PREPARATION_INCOMPATIBLE,
            len(foldback.realizations),
        ),
    )


def test_source_copy_rejects_a_noncomplementary_optional_stem_extension(
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
                junction_offset_nt=0,
                loop_length_nt=3,
                annealing_arm_length_bp=4,
            ),
        )
    )
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
        basal=None,
        design=design,
    )

    result = _discover_raw(request, foldback=foldback, basal=None, design=design)

    assert result.status is SearchCompletionStatus.INFEASIBLE
    assert result.realizations == ()
    assert all(
        item.rejection_reason is CompositionRejectionCode.SOURCE_PREPARATION_INCOMPATIBLE
        for item in result.combination_dispositions
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
                junction_offset_nt=0,
                loop_length_nt=3,
                annealing_arm_length_bp=4,
            ),
            domain=FoldbackGeometryDomain(
                junction_offsets_nt=(0, 1),
                loop_lengths_nt=(3,),
                annealing_arm_lengths_bp=(4,),
            ),
            max_retained_overhead_nt=13,
            max_search_nodes=2,
            max_realizations=100,
        )
    )
    assert foldback.neighborhood.disposition.completion is SearchCompletionStatus.TRUNCATED
    assert foldback.neighborhood.disposition.termination_reason.value == "evaluation_cap"
    design = _verified_design(tmp_path)
    request = _construction_request(
        payload=payload,
        foldback=foldback,
        basal=None,
        design=design,
        require_all=True,
    )

    result = _discover_raw(request, foldback=foldback, basal=None, design=design)

    assert result.status is SearchCompletionStatus.TRUNCATED
    assert result.truncation_reasons == ()
    assert result.upstream_truncation_reasons == ("foldback:evaluation_cap",)
    assert len(result.realizations) == 2
    assert tuple(item.status for item in result.combination_dispositions) == (
        CompositionDispositionStatus.ACCEPTED,
        CompositionDispositionStatus.ACCEPTED,
    )
    assert result.failure_reasons == ()
