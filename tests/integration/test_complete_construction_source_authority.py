"""
--------------------------------------------------------------------------------
HOP Design
tests/integration/test_complete_construction_source_authority.py

Tests complete-route authority against resealed upstream-source forgeries.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from collections.abc import Callable
from itertools import product
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import ValidationError

from hop_design.design.construction.complete import discovery as complete_discovery
from hop_design.design.construction.foldback import discover_foldback_neighborhood
from hop_design.models.construction import (
    CompleteConstructionRealization,
    ConstructionEndpoint,
    FinalPayloadReference,
    FoldbackTarget,
)
from hop_design.models.construction.complete import (
    ConstructionProgram,
    ConstructionSpaceResult,
    ConstructionState,
    ConstructionStatePhase,
    ConstructionTransition,
    ExactStateRelation,
    MaterializedConstructionRealization,
    ReactionBoundaryMapping,
    SourcePartitionBinding,
)
from hop_design.models.construction.complete.evaluation import (
    CompositionRejectionCode,
    evaluate_combination,
)
from hop_design.models.construction.complete.source_authority import (
    validate_local_authorities,
    validate_result_authorities,
)
from hop_design.models.construction.complete.transition_replay import (
    validate_non_enzyme_transition,
)
from hop_design.models.construction.foldback import FoldbackLocalRealization
from hop_design.models.construction.realization import FinalProductReference
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.enzymes import EnzymeRole, RecognitionOrientationSemantics
from hop_design.models.method import BindingOrientation
from hop_design.models.molecular_state import EndChemistry, LineageStrand
from hop_design.models.payload import ExactPayload
from hop_design.models.reactions import ReactionProgram
from hop_design.serialization import canonical_json_bytes
from tests.contract.test_foldback_construction_discovery import (
    _nickase,
    _request,
    _terminus_enzyme,
)
from tests.integration.test_complete_construction_discovery import (
    _basal_result,
    _construction_request,
    _discover_raw,
    _verified_design,
)


def _case(tmp_path: Path):
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
    request = _construction_request(
        payload=payload,
        foldback=foldback,
        basal=basal,
        design=design,
    )
    result = _discover_raw(
        request,
        foldback=foldback,
        basal=basal,
        design=design,
    )
    return request, foldback, basal, result


def _reseal_realization(record, **updates: object) -> MaterializedConstructionRealization:
    content = {
        name: getattr(record, name)
        for name in MaterializedConstructionRealization.model_fields
        if name != "materialized_realization_id"
    }
    content.update(updates)
    return MaterializedConstructionRealization.create(**content)


def test_complete_route_consumes_the_exact_source_preparation_product(
    tmp_path: Path,
) -> None:
    _, _, _, result = _case(tmp_path)
    realization = result.realizations[0]
    preparation = realization.source_preparation
    program = realization.construction_program

    assert program.states[0] == preparation.product_state
    assert realization.payload_source_map.segments[0].source_material_id == (
        preparation.source_ssdna.material_id
    )
    assert {
        item.origin_id for strand in program.states[0].molecules for item in strand.lineage
    } == {
        preparation.prepared_top_use.use_id,
        preparation.prepared_bottom_use.use_id,
    }


def test_unselected_route_omits_source_partition_authority_and_bindings(
    tmp_path: Path,
) -> None:
    _, _, _, result = _case(tmp_path)

    assert result.source_partition_authority is None
    assert result.source_partition_rejection_candidates == ()
    assert result.provenance.source_partition_result_id is None
    assert result.provenance.source_partition_realization_id is None
    assert all(item.source_partition_binding is None for item in result.realizations)
    serialized = canonical_json_bytes(result)
    assert b'"source_partition_authority"' not in serialized
    assert b'"source_partition_rejection_candidates"' not in serialized
    assert b'"source_partition_binding"' not in serialized
    assert b'"source_partition_result_id"' not in serialized
    assert b'"source_partition_realization_id"' not in serialized


def test_unselected_result_rejects_source_partition_provenance(
    tmp_path: Path,
) -> None:
    _, _, _, result = _case(tmp_path)
    provenance = type(result.provenance).model_validate(
        result.provenance.model_dump(mode="python")
        | {
            "source_partition_result_id": ("hop:source-partition-result/" + "a" * 64 + "@1"),
            "source_partition_realization_id": (
                "hop:source-partition-realization/" + "b" * 64 + "@1"
            ),
        }
    )

    with pytest.raises(ValidationError, match="source partition"):
        _reseal_result(result, provenance=provenance)


def test_unselected_realization_rejects_source_partition_binding(
    tmp_path: Path,
) -> None:
    _, _, _, result = _case(tmp_path)
    realization = result.realizations[0]
    program = realization.construction_program
    denatured = next(
        item for item in program.states if item.phase is ConstructionStatePhase.DENATURED_FRAGMENTS
    )
    selected = next(
        item for item in program.states if item.phase is ConstructionStatePhase.SELECTED_FRAGMENTS
    )
    binding = SourcePartitionBinding.create(
        result_id="hop:source-partition-result/" + "a" * 64 + "@1",
        realization_id="hop:source-partition-realization/" + "b" * 64 + "@1",
        source_preparation_product_state_id=realization.source_preparation.product_state.state_id,
        top_material_use_id=realization.material_uses[0].use_id,
        bottom_material_use_id=realization.material_uses[1].use_id,
        reaction_program_id=program.reaction_programs[0].program_id,
        denatured_state_id=denatured.state_id,
        selected_state_id=selected.state_id,
    )

    forged_realization = _reseal_realization(
        realization,
        source_partition_binding=binding,
    )
    with pytest.raises(ValidationError, match="source partition"):
        _reseal_result(
            result,
            realizations=(forged_realization, *result.realizations[1:]),
        )


def test_exhaustive_request_omits_absent_selected_pair_from_canonical_bytes(
    tmp_path: Path,
) -> None:
    request, _, _, _ = _case(tmp_path)

    content = canonical_json_bytes(request)

    assert b'"selected_foldback_realization_id"' not in content
    assert b'"selected_basal_realization_id"' not in content


def _reseal_result(record, **updates: object) -> ConstructionSpaceResult:
    content = {
        name: getattr(record, name)
        for name in ConstructionSpaceResult.model_fields
        if name != "result_id"
    }
    content.update(updates)
    return ConstructionSpaceResult.create(**content)


def _reseal_program(
    program: ConstructionProgram,
    states: tuple[ConstructionState, ...],
    *,
    reaction_programs: tuple[ReactionProgram, ...] | None = None,
    stage_assessments: tuple[object, ...] | None = None,
) -> ConstructionProgram:
    transitions: list[ConstructionTransition] = []
    for index, transition in enumerate(program.transitions):
        pre_state = states[index]
        post_state = states[index + 1]
        if transition.reaction_program_id is None:
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
        else:
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
    return ConstructionProgram.create(
        states=states,
        transitions=tuple(transitions),
        reaction_programs=reaction_programs or program.reaction_programs,
        stage_assessments=stage_assessments or program.stage_assessments,
    )


def _replace_member(result, replacement, **result_updates: object) -> dict[str, object]:
    original = result.realizations[0]
    replacement_id = replacement.materialized_realization_id
    original_id = original.materialized_realization_id
    dispositions = (
        result.combination_dispositions[0].model_copy(
            update={
                "foldback_realization_id": replacement.foldback_realization_id,
                "basal_realization_id": replacement.basal_realization_id,
                "materialized_realization_id": replacement_id,
            }
        ),
        *result.combination_dispositions[1:],
    )
    content = result.model_dump(mode="python") | {
        "realizations": (replacement, *result.realizations[1:]),
        "combination_dispositions": dispositions,
        "geometry_groups": tuple(
            group.model_copy(
                update={
                    "realization_ids": tuple(
                        replacement_id if item == original_id else item
                        for item in group.realization_ids
                    )
                }
            )
            for group in result.geometry_groups
        ),
        "final_product_groups": tuple(
            group.model_copy(
                update={
                    "realization_ids": tuple(
                        replacement_id if item == original_id else item
                        for item in group.realization_ids
                    )
                }
            )
            for group in result.final_product_groups
        ),
    }
    content.update(result_updates)
    return content


def _changed_state(
    state: ConstructionState,
    change: Callable[[Any], Any],
) -> ConstructionState:
    return ConstructionState.create(
        molecules=tuple(change(item) for item in state.molecules),
        phase=state.phase,
        pairings=state.pairings,
        formed_bonds=state.formed_bonds,
    )


def test_result_rejects_resealed_nonmember_foldback_authority(tmp_path: Path) -> None:
    _, _, _, result = _case(tmp_path)
    realization = result.realizations[0]
    local = realization.foldback_authority
    content = local.model_dump(mode="python", exclude={"foldback_realization_id"})
    content["changed_coordinates"] = ("different-valid-coordinate",)
    replacement_local = FoldbackLocalRealization.create(**content)
    complete = CompleteConstructionRealization.create(
        precursor_sequence=realization.realization.precursor_sequence,
        local_realization_ids=(
            realization.basal_realization_id,
            replacement_local.foldback_realization_id,
        ),
        stage_ids=realization.realization.stage_ids,
        final_product_id=realization.realization.final_product_id,
    )
    with pytest.raises(ValidationError, match=r"local authorities|foldback"):
        _reseal_realization(
            realization,
            realization=complete,
            foldback_authority=replacement_local,
            foldback_realization_id=replacement_local.foldback_realization_id,
        )


@pytest.mark.parametrize(
    ("update", "message"),
    (
        (
            lambda result: {
                "provenance": result.provenance.model_copy(update={"hop_version": "forged"})
            },
            "Provenance HOP version",
        ),
        (
            lambda result: {"upstream_truncation_reasons": ("foldback:invented-bound",)},
            "replay exact local authorities",
        ),
        (
            lambda result: {"realizations": (*result.realizations, result.realizations[0])},
            "must not repeat realizations",
        ),
        (
            lambda result: {
                "material_accounting": result.material_accounting.model_copy(
                    update={
                        "endpoint_product_nt": result.material_accounting.endpoint_product_nt + 1
                    }
                )
            },
            "Material accounting must derive",
        ),
    ),
)
def test_complete_result_rejects_resealed_authority_forgery_matrix(
    tmp_path: Path,
    update: Callable[[Any], dict[str, object]],
    message: str,
) -> None:
    _, _, _, result = _case(tmp_path)

    with pytest.raises(ValidationError, match=message):
        _reseal_result(result, **update(result))


def test_complete_result_replays_disposition_work_metrics(tmp_path: Path) -> None:
    _, _, _, result = _case(tmp_path)
    disposition = result.combination_dispositions[0]
    changed_disposition = disposition.model_copy(
        update={"candidate_enzyme_programs": disposition.candidate_enzyme_programs + 1}
    )
    changed_accounting = result.accounting.model_copy(
        update={"candidate_enzyme_programs": result.accounting.candidate_enzyme_programs + 1}
    )

    with pytest.raises(ValidationError, match="Disposition metrics"):
        _reseal_result(
            result,
            combination_dispositions=(
                changed_disposition,
                *result.combination_dispositions[1:],
            ),
            accounting=changed_accounting,
        )


def test_non_enzyme_transition_replay_rejects_molecular_forgery_matrix(
    tmp_path: Path,
) -> None:
    _, _, _, result = _case(tmp_path)
    program = result.realizations[0].construction_program
    cleaved, denatured, selected, annealed, ligated = program.states[1:]

    changed_denatured_strand = denatured.molecules[0].model_copy(
        update={"five_prime_end": EndChemistry.PHOSPHATE}
    )
    changed_denatured = ConstructionState.create(
        molecules=(changed_denatured_strand, *denatured.molecules[1:]),
        phase=denatured.phase,
    )
    with pytest.raises(ValueError, match="preserve exact strands, chemistry, and lineage"):
        validate_non_enzyme_transition(
            kind="denaturation",
            pre_state=cleaved,
            post_state=changed_denatured,
        )

    foreign_selected_strand = selected.molecules[0].model_copy(update={"strand_id": "foreign"})
    foreign_selected = ConstructionState.create(
        molecules=(foreign_selected_strand, *selected.molecules[1:]),
        phase=selected.phase,
    )
    with pytest.raises(ValueError, match="retain only exact precursor strands"):
        validate_non_enzyme_transition(
            kind="fragment_selection",
            pre_state=denatured,
            post_state=foreign_selected,
        )

    changed_annealed_strand = annealed.molecules[0].model_copy(
        update={"three_prime_end": EndChemistry.PHOSPHATE}
    )
    changed_annealed = ConstructionState.create(
        molecules=(changed_annealed_strand, *annealed.molecules[1:]),
        phase=annealed.phase,
        pairings=annealed.pairings,
    )
    with pytest.raises(ValueError, match="preserve exact strand sequence, chemistry, and lineage"):
        validate_non_enzyme_transition(
            kind="annealing",
            pre_state=selected,
            post_state=changed_annealed,
        )

    broken_bond = ligated.formed_bonds[0].model_copy(
        update={
            "bond": ligated.formed_bonds[0].bond.model_copy(
                update={"upstream_strand_id": "absent-precursor"}
            )
        }
    )
    broken_ligated = ConstructionState.create(
        molecules=ligated.molecules,
        phase=ligated.phase,
        pairings=ligated.pairings,
        formed_bonds=(broken_bond,),
    )
    with pytest.raises(ValueError, match="reference exact precursor strands"):
        validate_non_enzyme_transition(
            kind="ligation",
            pre_state=annealed,
            post_state=broken_ligated,
        )

    with pytest.raises(ValueError, match="explicit template-copying authority"):
        validate_non_enzyme_transition(
            kind="primer_extension",
            pre_state=annealed,
            post_state=ligated,
        )


def test_construction_program_rejects_resealed_program_authority_matrix(
    tmp_path: Path,
) -> None:
    _, _, _, result = _case(tmp_path)
    program = result.realizations[0].construction_program

    with pytest.raises(ValidationError, match="ReactionProgram ids must be unique"):
        ConstructionProgram.create(
            states=program.states,
            transitions=program.transitions,
            reaction_programs=(*program.reaction_programs, program.reaction_programs[0]),
            stage_assessments=program.stage_assessments,
        )

    with pytest.raises(ValidationError, match="referenced exactly once"):
        ConstructionProgram.create(
            states=program.states,
            transitions=program.transitions,
            reaction_programs=(),
            stage_assessments=(),
        )

    wrong_phase = ConstructionState.create(
        molecules=program.states[0].molecules,
        phase=ConstructionStatePhase.HAIRPIN_PCR_DUPLEX,
        pairings=program.states[0].pairings,
    )
    with pytest.raises(ValidationError, match="preserve physical phase order"):
        _reseal_program(program, (wrong_phase, *program.states[1:]))

    first_assessment = program.stage_assessments[0]
    first_binding = first_assessment.intended_bindings[0]
    forged_assessment = first_assessment.model_copy(
        update={
            "intended_bindings": (
                first_binding.model_copy(update={"enzyme_id": "forged-enzyme"}),
                *first_assessment.intended_bindings[1:],
            )
        }
    )
    with pytest.raises(ValidationError, match="replay its declared operation"):
        ConstructionProgram.create(
            states=program.states,
            transitions=program.transitions,
            reaction_programs=program.reaction_programs,
            stage_assessments=(forged_assessment, *program.stage_assessments[1:]),
        )


def test_result_rejects_resealed_origin_strand_drift(tmp_path: Path) -> None:
    _, _, _, result = _case(tmp_path)
    realization = result.realizations[0]
    program = realization.construction_program

    def change(strand):
        return strand.model_copy(
            update={
                "lineage": tuple(
                    item.model_copy(update={"origin_strand": LineageStrand.COMPLEMENTARY})
                    if item.origin_strand is LineageStrand.PRIMARY
                    else item
                    for item in strand.lineage
                )
            }
        )

    states = (program.states[0], *(_changed_state(item, change) for item in program.states[1:]))
    changed_program = _reseal_program(program, states)
    changed_product = realization.final_product.model_copy(
        update={"strands": changed_program.states[-1].molecules}
    )
    with pytest.raises(ValidationError, match="lineage"):
        _reseal_realization(
            realization,
            construction_program=changed_program,
            final_product=changed_product,
        )


def test_result_rejects_resealed_discarded_fragment_end_chemistry(tmp_path: Path) -> None:
    _, _, _, result = _case(tmp_path)
    realization = result.realizations[0]
    program = realization.construction_program
    selected_sequences = {item.sequence for item in program.states[3].molecules}
    discarded = next(
        item for item in program.states[1].molecules if item.sequence not in selected_sequences
    )

    def change(strand):
        if strand.sequence != discarded.sequence:
            return strand
        return strand.model_copy(update={"five_prime_end": EndChemistry.HYDROXYL})

    states = (
        program.states[0],
        _changed_state(program.states[1], change),
        _changed_state(program.states[2], change),
        *program.states[3:],
    )
    with pytest.raises(ValidationError, match=r"fragment|chemistry"):
        _reseal_realization(
            realization,
            construction_program=_reseal_program(program, states),
        )


def test_result_rejects_missing_required_basal_nick(tmp_path: Path) -> None:
    _, _, _, result = _case(tmp_path)
    realization = result.realizations[0]
    program = realization.construction_program
    reaction = program.reaction_programs[0]
    stage = reaction.stages[-1]
    retained_operations = tuple(
        item for item in stage.operations if item.role is not EnzymeRole.BASAL_NICK
    )
    changed_stage = stage.model_copy(update={"operations": retained_operations})
    changed_reaction = reaction.model_copy(
        update={"stages": (*reaction.stages[:-1], changed_stage)}
    )
    assessment = program.stage_assessments[-1]
    changed_assessment = assessment.model_copy(
        update={
            "intended_bindings": tuple(
                item
                for item in assessment.intended_bindings
                if item.operation_id
                in {operation.operation_id for operation in retained_operations}
            )
        }
    )
    changed_program = _reseal_program(
        program,
        program.states,
        reaction_programs=(changed_reaction,),
        stage_assessments=(*program.stage_assessments[:-1], changed_assessment),
    )
    with pytest.raises(ValidationError, match=r"basal|operation"):
        _reseal_realization(realization, construction_program=changed_program)


def test_result_rejects_endpoint_and_topology_forgery(tmp_path: Path) -> None:
    _, _, _, result = _case(tmp_path)
    realization = result.realizations[0]
    reference = FinalProductReference.create(
        endpoint=ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
        sequence=realization.final_product.reference.sequence,
        topology="invented-topology",
        end_descriptors=realization.final_product.reference.end_descriptors,
    )
    product = realization.final_product.model_copy(update={"reference": reference})
    complete = CompleteConstructionRealization.create(
        precursor_sequence=realization.realization.precursor_sequence,
        local_realization_ids=realization.realization.local_realization_ids,
        stage_ids=realization.realization.stage_ids,
        final_product_id=reference.final_product_id,
    )
    with pytest.raises(ValidationError, match=r"endpoint|topology"):
        _reseal_realization(
            realization,
            realization=complete,
            final_product=product,
        )


def test_result_rejects_resealed_nonmember_basal_id(tmp_path: Path) -> None:
    _, _, _, result = _case(tmp_path)
    realization = result.realizations[0]
    fake_basal_id = "hop:basal-realization/" + "e" * 64 + "@1"
    complete = CompleteConstructionRealization.create(
        precursor_sequence=realization.realization.precursor_sequence,
        local_realization_ids=(fake_basal_id, realization.foldback_realization_id),
        stage_ids=realization.realization.stage_ids,
        final_product_id=realization.realization.final_product_id,
    )
    with pytest.raises(ValidationError, match="basal"):
        _reseal_realization(
            realization,
            realization=complete,
            basal_realization_id=fake_basal_id,
        )


def test_result_rejects_resealed_equal_byte_origin_index(tmp_path: Path) -> None:
    _, _, _, result = _case(tmp_path)
    realization = result.realizations[0]
    program = realization.construction_program
    selected_sequences = {item.sequence for item in program.states[3].molecules}
    discarded = next(
        item for item in program.states[1].molecules if item.sequence not in selected_sequences
    )
    lineage = discarded.lineage[0]
    material_by_use_id = {
        use.use_id: material
        for use, material in zip(
            realization.material_uses,
            realization.materials,
            strict=True,
        )
    }
    material = material_by_use_id[lineage.origin_id]
    replacement_index = next(
        index
        for index, base in enumerate(material.sequence_5prime)
        if index != lineage.origin_index and base == discarded.sequence[0]
    )

    def change(strand):
        if strand.sequence != discarded.sequence:
            return strand
        lineage_records = tuple(
            item.model_copy(update={"origin_index": replacement_index})
            if (
                item.origin_id == lineage.origin_id
                and item.origin_strand is lineage.origin_strand
                and item.origin_index == lineage.origin_index
            )
            else item
            for item in strand.lineage
        )
        return strand.model_copy(update={"lineage": lineage_records})

    states = (
        program.states[0],
        _changed_state(program.states[1], change),
        _changed_state(program.states[2], change),
        *program.states[3:],
    )
    with pytest.raises(ValidationError, match=r"lineage|coordinate"):
        _reseal_realization(
            realization,
            construction_program=_reseal_program(program, states),
        )


def test_source_authority_validator_rejects_drifted_domains_and_order(tmp_path: Path) -> None:
    request, foldback, basal, result = _case(tmp_path)
    realization = result.realizations[0]
    with pytest.raises(ValueError, match="exact foldback authority"):
        validate_local_authorities(
            foldback=realization.foldback_authority,
            foldback_realization_id="hop:foldback-realization/" + "f" * 64 + "@1",
            basal=realization.basal_authority,
            basal_realization_id=realization.basal_realization_id,
            local_realization_ids=realization.realization.local_realization_ids,
        )
    with pytest.raises(ValueError, match="ordered local authorities"):
        validate_local_authorities(
            foldback=realization.foldback_authority,
            foldback_realization_id=realization.foldback_realization_id,
            basal=realization.basal_authority,
            basal_realization_id=realization.basal_realization_id,
            local_realization_ids=tuple(reversed(realization.realization.local_realization_ids)),
        )
    with pytest.raises(ValueError, match="foldback authority"):
        validate_result_authorities(
            request=SimpleNamespace(
                foldback_result_id="hop:foldback-neighborhood/" + "f" * 64 + "@1",
                basal_result_id=request.basal_result_id,
            ),
            provenance=result.provenance,
            foldback=foldback,
            basal=basal,
            realizations=result.realizations,
        )
    with pytest.raises(ValueError, match="basal authority"):
        validate_result_authorities(
            request=SimpleNamespace(
                foldback_result_id=request.foldback_result_id,
                basal_result_id="hop:basal-neighborhood/" + "b" * 64 + "@1",
            ),
            provenance=result.provenance,
            foldback=foldback,
            basal=basal,
            realizations=result.realizations,
        )
    with pytest.raises(ValueError, match="provenance domains"):
        validate_result_authorities(
            request=request,
            provenance=result.provenance.model_copy(update={"foldback_realization_ids": ()}),
            foldback=foldback,
            basal=basal,
            realizations=result.realizations,
        )


def test_source_authority_validator_rejects_unlisted_selected_members(tmp_path: Path) -> None:
    request, foldback, basal, result = _case(tmp_path)
    realization = result.realizations[0]
    cases = (
        (
            {
                "selected_foldback_realization_id": ("hop:foldback-realization/" + "f" * 64 + "@1"),
                "selected_basal_realization_id": realization.basal_realization_id,
            },
            "Selected foldback authority",
        ),
        (
            {
                "selected_foldback_realization_id": realization.foldback_realization_id,
                "selected_basal_realization_id": "hop:basal-realization/" + "b" * 64 + "@1",
            },
            "Selected basal authority",
        ),
    )
    for updates, message in cases:
        with pytest.raises(ValueError, match=message):
            validate_result_authorities(
                request=request.model_copy(update=updates),
                provenance=result.provenance,
                foldback=foldback,
                basal=basal,
                realizations=result.realizations,
            )


@pytest.mark.parametrize(
    ("updates", "message"),
    (
        ({"foldback_authority": None}, "Accepted foldback member"),
        (
            {
                "basal_realization_id": "hop:basal-realization/" + "b" * 64 + "@1",
                "basal_authority": None,
            },
            "Accepted basal member must belong",
        ),
        ({"basal_authority": None}, "Accepted basal member must equal"),
    ),
)
def test_source_authority_validator_rejects_drifted_embedded_members(
    tmp_path: Path,
    updates: dict[str, object],
    message: str,
) -> None:
    request, foldback, basal, result = _case(tmp_path)
    realization = result.realizations[0]

    with pytest.raises(ValueError, match=message):
        validate_result_authorities(
            request=request,
            provenance=result.provenance,
            foldback=foldback,
            basal=basal,
            realizations=(realization.model_copy(update=updates),),
        )


def test_realization_rejects_resealed_geometry_and_projection_drift(tmp_path: Path) -> None:
    _, _, _, result = _case(tmp_path)
    realization = result.realizations[0]
    with pytest.raises(ValidationError, match=r"geometry|radius"):
        _reseal_realization(
            realization,
            geometry_ids=("hop:geometry/" + "a" * 64 + "@1",),
            relaxation_radii=(7,),
        )
    projection = realization.final_product.encoding_projection.model_copy(
        update={"orientation": BindingOrientation.REVERSE_COMPLEMENT_5TO3}
    )
    with pytest.raises(ValidationError, match=r"projection|full-span|orientation"):
        _reseal_realization(
            realization,
            final_product=realization.final_product.model_copy(
                update={"encoding_projection": projection}
            ),
        )


def test_state_rejects_duplicate_pairing_coordinates(tmp_path: Path) -> None:
    _, _, _, result = _case(tmp_path)
    state = result.realizations[0].construction_program.states[0]
    pair = state.pairings[0]
    duplicate_coordinate = state.pairings[1].model_copy(
        update={
            "left_strand_id": pair.left_strand_id,
            "left_index": pair.left_index,
            "left_base": pair.left_base,
        }
    )
    with pytest.raises(ValidationError, match="pairing coordinates"):
        ConstructionState.create(
            molecules=state.molecules,
            phase=state.phase,
            pairings=(pair, duplicate_coordinate, *state.pairings[2:]),
            formed_bonds=state.formed_bonds,
        )


def test_complete_states_do_not_carry_opaque_authority_strings(tmp_path: Path) -> None:
    _, _, _, result = _case(tmp_path)
    states = result.realizations[0].construction_program.states
    assert all("authority_ids" not in type(state).model_fields for state in states)
    state = states[0]
    with pytest.raises(ValidationError, match="authority_ids"):
        ConstructionState.model_validate(
            state.model_dump(mode="python") | {"authority_ids": ("invented-authority",)}
        )


def test_realization_rejects_endpoint_before_result_assembly(tmp_path: Path) -> None:
    _, _, _, result = _case(tmp_path)
    realization = result.realizations[0]
    reference = FinalProductReference.create(
        endpoint=ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
        sequence=realization.final_product.reference.sequence,
        topology="invented-topology",
        end_descriptors=realization.final_product.reference.end_descriptors,
    )
    complete = CompleteConstructionRealization.create(
        precursor_sequence=realization.realization.precursor_sequence,
        local_realization_ids=realization.realization.local_realization_ids,
        stage_ids=realization.realization.stage_ids,
        final_product_id=reference.final_product_id,
    )
    with pytest.raises(ValidationError, match=r"endpoint|topology|terminal"):
        _reseal_realization(
            realization,
            realization=complete,
            final_product=realization.final_product.model_copy(update={"reference": reference}),
        )


def test_realization_rejects_reduced_cleaved_duplex_pairings(tmp_path: Path) -> None:
    _, _, _, result = _case(tmp_path)
    realization = result.realizations[0]
    program = realization.construction_program
    cleaved = program.states[1]
    reduced = ConstructionState.create(
        molecules=cleaved.molecules,
        phase=cleaved.phase,
        pairings=cleaved.pairings[:-1],
        formed_bonds=cleaved.formed_bonds,
    )
    states = (program.states[0], reduced, *program.states[2:])
    with pytest.raises(ValidationError, match=r"cleaved.*pair|duplex.*pair"):
        _reseal_realization(
            realization,
            construction_program=_reseal_program(program, states),
        )


def test_upstream_truncation_is_distinct_from_composition_suffix(tmp_path: Path) -> None:
    request, foldback, basal, _ = _case(tmp_path)
    neighborhood = foldback.neighborhood
    local_request = neighborhood.request.model_copy(
        update={
            "enumeration": neighborhood.request.enumeration.model_copy(
                update={"max_search_nodes": 1}
            )
        }
    )
    truncated_foldback = discover_foldback_neighborhood(local_request)
    truncated_request = request.model_copy(
        update={"foldback_result_id": truncated_foldback.result_id}
    )
    result = _discover_raw(
        truncated_request,
        foldback=truncated_foldback,
        basal=basal,
        design=_verified_design(tmp_path / "truncated-design"),
    )
    assert result.status.value == "truncated"
    assert result.truncation_reasons == ()
    assert result.upstream_truncation_reasons == ("foldback:max_search_nodes",)
    assert all(item.status.value != "unexamined" for item in result.combination_dispositions)


def test_composition_does_not_materialize_or_consume_the_unexamined_suffix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request, foldback, basal, _ = _case(tmp_path)
    design = _verified_design(tmp_path / "bounded-design")
    request = request.model_copy(
        update={"enumeration": request.enumeration.model_copy(update={"max_combinations": 1})}
    )

    def guarded_product(*domains: object):
        for index, pair in enumerate(product(*domains)):
            if index:
                raise AssertionError("composition consumed the unexamined suffix")
            yield pair

    monkeypatch.setattr(complete_discovery, "product", guarded_product)

    result = _discover_raw(
        request,
        foldback=foldback,
        basal=basal,
        design=design,
    )
    assert result.accounting.examined_combinations == 1
    assert len(result.combination_dispositions) == 1


def test_complete_route_detects_an_actionable_site_created_across_local_boundaries(
    tmp_path: Path,
) -> None:
    request, _, basal, _ = _case(tmp_path)
    foldback = discover_foldback_neighborhood(
        _request(
            _nickase(
                motif="AAGACA",
                cut_offset=0,
                orientation_semantics=RecognitionOrientationSemantics.DECLARED_ONLY,
            ),
            _terminus_enzyme(),
        )
    )
    assert all(
        not assessment.report.has_errors
        for realization in foldback.realizations
        for assessment in realization.stage_assessments
    )
    request = request.model_copy(update={"foldback_result_id": foldback.result_id})

    evaluation = evaluate_combination(
        request,
        foldback=foldback.realizations[0],
        basal=basal.realizations[0],
        foldback_policy=foldback.neighborhood.request.enzyme_provisioning,
        basal_policy=basal.discovery.request.enzyme_provisioning,
    )

    assert evaluation.prefix == "AAAA"
    assert evaluation.rejection_reason is CompositionRejectionCode.GLOBAL_ACTIONABLE_SITE_CONFLICT
    assert tuple(
        (
            binding.recognition_span.start.offset,
            binding.recognition_span.end.offset,
        )
        for assessment in evaluation.stage_assessments
        for binding in assessment.undeclared_bindings
    ) == ((2, 8),)


def test_payload_source_occurrence_is_exact_when_payload_bytes_repeat(tmp_path: Path) -> None:
    payload = FinalPayloadReference(
        payload=ExactPayload(sequence="A"),
        basal_boundary=Boundary(offset=0),
        foldback_boundary=Boundary(offset=1),
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
        ).model_copy(update={"payload": payload})
    )
    design = _verified_design(tmp_path / "repeated-design", payload="A")
    request = _construction_request(
        payload=payload,
        foldback=foldback,
        basal=None,
        design=design,
    )
    result = _discover_raw(request, foldback=foldback, basal=None, design=design)
    realization = result.realizations[0]
    segment = realization.payload_source_map.segments[0]
    assert segment.source_span.start.offset == 4
    repeated_byte_map = realization.payload_source_map.model_copy(
        update={
            "segments": (
                segment.model_copy(
                    update={
                        "source_span": Span(
                            start=Boundary(offset=0),
                            end=Boundary(offset=1),
                        )
                    }
                ),
            )
        }
    )
    with pytest.raises(ValidationError, match="exact lifted local authority"):
        _reseal_realization(realization, payload_source_map=repeated_byte_map)
