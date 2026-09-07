"""
--------------------------------------------------------------------------------
HOP Design
tests/contract/test_complete_construction_contracts.py

Tests exact whole-route materialization and composition request contracts.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import hashlib
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

import hop_design as hop
from hop_design.design.construction.complete.lineage import (
    MaterialOccurrence,
    foldback_occurrences,
    reaction_molecule_strands,
    whole_source_occurrences,
)
from hop_design.models.construction import (
    ConstructionEndpoint,
    FinalPayloadReference,
    RealizationGroup,
    RealizationGrouping,
    RouteFamily,
    SourceOrientation,
)
from hop_design.models.construction.complete import (
    CompositionAccounting,
    CompositionDisposition,
    CompositionDispositionStatus,
    CompositionEnumerationPolicy,
    CompositionPruningMode,
    ConstructionBondState,
    ConstructionDiscoveryRequest,
    ConstructionProgram,
    ConstructionState,
    ConstructionStatePhase,
    ConstructionTransition,
    ConstructionTransitionKind,
    DerivedPrimerPolicy,
    DerivedSourceSsdnaPolicy,
    DesignAuthorityReference,
    EndpointAuxiliaryPolicy,
    ExactConstructionMaterial,
    ExactStateRelation,
    FixedAdapterPolicy,
    FixedEndpointPrimerPolicy,
    LinearSourceMaterializationSpec,
    MaterialResolutionMode,
    MaterialRouteEntry,
    MaterialUse,
    MaterialUseRole,
    PcrPrimer,
    ReactionBoundaryMapping,
    ReleaseSideRequirement,
    SourceDuplexPreparationPolicy,
    TypeIisReleaseRequest,
    WholeRouteConstraints,
)
from hop_design.models.construction.complete.accounting import validate_realization_groups
from hop_design.models.construction.complete.evaluation_inputs import LinearSourceEmbedding
from hop_design.models.construction.complete.materials import validate_initial_material_state
from hop_design.models.construction.payload import _content_id
from hop_design.models.coordinates import Boundary
from hop_design.models.junction import JunctionPairKind
from hop_design.models.molecular_state import (
    CovalentBond,
    EndChemistry,
    LineageStrand,
    MaterialBaseLineage,
    MolecularStrand,
    StrandEnd,
    StrandPairObservation,
)
from hop_design.models.payload import ExactPayload
from hop_design.models.physical import SiteOrientation
from hop_design.models.plan import HopPlan
from hop_design.models.reactions import ReactionMolecule
from hop_design.models.references import ExternalRef
from tests.contract.test_endpoint_materialization import _release_policy
from tests.integration.test_resolved_compile import _component_spec


def _digest(sequence: str) -> str:
    return f"sha256:{hashlib.sha256(sequence.encode()).hexdigest()}"


def _payload() -> FinalPayloadReference:
    return FinalPayloadReference(
        payload=ExactPayload(sequence="GACA"),
        basal_boundary=Boundary(offset=0),
        foldback_boundary=Boundary(offset=4),
    )


def _material(_role: str, sequence: str) -> ExactConstructionMaterial:
    return ExactConstructionMaterial(
        sequence_5prime=sequence,
        five_prime_end=EndChemistry.PHOSPHATE,
        three_prime_end=EndChemistry.HYDROXYL,
    )


def _prepared_material_uses(
    source: ExactConstructionMaterial,
    complement: ExactConstructionMaterial,
) -> tuple[MaterialUse, MaterialUse]:
    return (
        MaterialUse.create(
            material_id=source.material_id,
            role=MaterialUseRole.PREPARED_SOURCE_REFERENCE,
            specification_resolution_mode=MaterialResolutionMode.DERIVE,
            route_entry=MaterialRouteEntry.MODELED_PRODUCT,
        ),
        MaterialUse.create(
            material_id=complement.material_id,
            role=MaterialUseRole.PREPARED_SOURCE_COMPLEMENT,
            specification_resolution_mode=MaterialResolutionMode.DERIVE,
            route_entry=MaterialRouteEntry.MODELED_PRODUCT,
        ),
    )


def _design() -> DesignAuthorityReference:
    compilation = hop.compile(
        _component_spec().model_copy(update={"payload": ExactPayload(sequence="GACA")})
    )
    plan = compilation.plan
    sequence = plan.hairpin_encoding_insert.sequence
    return DesignAuthorityReference(
        bundle=compilation.bundle,
        spec=compilation.spec,
        plan=plan,
        plan_id=plan.plan_id,
        design_id=plan.design_id,
        payload_sequence="GACA",
        encoding_sequence=sequence,
        encoding_digest=plan.hairpin_encoding_insert.sequence_digest,
    )


def _request(endpoint: ConstructionEndpoint) -> ConstructionDiscoveryRequest:
    materialization = LinearSourceMaterializationSpec(
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
        endpoint_auxiliaries=(
            None
            if endpoint is ConstructionEndpoint.SSDNA_HAIRPIN
            else EndpointAuxiliaryPolicy(
                adapter=FixedAdapterPolicy(
                    mode=MaterialResolutionMode.FIXED,
                    material=_material("adapter", "AGTC"),
                ),
                forward_primer=FixedEndpointPrimerPolicy(
                    mode=MaterialResolutionMode.FIXED,
                    primer=PcrPrimer(
                        oligo=_material("forward-primer", "GGACA"),
                        annealing_length_nt=5,
                    ),
                ),
                reverse_primer=FixedEndpointPrimerPolicy(
                    mode=MaterialResolutionMode.FIXED,
                    primer=PcrPrimer(
                        oligo=_material("reverse-primer", "GGACA"),
                        annealing_length_nt=5,
                    ),
                ),
            )
        ),
    )
    return ConstructionDiscoveryRequest(
        payload=_payload(),
        route_family=RouteFamily.LINEAR_SOURCE_V1,
        endpoint=endpoint,
        foldback_result_id="hop:foldback-neighborhood-result/" + "a" * 64 + "@1",
        basal_result_id=(
            None
            if endpoint is ConstructionEndpoint.SSDNA_HAIRPIN
            else "hop:basal-neighborhood-result/" + "b" * 64 + "@1"
        ),
        materialization=materialization,
        release=(
            TypeIisReleaseRequest(
                enzyme_provisioning=_release_policy(),
                left=ReleaseSideRequirement(
                    orientation=SiteOrientation.FORWARD,
                    cohesive_end_sequence="AATG",
                    overhang_end=StrandEnd.FIVE_PRIME,
                ),
                right=ReleaseSideRequirement(
                    orientation=SiteOrientation.REVERSE,
                    cohesive_end_sequence="CGCT",
                    overhang_end=StrandEnd.FIVE_PRIME,
                ),
                max_site_pairs=16,
            )
            if endpoint is ConstructionEndpoint.CLONE_READY_DUPLEX
            else None
        ),
        design=_design(),
        whole_route_constraints=WholeRouteConstraints(),
        enumeration=CompositionEnumerationPolicy(
            pruning=CompositionPruningMode.DISABLED,
            max_combinations=100,
            max_realizations=100,
        ),
    )


def test_direct_endpoint_forbids_adapter_and_pcr_materials() -> None:
    direct = _request(ConstructionEndpoint.SSDNA_HAIRPIN)
    assert direct.schema_id == "hop.construction-discovery-request/v5"
    assert direct.model_dump(mode="json", by_alias=True)["schema"] == direct.schema_id
    assert direct.basal_result_id is None
    assert direct.materialization.endpoint_auxiliaries is None

    data = direct.model_dump(mode="python")
    data["materialization"]["endpoint_auxiliaries"] = _request(
        ConstructionEndpoint.HAIRPIN_PCR_DUPLEX
    ).materialization.endpoint_auxiliaries
    with pytest.raises(ValidationError, match="must omit endpoint auxiliaries"):
        ConstructionDiscoveryRequest.model_validate(data)


def test_direct_endpoint_rejects_a_basal_discovery() -> None:
    direct = _request(ConstructionEndpoint.SSDNA_HAIRPIN)
    data = direct.model_dump(mode="python")
    data["basal_result_id"] = "hop:basal-neighborhood-result/" + "b" * 64 + "@1"

    with pytest.raises(ValidationError, match="direct endpoint must omit basal authority"):
        ConstructionDiscoveryRequest.model_validate(data)


def test_complete_request_declares_foldback_ssdna_as_an_intermediate_not_final_endpoint() -> None:
    clone = _request(ConstructionEndpoint.CLONE_READY_DUPLEX)

    assert clone.foldback_intermediate_endpoint is ConstructionEndpoint.SSDNA_HAIRPIN
    assert clone.endpoint is ConstructionEndpoint.CLONE_READY_DUPLEX

    data = clone.model_dump(mode="python")
    data["foldback_intermediate_endpoint"] = ConstructionEndpoint.HAIRPIN_PCR_DUPLEX
    with pytest.raises(ValidationError, match="foldback intermediate"):
        ConstructionDiscoveryRequest.model_validate(data)


def test_complete_request_rejects_payload_drift_from_design_authority() -> None:
    data = _request(ConstructionEndpoint.SSDNA_HAIRPIN).model_dump(mode="python")
    data["payload"]["payload"]["sequence"] = "GACT"

    with pytest.raises(ValidationError, match="bind the exact requested payload"):
        ConstructionDiscoveryRequest.model_validate(data)


@pytest.mark.parametrize(
    ("endpoint", "updates", "message"),
    (
        (
            ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
            {"selected_basal_realization_id": "hop:basal-realization/" + "b" * 64 + "@1"},
            "selected basal realization requires a selected foldback",
        ),
        (
            ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
            {"selected_foldback_realization_id": "hop:foldback-realization/" + "a" * 64 + "@1"},
            "requires both local realization ids",
        ),
        (
            ConstructionEndpoint.SSDNA_HAIRPIN,
            {
                "selected_foldback_realization_id": ("hop:foldback-realization/" + "a" * 64 + "@1"),
                "selected_basal_realization_id": ("hop:basal-realization/" + "b" * 64 + "@1"),
            },
            "direct endpoint must omit a selected basal realization",
        ),
    ),
)
def test_selected_local_realizations_obey_endpoint_pairing(
    endpoint: ConstructionEndpoint,
    updates: dict[str, str],
    message: str,
) -> None:
    data = _request(endpoint).model_dump(mode="python")
    data.update(updates)

    with pytest.raises(ValidationError, match=message):
        ConstructionDiscoveryRequest.model_validate(data)


@pytest.mark.parametrize(
    "endpoint",
    (ConstructionEndpoint.HAIRPIN_PCR_DUPLEX, ConstructionEndpoint.CLONE_READY_DUPLEX),
)
def test_pcr_bearing_endpoints_require_basal_and_auxiliary_policies(
    endpoint: ConstructionEndpoint,
) -> None:
    request = _request(endpoint)
    assert request.basal_result_id is not None

    data = request.model_dump(mode="python")
    data["materialization"]["endpoint_auxiliaries"] = None
    with pytest.raises(ValidationError, match="require endpoint auxiliary policies"):
        ConstructionDiscoveryRequest.model_validate(data)


def test_pcr_and_clone_endpoints_enforce_release_ownership() -> None:
    pcr = _request(ConstructionEndpoint.HAIRPIN_PCR_DUPLEX).model_dump(mode="python")
    pcr["release"] = _request(ConstructionEndpoint.CLONE_READY_DUPLEX).release
    with pytest.raises(ValidationError, match="hairpin PCR endpoint must omit clone release"):
        ConstructionDiscoveryRequest.model_validate(pcr)

    clone = _request(ConstructionEndpoint.CLONE_READY_DUPLEX).model_dump(mode="python")
    clone["release"] = None
    with pytest.raises(ValidationError, match="clone-ready endpoint requires"):
        ConstructionDiscoveryRequest.model_validate(clone)


def test_release_side_requires_a_dna_string() -> None:
    with pytest.raises(ValidationError, match="Cohesive-end sequence must be a DNA string"):
        ReleaseSideRequirement(
            orientation=SiteOrientation.FORWARD,
            cohesive_end_sequence=123,
            overhang_end=StrandEnd.FIVE_PRIME,
        )


def test_material_and_design_authorities_are_sequence_and_digest_exact() -> None:
    request = _request(ConstructionEndpoint.SSDNA_HAIRPIN)
    assert request.design.encoding_digest == _digest(request.design.encoding_sequence)

    design = request.design.model_dump(mode="python")
    design["encoding_sequence"] = "AGACAGTTTCTGTCC"
    with pytest.raises(ValidationError, match="digest must match"):
        DesignAuthorityReference.model_validate(design)

    changed_plan = hop.compile(
        _component_spec()
        .model_copy(update={"payload": ExactPayload(sequence="GACA")})
        .model_copy(
            update={
                "stem_extension": hop.PairedStemExtensionRequest(
                    left_arm="GCTA",
                    right_arm="TAAC",
                )
            }
        )
    ).plan
    with pytest.raises(ValidationError, match="model-layer HOP plan"):
        DesignAuthorityReference.model_validate(
            request.design.model_dump(mode="python") | {"plan": changed_plan}
        )

    plan_data = request.design.plan.model_dump(mode="python")
    plan_data["lock"]["compiler_version"] = "forged-compiler"
    with pytest.raises(ValidationError, match="plan identity"):
        HopPlan.model_validate(plan_data)

    spec_data = request.design.spec.model_dump(mode="python")
    spec_data["design_id"] = "forged-design"
    with pytest.raises(ValidationError, match="exact authored design specification"):
        DesignAuthorityReference.model_validate(
            request.design.model_dump(mode="python") | {"spec": spec_data}
        )

    spec_data = request.design.spec.model_dump(mode="python")
    spec_data["defaults_ref"] = "hop:defaults/forged@1"
    with pytest.raises(ValidationError, match="exact authored design specification"):
        DesignAuthorityReference.model_validate(
            request.design.model_dump(mode="python") | {"spec": spec_data}
        )

    spec_data = request.design.spec.model_dump(mode="python")
    spec_data["payload"] = ExactPayload(sequence="GACT")
    with pytest.raises(ValidationError, match="exact authored design specification"):
        DesignAuthorityReference.model_validate(
            request.design.model_dump(mode="python") | {"spec": spec_data}
        )

    spec_data = request.design.spec.model_dump(mode="python")
    spec_data["external_refs"] = (
        ExternalRef(system="test", kind="forged", id="unexpected-source"),
    )
    with pytest.raises(ValidationError, match="exact authored design specification"):
        DesignAuthorityReference.model_validate(
            request.design.model_dump(mode="python") | {"spec": spec_data}
        )

    for bundle_update in (
        {"bundle_id": "hop:bundle/invented/0000000000000000"},
        {"manifest_digest": "sha256:" + "0" * 64},
        {"plan_digest": "sha256:" + "0" * 64},
    ):
        with pytest.raises(
            ValidationError,
            match=r"manifest and root identity|model-layer HOP plan",
        ):
            DesignAuthorityReference.model_validate(
                request.design.model_dump(mode="python")
                | {"bundle": request.design.bundle.model_copy(update=bundle_update)}
            )

    source = _material("source", "GACA").model_dump(mode="python")
    source["sequence_5prime"] = "NNNN"
    with pytest.raises(ValidationError):
        ExactConstructionMaterial.model_validate(source)
    with pytest.raises(ValidationError, match="DNA sequence must be a string"):
        ExactConstructionMaterial.model_validate(source | {"sequence_5prime": 123})

    with pytest.raises(ValidationError, match="must be a DNA string"):
        DesignAuthorityReference.model_validate(
            request.design.model_dump(mode="python") | {"payload_sequence": 123}
        )

    shared_material = _material("shared", "AAAA")
    shared_auxiliary = LinearSourceMaterializationSpec(
        source_preparation=request.materialization.source_preparation,
        endpoint_auxiliaries=EndpointAuxiliaryPolicy(
            adapter=FixedAdapterPolicy(
                mode=MaterialResolutionMode.FIXED,
                material=shared_material,
            ),
            forward_primer=FixedEndpointPrimerPolicy(
                mode=MaterialResolutionMode.FIXED,
                primer=PcrPrimer(oligo=shared_material, annealing_length_nt=4),
            ),
            reverse_primer=FixedEndpointPrimerPolicy(
                mode=MaterialResolutionMode.FIXED,
                primer=PcrPrimer(oligo=shared_material, annealing_length_nt=4),
            ),
        ),
    ).model_dump(mode="python")
    parsed = LinearSourceMaterializationSpec.model_validate(shared_auxiliary)
    assert parsed.endpoint_auxiliaries is not None
    adapter_policy = parsed.endpoint_auxiliaries.adapter
    forward_policy = parsed.endpoint_auxiliaries.forward_primer
    assert isinstance(adapter_policy, FixedAdapterPolicy)
    assert isinstance(forward_policy, FixedEndpointPrimerPolicy)
    assert adapter_policy.material == forward_policy.primer.oligo


def test_complete_identity_bearing_groups_require_canonical_key_order() -> None:
    realizations = (
        SimpleNamespace(materialized_realization_id="route-z", geometry_ids=("z",)),
        SimpleNamespace(materialized_realization_id="route-a", geometry_ids=("a",)),
    )
    groups = tuple(
        RealizationGroup(
            grouping=RealizationGrouping.ACHIEVED_GEOMETRY,
            group_key=_content_id("geometry", 1, item.geometry_ids),
            realization_ids=(item.materialized_realization_id,),
            multiplicity=1,
        )
        for item in realizations
    )
    reversed_groups = tuple(sorted(groups, key=lambda item: item.group_key, reverse=True))

    with pytest.raises(ValueError, match="canonical key order"):
        validate_realization_groups(
            reversed_groups,
            realizations,
            RealizationGrouping.ACHIEVED_GEOMETRY,
        )


def test_linear_source_policy_declares_preparation_without_preselecting_sequence() -> None:
    policy = LinearSourceMaterializationSpec(
        source_preparation=SourceDuplexPreparationPolicy(
            source_ssdna=DerivedSourceSsdnaPolicy(
                mode=MaterialResolutionMode.DERIVE,
                five_prime_end=EndChemistry.PHOSPHATE,
                three_prime_end=EndChemistry.HYDROXYL,
            ),
            forward_primer=DerivedPrimerPolicy(
                mode=MaterialResolutionMode.DERIVE,
                annealing_length_nt=8,
            ),
            reverse_primer=DerivedPrimerPolicy(
                mode=MaterialResolutionMode.DERIVE,
                annealing_length_nt=8,
            ),
        ),
    )

    assert not hasattr(policy.source_preparation.source_ssdna, "material")


def test_composition_policy_is_finite_and_pruning_is_closed() -> None:
    for pruning in CompositionPruningMode:
        policy = CompositionEnumerationPolicy(
            pruning=pruning,
            max_combinations=1,
            max_realizations=1,
        )
        assert policy.max_combinations == 1

    with pytest.raises(ValidationError):
        CompositionEnumerationPolicy(
            pruning="heuristic",
            max_combinations=1,
            max_realizations=1,
        )


@pytest.mark.parametrize(
    "field",
    ("preserve_payload", "reject_unintended_actionable_sites", "require_exact_materials"),
)
def test_v1_whole_route_constraints_reject_unsupported_false_switches(field: str) -> None:
    with pytest.raises(ValidationError):
        WholeRouteConstraints.model_validate({field: False})


def test_reaction_lineage_uses_declared_occurrence_for_repeated_subsequences() -> None:
    source = _material("source", "AAAAAAAA")
    complement = _material("source-complement", "TTTTTTTT")
    source_use, complement_use = _prepared_material_uses(source, complement)
    strands = reaction_molecule_strands(
        ReactionMolecule(
            molecule_id="top-4-8",
            reference_sequence_5prime="AAAA",
            complement_sequence_5prime=None,
        ),
        namespace="repeated",
        source=source,
        source_complement=complement,
        reference_occurrence=MaterialOccurrence(
            start=4,
            length=4,
            five_prime_end=EndChemistry.PHOSPHATE,
            three_prime_end=EndChemistry.HYDROXYL,
            origin_strand=LineageStrand.PRIMARY,
        ),
        complement_occurrence=None,
        source_use_id=source_use.use_id,
        source_complement_use_id=complement_use.use_id,
    )

    assert tuple(item.origin_index for item in strands[0].lineage) == (4, 5, 6, 7)


def test_reaction_lineage_requires_contextual_material_use_ids() -> None:
    source = _material("source", "AAAAAAAA")
    complement = _material("source-complement", "TTTTTTTT")

    with pytest.raises(TypeError):
        reaction_molecule_strands(
            ReactionMolecule(
                molecule_id="top-4-8",
                reference_sequence_5prime="AAAA",
                complement_sequence_5prime=None,
            ),
            namespace="repeated",
            source=source,
            source_complement=complement,
            reference_occurrence=MaterialOccurrence(
                start=4,
                length=4,
                five_prime_end=EndChemistry.PHOSPHATE,
                three_prime_end=EndChemistry.HYDROXYL,
                origin_strand=LineageStrand.PRIMARY,
            ),
            complement_occurrence=None,
        )


def _strand(strand_id: str, sequence: str) -> MolecularStrand:
    return MolecularStrand(
        strand_id=strand_id,
        sequence=sequence,
        five_prime_end=EndChemistry.PHOSPHATE,
        three_prime_end=EndChemistry.HYDROXYL,
        lineage=tuple(
            MaterialBaseLineage(
                product_index=index,
                origin_id="source",
                origin_strand=LineageStrand.PRIMARY,
                origin_index=index,
            )
            for index in range(len(sequence))
        ),
    )


def test_construction_program_separates_enzyme_phases_from_exact_state_relations() -> None:
    released = ConstructionState.create(
        molecules=(_strand("retained", "GACA"), _strand("released", "GACT")),
        phase=ConstructionStatePhase.DENATURED_FRAGMENTS,
    )
    fragments = ConstructionState.create(
        molecules=(_strand("retained", "GACA"),),
        phase=ConstructionStatePhase.SELECTED_FRAGMENTS,
    )
    selection_relation = ExactStateRelation.create(
        pre_state_id=released.state_id,
        post_state_id=fragments.state_id,
    )
    program = ConstructionProgram.create(
        states=(released, fragments),
        transitions=(
            ConstructionTransition.create(
                kind=ConstructionTransitionKind.FRAGMENT_SELECTION,
                pre_state_id=released.state_id,
                post_state_id=fragments.state_id,
                exact_relation=selection_relation,
            ),
        ),
        reaction_programs=(),
        stage_assessments=(),
    )

    assert tuple(item.kind for item in program.transitions) == (
        ConstructionTransitionKind.FRAGMENT_SELECTION,
    )
    assert program.program_id.startswith("hop:construction-program/")


def test_construction_program_rejects_gaps_and_wrong_transition_authority() -> None:
    first = ConstructionState.create(molecules=(_strand("first", "GACA"),))
    second = ConstructionState.create(molecules=(_strand("second", "GACA"),))
    relation = ExactStateRelation.create(
        pre_state_id=first.state_id,
        post_state_id=second.state_id,
    )
    with pytest.raises(ValidationError, match="non-enzyme transition"):
        ConstructionTransition.create(
            kind=ConstructionTransitionKind.ANNEALING,
            pre_state_id=first.state_id,
            post_state_id=second.state_id,
            reaction_program_id="enzyme-phase",
            exact_relation=relation,
        )

    third = ConstructionState.create(molecules=(_strand("third", "GACT"),))
    skipped_relation = ExactStateRelation.create(
        pre_state_id=first.state_id,
        post_state_id=third.state_id,
    )
    skipped = ConstructionTransition.create(
        kind=ConstructionTransitionKind.ANNEALING,
        pre_state_id=first.state_id,
        post_state_id=third.state_id,
        exact_relation=skipped_relation,
    )
    with pytest.raises(ValidationError, match="connect consecutive states"):
        ConstructionProgram.create(
            states=(first, second),
            transitions=(skipped,),
            reaction_programs=(),
            stage_assessments=(),
        )


def test_construction_transition_authorities_are_exact_and_state_changing() -> None:
    first = ConstructionState.create(molecules=(_strand("first-authority", "GACA"),))
    second = ConstructionState.create(molecules=(_strand("second-authority", "GACT"),))
    relation = ExactStateRelation.create(
        pre_state_id=first.state_id,
        post_state_id=second.state_id,
    )
    with pytest.raises(ValidationError, match="identity must seal"):
        ExactStateRelation.model_validate(
            relation.model_dump(mode="python")
            | {"relation_id": "hop:state-relation/" + "0" * 64 + "@1"}
        )
    with pytest.raises(ValidationError, match="must change"):
        ExactStateRelation.create(
            pre_state_id=first.state_id,
            post_state_id=first.state_id,
        )

    mapping = ReactionBoundaryMapping.create(
        reaction_program_id="reaction-program",
        pre_state_id=first.state_id,
        post_state_id=second.state_id,
        pre_strands=first.molecules,
        post_strands=second.molecules,
    )
    with pytest.raises(ValidationError, match="identity must seal"):
        ReactionBoundaryMapping.model_validate(
            mapping.model_dump(mode="python")
            | {"mapping_id": "hop:reaction-boundary-mapping/" + "0" * 64 + "@1"}
        )
    with pytest.raises(ValidationError, match="requires a ReactionProgram"):
        ConstructionTransition.create(
            kind=ConstructionTransitionKind.ENZYME_PHASE,
            pre_state_id=first.state_id,
            post_state_id=second.state_id,
        )
    with pytest.raises(ValidationError, match="bind the transition authority"):
        ConstructionTransition.create(
            kind=ConstructionTransitionKind.ENZYME_PHASE,
            pre_state_id=first.state_id,
            post_state_id=second.state_id,
            reaction_program_id="other-program",
            reaction_boundary_mapping=mapping,
        )
    unchanged_mapping = ReactionBoundaryMapping.create(
        reaction_program_id="reaction-program",
        pre_state_id=first.state_id,
        post_state_id=second.state_id,
        pre_strands=first.molecules,
        post_strands=first.molecules,
    )
    with pytest.raises(ValidationError, match="must change the exact molecular state"):
        ConstructionTransition.create(
            kind=ConstructionTransitionKind.ENZYME_PHASE,
            pre_state_id=first.state_id,
            post_state_id=second.state_id,
            reaction_program_id="reaction-program",
            reaction_boundary_mapping=unchanged_mapping,
        )
    with pytest.raises(ValidationError, match="bind the transition boundaries"):
        ConstructionTransition.create(
            kind=ConstructionTransitionKind.ANNEALING,
            pre_state_id=first.state_id,
            post_state_id=second.state_id,
            exact_relation=ExactStateRelation.create(
                pre_state_id=second.state_id,
                post_state_id=first.state_id,
            ),
        )


@pytest.mark.parametrize(
    ("updates", "message"),
    (
        ({"executed_combinations": 0}, "Executed and examined"),
        ({"rejected_after_execution": 1}, "Post-execution rejection"),
        ({"valid_realizations": 0}, "partition into rejected, truncated, and valid"),
        ({"nominal_combinations": 0}, "cannot exceed the nominal"),
        (
            {"nominal_combinations": 1, "pruned_before_execution": 1},
            "Pruned and executed",
        ),
    ),
)
def test_composition_accounting_rejects_nonreplayable_counts(
    updates: dict[str, int], message: str
) -> None:
    content = {
        "foldback_local_realizations": 1,
        "basal_local_realizations": 1,
        "nominal_combinations": 1,
        "pruned_before_execution": 0,
        "executed_combinations": 1,
        "examined_combinations": 1,
        "rejected_after_execution": 0,
        "rejected_combinations": 0,
        "truncated_combinations": 0,
        "valid_realizations": 1,
        "candidate_enzyme_programs": 1,
        "recognition_placements_attempted": 1,
        "constraint_systems_attempted": 1,
        "distinct_geometry_groups": 1,
        "distinct_final_products": 1,
    }
    content.update(updates)
    with pytest.raises(ValidationError, match=message):
        CompositionAccounting.model_validate(content)


def _pair(left_id: str, right_id: str) -> StrandPairObservation:
    return StrandPairObservation(
        left_index=0,
        right_index=0,
        left_base="G",
        right_base="C",
        kind=JunctionPairKind.WATSON_CRICK,
        left_strand_id=left_id,
        right_strand_id=right_id,
    )


def test_construction_states_reject_incoherent_associations_and_identity() -> None:
    left = _strand("left", "G")
    right = _strand("right", "C")
    pair = _pair(left.strand_id, right.strand_id)
    duplex = ConstructionState.create(
        molecules=(left, right),
        phase=ConstructionStatePhase.DUPLEX,
        pairings=(pair,),
    )
    bond = CovalentBond(
        upstream_strand_id="left",
        upstream_end=StrandEnd.THREE_PRIME,
        downstream_strand_id="right",
        downstream_end=StrandEnd.FIVE_PRIME,
    )
    invalid_cases = (
        ({"molecules": (left, left)}, "strand ids must be unique"),
        (
            {"pairings": (pair.model_copy(update={"right_strand_id": "absent"}),)},
            "reference present strands",
        ),
        (
            {"pairings": (pair.model_copy(update={"right_index": 1}),)},
            "replay exact strand bases",
        ),
        (
            {"formed_bonds": (ConstructionBondState(bond=bond, product_strand_id="absent"),)},
            "reference their present product",
        ),
        ({"pairings": ()}, "paired construction phase"),
        (
            {"phase": ConstructionStatePhase.DENATURED_FRAGMENTS},
            "must not retain base associations",
        ),
        ({"phase": ConstructionStatePhase.LIGATED_PRODUCT}, "formed-bond evidence"),
        ({"state_id": "hop:construction-state/" + "0" * 64 + "@1"}, "identity must seal"),
    )
    for updates, message in invalid_cases:
        with pytest.raises(ValidationError, match=message):
            ConstructionState.model_validate(duplex.model_dump(mode="python") | updates)

    with pytest.raises(ValidationError, match="distinct from both precursor"):
        ConstructionBondState(bond=bond, product_strand_id="left")


def test_lineage_mapping_rejects_missing_or_inexact_material_occurrences() -> None:
    source = _material("source", "AAAACCCC")
    complement = _material("source-complement", "GGGGTTTT")
    source_use, complement_use = _prepared_material_uses(source, complement)
    molecule = ReactionMolecule(
        molecule_id="duplex",
        reference_sequence_5prime="AAAA",
        complement_sequence_5prime="TTTT",
    )
    occurrence = MaterialOccurrence(
        start=0,
        length=4,
        five_prime_end=EndChemistry.PHOSPHATE,
        three_prime_end=EndChemistry.HYDROXYL,
        origin_strand=LineageStrand.PRIMARY,
    )
    with pytest.raises(ValueError, match="exact complement occurrence"):
        reaction_molecule_strands(
            molecule,
            namespace="missing",
            source=source,
            source_complement=complement,
            reference_occurrence=occurrence,
            complement_occurrence=None,
            source_use_id=source_use.use_id,
            source_complement_use_id=complement_use.use_id,
        )
    for start, message in ((6, "lie within"), (4, "replay the exact material bytes")):
        with pytest.raises(ValueError, match=message):
            reaction_molecule_strands(
                ReactionMolecule(
                    molecule_id="fragment",
                    reference_sequence_5prime="AAAA",
                    complement_sequence_5prime=None,
                ),
                namespace="invalid",
                source=source,
                source_complement=complement,
                reference_occurrence=MaterialOccurrence(
                    start=start,
                    length=4,
                    five_prime_end=EndChemistry.PHOSPHATE,
                    three_prime_end=EndChemistry.HYDROXYL,
                    origin_strand=LineageStrand.PRIMARY,
                ),
                complement_occurrence=None,
                source_use_id=source_use.use_id,
                source_complement_use_id=complement_use.use_id,
            )
    with pytest.raises(ValueError, match="preserve the complete exact source duplex"):
        whole_source_occurrences(
            (molecule,),
            source=source,
            source_complement=complement,
        )
    with pytest.raises(ValueError, match="lacks an exact fragment authority"):
        foldback_occurrences(
            (
                ReactionMolecule(
                    molecule_id="unmapped-fragment",
                    reference_sequence_5prime="AAAA",
                    complement_sequence_5prime=None,
                ),
            ),
            fragments=(),
            embedding=LinearSourceEmbedding(
                source_sequence=source.sequence_5prime,
                complement_sequence=complement.sequence_5prime,
                local_reference_offset=0,
                local_complement_offset=0,
                local_source_length=len(source.sequence_5prime),
                source_orientation=SourceOrientation.FORWARD,
            ),
            source=source,
            source_complement=complement,
        )


def test_initial_material_state_replays_duplex_shape_and_phase() -> None:
    source = _material("source", "GACA")
    complement = _material("source-complement", "TGTC")
    single = ConstructionState.create(molecules=(_strand("source", "GACA"),))
    with pytest.raises(ValueError, match="requires two exact source strands"):
        validate_initial_material_state(single, (source,))

    denatured = ConstructionState.create(
        molecules=(
            _strand("source", "GACA"),
            _strand("source-complement", "TGTC"),
        ),
        phase=ConstructionStatePhase.DENATURED_FRAGMENTS,
    )
    with pytest.raises(ValueError, match="preserve exact duplex association"):
        validate_initial_material_state(denatured, (source, complement))


def test_composition_disposition_requires_status_specific_evidence() -> None:
    content = {
        "ordinal": 0,
        "foldback_realization_id": "hop:foldback-realization/" + "f" * 64 + "@1",
        "candidate_enzyme_programs": 1,
        "recognition_placements_attempted": 1,
        "constraint_systems_attempted": 1,
    }
    with pytest.raises(ValidationError, match="fields must match"):
        CompositionDisposition(
            **content,
            status=CompositionDispositionStatus.ACCEPTED,
        )
    with pytest.raises(ValidationError):
        CompositionDisposition(
            **content,
            status="unexamined",
        )
