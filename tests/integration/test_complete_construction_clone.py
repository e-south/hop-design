"""
--------------------------------------------------------------------------------
HOP Design
tests/integration/test_complete_construction_clone.py

Exercises exact complete-construction contracts for the clone-ready endpoint.

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
from hop_design.models.construction import (
    BasalPairAllowance,
    BasalTarget,
    ConstructionConstraints,
    ConstructionEndpoint,
    EndGenerationRequest,
    EnumerationPolicy,
    FinalPayloadReference,
    LocalNeighborhoodFamily,
    LocalNeighborhoodRequest,
    RelaxationMode,
    RelaxationPolicy,
    RouteFamily,
    SearchCompletionStatus,
)
from hop_design.models.construction.complete import (
    ConstructionProgram,
    ConstructionStatePhase,
    ConstructionTransitionKind,
    MaterializedConstructionRealization,
    MaterialRetentionDisposition,
)
from hop_design.models.construction.complete.clone import (
    CloneEndGenerationError,
    derive_clone_end_program_for_template,
)
from hop_design.models.construction.complete.clone.validation import validate_clone_realization
from hop_design.models.construction.complete.evaluation import (
    CompositionRejectionCode,
    evaluate_combination,
)
from hop_design.models.construction.complete.validation import validate_combination_evaluations
from hop_design.models.coordinates import Boundary
from hop_design.models.enzymes import (
    CharacterizedEnzyme,
    EnzymeClass,
    RecognitionOrientationSemantics,
    ResultingEndModel,
    SubstrateRequirement,
    TargetMolecule,
)
from hop_design.models.junction import Strand
from hop_design.models.method import BindingOrientation
from hop_design.models.molecular_state import EndChemistry, StrandEnd
from hop_design.models.payload import ExactPayload
from hop_design.models.reactions import ReactionProgram
from hop_design.models.references import ExternalRef
from hop_design.models.sequence import reverse_complement_iupac
from tests.contract.test_basal_construction_discovery import (
    _pairing_constraints,
    _provisioning,
    _type_iis,
)
from tests.integration.test_complete_construction_discovery import (
    _construction_request,
    _discover_raw,
    _material,
    _verified_design,
)
from tests.integration.test_complete_construction_pcr import _foldback, _payload
from tests.integration.test_resolved_compile import _component_spec


def _substitute_first_base(sequence: str) -> str:
    replacement = next(base for base in "ACGT" if base != sequence[0])
    return replacement + sequence[1:]


def _clone_basal_result(
    payload: FinalPayloadReference,
    *,
    pairing_allowances: tuple[BasalPairAllowance, ...] = (BasalPairAllowance.MATCH,) * 4,
    nickase_pattern: str = "TTTT",
    nickase_cut_offset_reference: int = 0,
    requested_overhangs: tuple[str, ...] = (),
):
    nickase = CharacterizedEnzyme(
        enzyme_id="example:enzyme/clone-bottom-nick@1",
        canonical_name="clone-bottom-nick",
        enzyme_class=EnzymeClass.NICKASE,
        target_molecule=TargetMolecule.DNA,
        recognition_pattern=nickase_pattern,
        recognition_orientation_semantics=RecognitionOrientationSemantics.BOTH_ORIENTATIONS,
        recognition_length=len(nickase_pattern),
        substrate_requirement=SubstrateRequirement.DUPLEX_DNA,
        cut_offset_reference_strand=nickase_cut_offset_reference,
        cut_offset_complement_strand=None,
        resulting_end_model=ResultingEndModel.NICK,
        characterization_source=ExternalRef(
            system="literature",
            kind="synthetic-characterization-fixture",
            id="clone-bottom-nick",
        ),
    )
    return discover_basal_neighborhood(
        LocalNeighborhoodRequest(
            payload=payload,
            family=LocalNeighborhoodFamily.BASAL,
            route_family=RouteFamily.LINEAR_SOURCE_V1,
            endpoint=ConstructionEndpoint.CLONE_READY_DUPLEX,
            target=BasalTarget(
                nick_strand=Strand.BOTTOM,
                nick_offset_nt=0,
                pairing_constraints=_pairing_constraints(pairing_allowances),
                ligation_proximal_match_required=True,
                end_generation=EndGenerationRequest(
                    type_iis_cut_offset_nt=0,
                    requested_overhangs=requested_overhangs,
                ),
            ),
            hard_constraints=ConstructionConstraints(),
            enzyme_provisioning=_provisioning(
                nickase,
                _type_iis(),
                max_operations=3,
            ),
            relaxation=RelaxationPolicy(
                mode=RelaxationMode.EXACT_ONLY,
                max_radius=0,
            ),
            enumeration=EnumerationPolicy(
                max_search_nodes=10_000,
                max_realizations=10_000,
            ),
        )
    )


def _clone_fixture(tmp_path: Path):
    payload = _payload()
    foldback = _foldback(payload)
    basal = _clone_basal_result(payload)
    assert basal.discovery.status is SearchCompletionStatus.COMPLETE
    assert len(basal.realizations) == 1
    basal_realization = basal.realizations[0]
    assert basal_realization.hairpin_pcr_duplex is not None
    adapter = next(
        item for item in basal_realization.materials if item.material_id == "ligation-adapter"
    )
    local_pcr_top = basal_realization.hairpin_pcr_duplex.top_strand.sequence
    design = _verified_design(tmp_path)
    encoding = design.plan.hairpin_encoding_insert.sequence
    complete_pcr_top = f"{local_pcr_top[:6]}{encoding}{local_pcr_top[-6:]}"
    return payload, foldback, basal, design, adapter, complete_pcr_top, encoding


def _clone_request(tmp_path: Path):
    payload, foldback, basal, design, adapter, complete_pcr_top, encoding = _clone_fixture(tmp_path)
    request = _construction_request(
        payload=payload,
        foldback=foldback,
        basal=basal,
        design=design,
        endpoint=ConstructionEndpoint.CLONE_READY_DUPLEX,
        adapter=_material(adapter.material_id, adapter.sequence_5prime),
        forward_primer=_material("forward-primer", complete_pcr_top[:4]),
        reverse_primer=_material(
            "reverse-primer",
            reverse_complement_iupac(complete_pcr_top[-4:]),
        ),
    )
    return request, foldback, basal, design, complete_pcr_top, encoding


def _verified_distal_mismatch_design(
    tmp_path: Path,
    *,
    left_arm: str,
    right_arm: str,
):
    spec = _component_spec().model_copy(update={"payload": ExactPayload(sequence="GACA")})
    data = spec.model_dump(by_alias=True)
    data["basal"]["pairing"]["left_arm"] = left_arm
    data["basal"]["pairing"]["right_arm"] = right_arm
    constraints = data["basal"]["constraints"]
    constraints["max_active_hard_mismatches"] = 1
    constraints["max_active_non_watson_crick_pairs"] = 1
    constraints["minimum_active_pair_support_index"] = 0.0
    constraints["maximum_active_pair_disruption_index"] = 4.0
    resolved = type(spec).model_validate(data)
    return load_verified_bundle(hop.compile(resolved).write(tmp_path / "mismatch-design"))


def _valid_clone_result(tmp_path: Path):
    request, foldback, basal, design, complete_pcr_top, encoding = _clone_request(tmp_path)
    result = _discover_raw(request, foldback=foldback, basal=basal, design=design)
    assert result.status is SearchCompletionStatus.COMPLETE
    assert result.realizations
    return result, basal, complete_pcr_top, encoding


def _realization_content(realization: MaterializedConstructionRealization) -> dict[str, object]:
    return {
        name: getattr(realization, name)
        for name in type(realization).model_fields
        if name not in {"materialized_realization_id", "construction_program"}
    }


def _reseal_program(
    original: ConstructionProgram,
    *,
    reaction_programs: tuple[ReactionProgram, ...] | None = None,
    stage_assessments=None,
) -> ConstructionProgram:
    return ConstructionProgram.create(
        states=original.states,
        transitions=original.transitions,
        reaction_programs=(
            original.reaction_programs if reaction_programs is None else reaction_programs
        ),
        stage_assessments=(
            original.stage_assessments if stage_assessments is None else stage_assessments
        ),
    )


def test_clone_end_generation_requires_local_authorities_or_lifted_bindings() -> None:
    with pytest.raises(
        CloneEndGenerationError,
        match="local authorities or lifted bindings",
    ):
        derive_clone_end_program_for_template(
            basal=None,
            foldback=None,
            pcr_top="AAAA",
            design_sequence="AAAA",
        )


def test_clone_ready_endpoint_extends_exact_pcr_route_through_end_generation(
    tmp_path: Path,
) -> None:
    payload = _payload()
    foldback = _foldback(payload)
    basal = _clone_basal_result(payload)
    assert basal.discovery.status is SearchCompletionStatus.COMPLETE
    assert len(basal.realizations) == 1

    basal_realization = basal.realizations[0]
    assert basal_realization.hairpin_pcr_duplex is not None
    adapter = next(
        item for item in basal_realization.materials if item.material_id == "ligation-adapter"
    )
    local_pcr_top = basal_realization.hairpin_pcr_duplex.top_strand.sequence
    design = _verified_design(tmp_path)
    encoding = design.plan.hairpin_encoding_insert.sequence
    complete_pcr_top = f"{local_pcr_top[:6]}{encoding}{local_pcr_top[-6:]}"
    request = _construction_request(
        payload=payload,
        foldback=foldback,
        basal=basal,
        design=design,
        endpoint=ConstructionEndpoint.CLONE_READY_DUPLEX,
        adapter=_material(adapter.material_id, adapter.sequence_5prime),
        forward_primer=_material("forward-primer", complete_pcr_top[:4]),
        reverse_primer=_material(
            "reverse-primer",
            reverse_complement_iupac(complete_pcr_top[-4:]),
        ),
    )

    result = _discover_raw(request, foldback=foldback, basal=basal, design=design)

    assert result.status is SearchCompletionStatus.COMPLETE
    realization = result.realizations[0]
    program = realization.construction_program
    assert tuple(state.phase for state in program.states[-2:]) == (
        ConstructionStatePhase.HAIRPIN_PCR_DUPLEX,
        ConstructionStatePhase.CLONE_READY_DUPLEX,
    )
    assert len(program.reaction_programs) == 2
    end_generation = tuple(
        transition
        for transition in program.transitions
        if transition.kind is ConstructionTransitionKind.END_GENERATION
    )
    assert end_generation == (program.transitions[-1],)
    assert end_generation[0].reaction_program_id == program.reaction_programs[-1].program_id

    pcr_state, terminal = program.states[-2:]
    assert pcr_state.molecules[0].sequence == complete_pcr_top
    assert complete_pcr_top[:6] == "GGTCTC"
    assert complete_pcr_top[-6:] == "GAGACC"
    assert terminal.molecules[0].sequence == encoding[:-4]
    assert terminal.molecules[1].sequence == reverse_complement_iupac(encoding[4:])

    local_end_bindings = tuple(
        operation.intended_binding
        for operation in basal_realization.reaction_programs[-1].stages[0].operations
    )
    complete_end_bindings = tuple(
        operation.intended_binding
        for operation in program.reaction_programs[-1].stages[0].operations
    )
    assert complete_end_bindings[0] == local_end_bindings[0]
    right_lift = len(foldback.realizations[0].retained_sequence) - len(payload.payload.sequence)
    assert (
        complete_end_bindings[1].recognition_span.start.offset
        - local_end_bindings[1].recognition_span.start.offset
        == right_lift
    )
    assert (
        complete_end_bindings[1].reference_cut.offset - local_end_bindings[1].reference_cut.offset
        == right_lift
    )
    assert (
        complete_end_bindings[1].complement_cut.offset - local_end_bindings[1].complement_cut.offset
        == right_lift
    )

    assert tuple(end.product_end for end in realization.final_product.cohesive_ends) == (
        "left",
        "right",
    )
    assert tuple(end.sequence for end in realization.final_product.cohesive_ends) == (
        encoding[:4],
        reverse_complement_iupac(encoding[-4:]),
    )
    projection = realization.final_product.encoding_projection
    assert projection.sequence == encoding
    assert projection.source_span.start.offset == len(local_pcr_top[:6])
    assert projection.source_span.end.offset == len(local_pcr_top[:6]) + len(encoding)
    assert projection.orientation is BindingOrientation.SAME_5TO3


def test_clone_ready_endpoint_preserves_distal_basal_mismatch_as_asymmetric_ends(
    tmp_path: Path,
) -> None:
    payload = _payload()
    foldback = _foldback(payload)
    basal = _clone_basal_result(
        payload,
        pairing_allowances=(
            BasalPairAllowance.MATCH,
            BasalPairAllowance.MATCH,
            BasalPairAllowance.MISMATCH,
            BasalPairAllowance.MATCH,
        ),
        nickase_pattern="GAGACC",
        nickase_cut_offset_reference=-4,
        requested_overhangs=("ATAA", "AGAA"),
    )
    assert basal.discovery.status is SearchCompletionStatus.COMPLETE
    basal_realization = next(
        item
        for item in basal.realizations
        if next(
            material.sequence_5prime
            for material in item.materials
            if material.material_id == "ligation-adapter"
        )
        == "TTCTGAGACC"
    )
    assert basal_realization.hairpin_pcr_duplex is not None
    adapter = next(
        item for item in basal_realization.materials if item.material_id == "ligation-adapter"
    )
    local_pcr_top = basal_realization.hairpin_pcr_duplex.top_strand.sequence
    design = _verified_distal_mismatch_design(
        tmp_path,
        left_arm="ATAA",
        right_arm="TTCT",
    )
    encoding = design.plan.hairpin_encoding_insert.sequence
    complete_pcr_top = f"{local_pcr_top[:6]}{encoding}{local_pcr_top[-6:]}"
    request = _construction_request(
        payload=payload,
        foldback=foldback,
        basal=basal,
        design=design,
        endpoint=ConstructionEndpoint.CLONE_READY_DUPLEX,
        adapter=_material(adapter.material_id, adapter.sequence_5prime),
        forward_primer=_material("forward-primer", complete_pcr_top[:4]),
        reverse_primer=_material(
            "reverse-primer",
            reverse_complement_iupac(complete_pcr_top[-4:]),
        ),
    )

    result = _discover_raw(request, foldback=foldback, basal=basal, design=design)

    assert result.status is SearchCompletionStatus.COMPLETE
    assert tuple(end.sequence for end in result.realizations[0].final_product.cohesive_ends) == (
        "ATAA",
        "AGAA",
    )


def test_clone_ready_reports_shared_pcr_primer_failures_as_infeasible(
    tmp_path: Path,
) -> None:
    payload, foldback, basal, design, adapter, complete_pcr_top, _ = _clone_fixture(tmp_path)
    invalid_forward_primers = (
        _material("forward-primer", complete_pcr_top[:4]).model_copy(
            update={"three_prime_end": EndChemistry.PHOSPHATE}
        ),
        _material("forward-primer", "CCCC"),
    )
    for forward_primer in invalid_forward_primers:
        request = _construction_request(
            payload=payload,
            foldback=foldback,
            basal=basal,
            design=design,
            endpoint=ConstructionEndpoint.CLONE_READY_DUPLEX,
            adapter=_material(adapter.material_id, adapter.sequence_5prime),
            forward_primer=forward_primer,
            reverse_primer=_material(
                "reverse-primer",
                reverse_complement_iupac(complete_pcr_top[-4:]),
            ),
        )

        result = _discover_raw(request, foldback=foldback, basal=basal, design=design)

        assert result.status is SearchCompletionStatus.INFEASIBLE
        assert result.realizations == ()
        assert {item.code for item in result.failure_reasons} == {
            CompositionRejectionCode.PCR_PRIMER_MISMATCH
        }


def test_clone_ready_rejects_shortened_and_wrong_full_adapter_materials(
    tmp_path: Path,
) -> None:
    payload, foldback, basal, design, adapter, complete_pcr_top, _ = _clone_fixture(tmp_path)
    invalid_adapters = (
        adapter.sequence_5prime[:-6],
        f"{adapter.sequence_5prime[:-1]}{_substitute_first_base(adapter.sequence_5prime[-1:])}",
    )
    for sequence in invalid_adapters:
        request = _construction_request(
            payload=payload,
            foldback=foldback,
            basal=basal,
            design=design,
            endpoint=ConstructionEndpoint.CLONE_READY_DUPLEX,
            adapter=_material(adapter.material_id, sequence),
            forward_primer=_material("forward-primer", complete_pcr_top[:4]),
            reverse_primer=_material(
                "reverse-primer",
                reverse_complement_iupac(complete_pcr_top[-4:]),
            ),
        )

        result = _discover_raw(request, foldback=foldback, basal=basal, design=design)

        assert result.status is SearchCompletionStatus.INFEASIBLE
        assert result.realizations == ()
        assert {item.code for item in result.failure_reasons} == {
            CompositionRejectionCode.PCR_ADAPTER_MISMATCH
        }


def test_clone_evaluator_rejects_full_adapter_that_breaks_end_generation(
    tmp_path: Path,
) -> None:
    payload, foldback, basal, design, adapter, complete_pcr_top, _ = _clone_fixture(tmp_path)
    changed_adapter_sequence = (
        f"{adapter.sequence_5prime[:-1]}{_substitute_first_base(adapter.sequence_5prime[-1:])}"
    )
    changed_complete_pcr_top = f"{complete_pcr_top[:-1]}{changed_adapter_sequence[-1]}"
    changed_material = _material(adapter.material_id, changed_adapter_sequence)
    basal_realization = basal.realizations[0]
    changed_basal = basal_realization.model_copy(
        update={
            "materials": tuple(
                changed_material if item.material_id == adapter.material_id else item
                for item in basal_realization.materials
            )
        }
    )
    request = _construction_request(
        payload=payload,
        foldback=foldback,
        basal=basal,
        design=design,
        endpoint=ConstructionEndpoint.CLONE_READY_DUPLEX,
        adapter=changed_material,
        forward_primer=_material("forward-primer", changed_complete_pcr_top[:4]),
        reverse_primer=_material(
            "reverse-primer",
            reverse_complement_iupac(changed_complete_pcr_top[-4:]),
        ),
    )

    evaluation = evaluate_combination(
        request,
        foldback=foldback.realizations[0],
        basal=changed_basal,
        foldback_policy=foldback.neighborhood.request.enzyme_provisioning,
        basal_policy=basal.discovery.request.enzyme_provisioning,
    )

    assert evaluation.rejection_reason is (
        CompositionRejectionCode.CLONE_END_GENERATION_INCOMPATIBLE
    )


def test_clone_rejects_resealed_lifted_end_generation_binding_forgeries(
    tmp_path: Path,
) -> None:
    result, _, _, _ = _valid_clone_result(tmp_path)
    realization = result.realizations[0]
    program = realization.construction_program
    end_program = program.reaction_programs[-1]
    end_stage = end_program.stages[0]
    right_operation = end_stage.operations[-1]
    right_binding = right_operation.intended_binding
    end_assessment = program.stage_assessments[-1]
    right_evidence = end_assessment.intended_bindings[-1]
    assert right_binding.reference_cut is not None
    assert right_binding.complement_cut is not None

    changed_bindings = (
        right_binding.model_copy(
            update={
                "recognition_span": right_binding.recognition_span.model_copy(
                    update={
                        "start": Boundary(offset=right_binding.recognition_span.start.offset + 1),
                        "end": Boundary(offset=right_binding.recognition_span.end.offset + 1),
                    }
                )
            }
        ),
        right_binding.model_copy(
            update={"reference_cut": Boundary(offset=right_binding.reference_cut.offset + 1)}
        ),
        right_binding.model_copy(
            update={"complement_cut": Boundary(offset=right_binding.complement_cut.offset + 1)}
        ),
    )
    content = _realization_content(realization)
    for changed_binding in changed_bindings:
        changed_operation = right_operation.model_copy(update={"intended_binding": changed_binding})
        changed_stage = end_stage.model_copy(
            update={"operations": (*end_stage.operations[:-1], changed_operation)}
        )
        changed_end_program = ReactionProgram(
            program_id=end_program.program_id,
            states=end_program.states,
            stages=(changed_stage,),
        )
        changed_evidence = right_evidence.model_copy(
            update={
                "recognition_span": changed_binding.recognition_span,
                "reference_cut": changed_binding.reference_cut,
                "complement_cut": changed_binding.complement_cut,
            }
        )
        changed_assessment = end_assessment.model_copy(
            update={
                "intended_bindings": (
                    *end_assessment.intended_bindings[:-1],
                    changed_evidence,
                )
            }
        )
        resealed = _reseal_program(
            program,
            reaction_programs=(*program.reaction_programs[:-1], changed_end_program),
            stage_assessments=(*program.stage_assessments[:-1], changed_assessment),
        )

        with pytest.raises(ValidationError, match="exact lifted bindings"):
            MaterializedConstructionRealization.create(
                **content,
                construction_program=resealed,
            )


def test_clone_replay_rejects_terminal_strand_forgery_matrix(tmp_path: Path) -> None:
    result, _, _, _ = _valid_clone_result(tmp_path)
    realization = result.realizations[0]
    program = realization.construction_program
    terminal = program.states[-1]
    primary = terminal.molecules[0]
    first_lineage = primary.lineage[0]
    changed_strands = (
        primary.model_copy(update={"sequence": _substitute_first_base(primary.sequence)}),
        primary.model_copy(
            update={
                "lineage": (
                    first_lineage.model_copy(
                        update={"origin_index": first_lineage.origin_index + 1}
                    ),
                    *primary.lineage[1:],
                )
            }
        ),
        primary.model_copy(
            update={
                "five_prime_end": (
                    EndChemistry.HYDROXYL
                    if primary.five_prime_end is EndChemistry.PHOSPHATE
                    else EndChemistry.PHOSPHATE
                )
            }
        ),
    )
    for changed_strand in changed_strands:
        changed_terminal = terminal.model_copy(
            update={"molecules": (changed_strand, terminal.molecules[1])}
        )
        changed_program = program.model_copy(
            update={"states": (*program.states[:-1], changed_terminal)}
        )
        changed_realization = realization.model_copy(
            update={"construction_program": changed_program}
        )

        with pytest.raises(ValueError, match="exact digest molecular graph"):
            validate_clone_realization(changed_realization)


def test_clone_replay_rejects_cohesive_end_forgery_matrix(tmp_path: Path) -> None:
    result, _, _, _ = _valid_clone_result(tmp_path)
    realization = result.realizations[0]
    product = realization.final_product
    left = product.cohesive_ends[0]
    alternative_strand_id = next(
        strand.strand_id
        for strand in product.strands
        if strand.strand_id != left.protruding_strand_id
    )
    forged_ends = (
        left.model_copy(update={"sequence": _substitute_first_base(left.sequence)}),
        left.model_copy(
            update={
                "overhang_end": (
                    StrandEnd.THREE_PRIME
                    if left.overhang_end is StrandEnd.FIVE_PRIME
                    else StrandEnd.FIVE_PRIME
                )
            }
        ),
        left.model_copy(update={"protruding_strand_id": alternative_strand_id}),
        left.model_copy(
            update={
                "source_span": left.source_span.model_copy(
                    update={
                        "start": Boundary(offset=left.source_span.start.offset + 1),
                        "end": Boundary(offset=left.source_span.end.offset + 1),
                    }
                )
            }
        ),
    )
    for forged in forged_ends:
        ends = (forged, *product.cohesive_ends[1:])
        changed_reference = product.reference.model_copy(update={"cohesive_ends": ends})
        changed_product = product.model_copy(
            update={"reference": changed_reference, "cohesive_ends": ends}
        )

        with pytest.raises(ValueError, match="exact staggered duplex graph"):
            validate_clone_realization(
                realization.model_copy(update={"final_product": changed_product})
            )


def test_clone_replay_rejects_terminal_pairing_and_design_union_forgeries(
    tmp_path: Path,
) -> None:
    result, _, _, _ = _valid_clone_result(tmp_path)
    realization = result.realizations[0]
    product = realization.final_product
    reversed_pairings = tuple(reversed(product.pairings))
    changed_pairing_product = product.model_copy(
        update={
            "reference": product.reference.model_copy(update={"pairings": reversed_pairings}),
            "pairings": reversed_pairings,
        }
    )
    changed_projection_product = product.model_copy(
        update={
            "encoding_projection": product.encoding_projection.model_copy(
                update={"orientation": BindingOrientation.REVERSE_COMPLEMENT_5TO3}
            )
        }
    )

    with pytest.raises(ValueError, match="exact staggered duplex graph"):
        validate_clone_realization(
            realization.model_copy(update={"final_product": changed_pairing_product})
        )
    with pytest.raises(ValueError, match="exact pre-digest cut union"):
        validate_clone_realization(
            realization.model_copy(update={"final_product": changed_projection_product})
        )


def test_clone_result_replay_rejects_forged_end_stage_assessment(tmp_path: Path) -> None:
    result, _, _, _ = _valid_clone_result(tmp_path)
    realization = result.realizations[0]
    program = realization.construction_program
    end_assessment = program.stage_assessments[-1]
    changed_assessment = end_assessment.model_copy(
        update={"intended_bindings": tuple(reversed(end_assessment.intended_bindings))}
    )
    changed_program = program.model_copy(
        update={"stage_assessments": (*program.stage_assessments[:-1], changed_assessment)}
    )
    changed_realization = realization.model_copy(update={"construction_program": changed_program})

    with pytest.raises(ValueError, match="exact combination evaluation"):
        validate_combination_evaluations(
            request=result.request,
            foldback_authority=result.foldback_authority,
            basal_authority=result.basal_authority,
            dispositions=result.combination_dispositions,
            realizations=(changed_realization, *result.realizations[1:]),
        )


def test_clone_route_rejects_forged_transient_removal_disposition(tmp_path: Path) -> None:
    result, _, _, _ = _valid_clone_result(tmp_path)
    realization = result.realizations[0]
    records = realization.route_material_dispositions
    end_generation_transition = realization.construction_program.transitions[-1]
    transient_index = next(
        index
        for index, item in enumerate(records)
        if item.disposition is MaterialRetentionDisposition.TRANSIENT
        and item.removal_transition_id == end_generation_transition.transition_id
    )
    transient = records[transient_index]
    changed = transient.model_copy(
        update={
            "removal_transition_id": realization.construction_program.transitions[0].transition_id
        }
    )
    changed_records = (*records[:transient_index], changed, *records[transient_index + 1 :])
    content = {
        name: getattr(realization, name)
        for name in type(realization).model_fields
        if name not in {"materialized_realization_id", "route_material_dispositions"}
    }

    with pytest.raises(ValidationError, match="material dispositions"):
        MaterializedConstructionRealization.create(
            **content,
            route_material_dispositions=changed_records,
        )
