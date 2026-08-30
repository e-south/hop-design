"""
--------------------------------------------------------------------------------
HOP Design
tests/integration/test_complete_construction_pcr.py

Exercises exact complete-construction contracts for the hairpin PCR endpoint.

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
from hop_design.design.construction.foldback import discover_foldback_neighborhood
from hop_design.models.basal import BasalPairingRequest
from hop_design.models.construction import (
    BasalPairAllowance,
    CompleteConstructionRealization,
    ConstructionEndpoint,
    FinalPayloadReference,
    FoldbackTarget,
    SearchCompletionStatus,
)
from hop_design.models.construction.complete import (
    AdapterLigationAuthority,
    ConstructionProgram,
    ConstructionState,
    ConstructionStatePhase,
    ConstructionTransition,
    ConstructionTransitionKind,
    DuplexFinalProductReference,
    EndpointSequenceFate,
    MaterialFunction,
    MaterializedConstructionRealization,
    MaterializedFinalProduct,
    MaterialRetentionDisposition,
    PrimerExtensionAuthority,
)
from hop_design.models.construction.complete.evaluation import (
    CompositionRejectionCode,
    evaluate_combination,
)
from hop_design.models.construction.complete.pcr.replay import validate_pcr_transition
from hop_design.models.construction.complete.pcr.route import select_pcr_fragments
from hop_design.models.construction.complete.pcr.validation import (
    validate_adapter_pairing_profile,
    validate_pcr_realization,
)
from hop_design.models.construction.complete.route_schedule import (
    derive_direct_reaction_program,
    derive_pcr_reaction_program,
)
from hop_design.models.construction.payload import _content_id
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.enzymes import RecognitionOrientationSemantics
from hop_design.models.junction import Strand
from hop_design.models.method import BindingOrientation
from hop_design.models.molecular_state import CohesiveEnd, EndChemistry, StrandEnd
from hop_design.models.payload import ExactPayload
from hop_design.models.physical import JunctionPairKind
from hop_design.models.sequence import reverse_complement_iupac
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
    _material,
    _verified_design,
)
from tests.integration.test_resolved_compile import _component_spec


def _foldback(payload: FinalPayloadReference):
    return discover_foldback_neighborhood(
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


def _payload() -> FinalPayloadReference:
    return FinalPayloadReference(
        payload=ExactPayload(sequence="GACA"),
        basal_boundary=Boundary(offset=0),
        foldback_boundary=Boundary(offset=4),
    )


def _substitute_first_base(sequence: str) -> str:
    replacement = next(base for base in "ACGT" if base != sequence[0])
    return replacement + sequence[1:]


def _valid_pcr_result(tmp_path: Path):
    payload = _payload()
    foldback = _foldback(payload)
    basal = _basal_result(
        payload,
        ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
        nick_strand=Strand.BOTTOM,
    )
    design = _verified_design(tmp_path)
    encoding = design.plan.hairpin_encoding_insert.sequence
    adapter = next(
        item for item in basal.realizations[0].materials if item.material_id == "ligation-adapter"
    )
    request = _construction_request(
        payload=payload,
        foldback=foldback,
        basal=basal,
        design=design,
        endpoint=ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
        adapter=_material(adapter.material_id, adapter.sequence_5prime),
        forward_primer=_material("forward-primer", encoding[:4]),
        reverse_primer=_material("reverse-primer", reverse_complement_iupac(encoding[-4:])),
    )
    return (
        _discover_raw(request, foldback=foldback, basal=basal, design=design),
        basal,
        encoding,
    )


def _verified_distal_mismatch_design(tmp_path: Path):
    spec = _component_spec().model_copy(update={"payload": ExactPayload(sequence="GACA")})
    basal = spec.basal.model_copy(
        update={
            "pairing": BasalPairingRequest(left_arm="AAAA", right_arm="TTAT"),
            "acceptance": "allow_reserve",
            "constraints": spec.basal.constraints.model_copy(
                update={
                    "max_active_hard_mismatches": 1,
                    "max_active_non_watson_crick_pairs": 1,
                    "minimum_active_pair_support_index": 0.0,
                    "maximum_active_pair_disruption_index": 4.0,
                    "reject_compact_profiles": (),
                    "reserve_compact_profiles": (),
                }
            ),
        }
    )
    resolved = spec.model_copy(update={"basal": basal})
    return load_verified_bundle(hop.compile(resolved).write(tmp_path / "mismatch-design"))


def _unchecked_program(
    original: ConstructionProgram,
    *,
    states: tuple[ConstructionState, ...] | None = None,
    transitions: tuple[ConstructionTransition, ...] | None = None,
) -> ConstructionProgram:
    content = {
        "states": states or original.states,
        "transitions": transitions or original.transitions,
        "reaction_programs": original.reaction_programs,
        "stage_assessments": original.stage_assessments,
    }
    draft = ConstructionProgram.model_construct(program_id="", **content)
    program_id = _content_id(
        "construction-program",
        1,
        draft.model_dump(mode="json", exclude={"program_id"}),
    )
    return ConstructionProgram.model_construct(program_id=program_id, **content)


def _realization_content(realization: MaterializedConstructionRealization) -> dict[str, object]:
    return {
        name: getattr(realization, name)
        for name in type(realization).model_fields
        if name not in {"materialized_realization_id", "construction_program"}
    }


def test_hairpin_pcr_endpoint_materializes_exact_adapter_and_primer_route(
    tmp_path: Path,
) -> None:
    result, basal, top_sequence = _valid_pcr_result(tmp_path)
    assert basal.discovery.status is SearchCompletionStatus.COMPLETE

    assert result.status is SearchCompletionStatus.COMPLETE
    realization = result.realizations[0]
    phases = tuple(state.phase for state in realization.construction_program.states)
    assert phases[-4:] == (
        "foldback_closed_hairpin",
        "adapter_annealed",
        "adapter_ligated",
        "hairpin_pcr_duplex",
    )
    cleaved = realization.construction_program.states[1]
    denatured = realization.construction_program.states[2]
    assert denatured.molecules == cleaved.molecules
    assert denatured.pairings == ()
    selected = realization.construction_program.states[3]
    assert all("pcr-bottom-return-arm" not in item.strand_id for item in selected.molecules)
    terminal = realization.construction_program.states[-1]
    assert terminal.molecules[0].sequence == top_sequence
    assert terminal.molecules[1].sequence == reverse_complement_iupac(top_sequence)
    assert len(terminal.pairings) == len(top_sequence)
    assert realization.final_product.cohesive_ends == ()
    assert sum(len(item.sequence) for item in terminal.molecules) == 2 * len(top_sequence)
    functions = realization.final_product.material_function_spans
    assert {item.function for item in functions} == set(MaterialFunction)
    assert all(item.material_span.length.value > 1 for item in functions)
    assert all(
        item.fate.value != "destination_associated"
        for item in realization.final_product.endpoint_sequence_fate_spans
    )


def test_hairpin_pcr_preserves_a_literal_distal_mismatch_through_copying(
    tmp_path: Path,
) -> None:
    payload = _payload()
    foldback = _foldback(payload)
    basal = _basal_result(
        payload,
        ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
        nick_strand=Strand.BOTTOM,
        pairing_allowances=(
            BasalPairAllowance.MATCH,
            BasalPairAllowance.MATCH,
            BasalPairAllowance.MISMATCH,
            BasalPairAllowance.MATCH,
        ),
        recognition_pattern="TGTC",
        cut_offset_reference_strand=4,
    )
    design = _verified_distal_mismatch_design(tmp_path)
    encoding = design.plan.hairpin_encoding_insert.sequence
    adapter = next(
        item for item in basal.realizations[0].materials if item.material_id == "ligation-adapter"
    )
    assert adapter.sequence_5prime == "TTAT"
    request = _construction_request(
        payload=payload,
        foldback=foldback,
        basal=basal,
        design=design,
        endpoint=ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
        adapter=_material(adapter.material_id, adapter.sequence_5prime),
        forward_primer=_material("forward-primer", encoding[:4]),
        reverse_primer=_material("reverse-primer", reverse_complement_iupac(encoding[-1:])),
    )

    result = _discover_raw(request, foldback=foldback, basal=basal, design=design)

    assert result.status is SearchCompletionStatus.TRUNCATED
    assert result.realizations
    realization = result.realizations[0]
    annealing = realization.construction_program.transitions[-3].pcr_authority
    assert annealing is not None
    assert (
        tuple(item.kind for item in annealing.pairings).count(JunctionPairKind.HARD_MISMATCH) == 1
    )
    top, bottom = realization.final_product.strands
    assert top.sequence.endswith(adapter.sequence_5prime)
    assert bottom.sequence.startswith(reverse_complement_iupac(adapter.sequence_5prime))
    adapter_spans = tuple(
        item
        for item in realization.final_product.material_function_spans
        if item.function is MaterialFunction.ADAPTER
    )
    assert {item.endpoint_strand.value for item in adapter_spans} == {"top", "bottom"}
    bottom_adapter = next(item for item in adapter_spans if item.endpoint_strand.value == "bottom")
    mismatch_bottom_index = 1
    assert (
        bottom_adapter.endpoint_span.start.offset
        <= mismatch_bottom_index
        < bottom_adapter.endpoint_span.end.offset
    )
    mismatch_lineage = bottom.lineage[mismatch_bottom_index]
    assert mismatch_lineage.origin_id == adapter.material_id
    assert mismatch_lineage.origin_index == 2
    reverse_primer_spans = tuple(
        item
        for item in realization.final_product.material_function_spans
        if item.function is MaterialFunction.REVERSE_PRIMER
    )
    assert {item.endpoint_strand.value for item in reverse_primer_spans} == {"bottom"}


def test_pcr_fragment_selection_requires_exact_return_arm_identity(tmp_path: Path) -> None:
    result, basal, _ = _valid_pcr_result(tmp_path)
    realization = result.realizations[0]
    cleaved = realization.construction_program.states[1]
    changed = tuple(
        item.model_copy(update={"strand_id": item.strand_id + "-forged"})
        if item.strand_id.endswith("-pcr-bottom-return-arm-top")
        else item
        for item in cleaved.molecules
    )

    with pytest.raises(ValueError, match="exact removable return-arm fragment"):
        select_pcr_fragments(
            changed,
            foldback=realization.foldback_authority,
            source_material_id=realization.materials[0].material_id,
            source_complement_material_id=realization.materials[1].material_id,
            return_arm=next(
                item.sequence_5prime
                for item in basal.realizations[0].materials
                if item.material_id == "ligation-adapter"
            ),
        )


def test_pcr_adapter_pair_kind_must_match_the_h5_profile(tmp_path: Path) -> None:
    result, _, _ = _valid_pcr_result(tmp_path)
    realization = result.realizations[0]
    transition = realization.construction_program.transitions[-3]
    authority = transition.pcr_authority
    assert authority is not None
    changed_kind = (
        JunctionPairKind.HARD_MISMATCH
        if authority.pairings[0].kind is not JunctionPairKind.HARD_MISMATCH
        else JunctionPairKind.WATSON_CRICK
    )
    changed_pair = authority.pairings[0].model_copy(update={"kind": changed_kind})
    changed_authority = authority.model_copy(
        update={"pairings": (changed_pair, *authority.pairings[1:])}
    )
    adapter_annealed = realization.construction_program.states[-3]
    assert realization.basal_authority is not None

    with pytest.raises(ValueError, match="exact H5 pairing profile"):
        validate_adapter_pairing_profile(
            changed_authority,
            basal=realization.basal_authority,
            closed_strand_id=adapter_annealed.molecules[0].strand_id,
            adapter_strand_id=adapter_annealed.molecules[1].strand_id,
        )


def test_primer_extension_rejects_resealed_product_chemistry_and_lineage(
    tmp_path: Path,
) -> None:
    result, _, _ = _valid_pcr_result(tmp_path)
    realization = result.realizations[0]
    program = realization.construction_program
    transition = program.transitions[-1]
    authority = transition.pcr_authority
    assert isinstance(authority, PrimerExtensionAuthority)
    top, bottom = authority.products
    changed_lineage = (
        bottom.lineage[0].model_copy(update={"origin_id": "invented-material"}),
        *bottom.lineage[1:],
    )
    changed_products = (
        bottom.model_copy(update={"five_prime_end": EndChemistry.HYDROXYL}),
        bottom.model_copy(update={"lineage": changed_lineage}),
    )
    for changed_bottom in changed_products:
        changed_state = ConstructionState.create(
            molecules=(top, changed_bottom),
            phase=program.states[-1].phase,
            pairings=program.states[-1].pairings,
        )
        changed_authority = PrimerExtensionAuthority.create(
            pre_state_id=authority.pre_state_id,
            post_state_id=changed_state.state_id,
            forward_primer=authority.forward_primer,
            reverse_primer=authority.reverse_primer,
            bindings=authority.bindings,
            products=(top, changed_bottom),
            pairings=authority.pairings,
            material_function_spans=authority.material_function_spans,
            endpoint_sequence_fate_spans=authority.endpoint_sequence_fate_spans,
        )
        with pytest.raises(ValueError, match=r"lineage|products"):
            validate_pcr_transition(
                kind=transition.kind,
                authority=changed_authority,
                pre_state=program.states[-2],
                post_state=changed_state,
            )


def test_hairpin_pcr_endpoint_reports_adapter_mismatch_as_infeasible(
    tmp_path: Path,
) -> None:
    payload = _payload()
    foldback = _foldback(payload)
    basal = _basal_result(
        payload,
        ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
        nick_strand=Strand.BOTTOM,
    )
    design = _verified_design(tmp_path)
    encoding = design.plan.hairpin_encoding_insert.sequence
    local_adapter = next(
        item for item in basal.realizations[0].materials if item.material_id == "ligation-adapter"
    )
    incompatible_adapters = (
        _material("ligation-adapter", "CCCC"),
        _material("ligation-adapter", local_adapter.sequence_5prime).model_copy(
            update={"five_prime_end": EndChemistry.HYDROXYL}
        ),
    )
    for adapter in incompatible_adapters:
        request = _construction_request(
            payload=payload,
            foldback=foldback,
            basal=basal,
            design=design,
            endpoint=ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
            adapter=adapter,
            forward_primer=_material("forward-primer", encoding[:4]),
            reverse_primer=_material(
                "reverse-primer",
                reverse_complement_iupac(encoding[-4:]),
            ),
        )

        result = _discover_raw(request, foldback=foldback, basal=basal, design=design)

        assert result.status is SearchCompletionStatus.INFEASIBLE
        assert result.realizations == ()
        assert {item.code for item in result.failure_reasons} == {
            CompositionRejectionCode.PCR_ADAPTER_MISMATCH
        }
        assert sum(item.count for item in result.failure_reasons) == len(
            result.combination_dispositions
        )


def test_hairpin_pcr_endpoint_rejects_top_strand_basal_nick(tmp_path: Path) -> None:
    payload = _payload()
    foldback = _foldback(payload)
    basal = _basal_result(payload, ConstructionEndpoint.HAIRPIN_PCR_DUPLEX)
    design = _verified_design(tmp_path)
    encoding = design.plan.hairpin_encoding_insert.sequence
    adapter_sequence = next(
        material.sequence_5prime
        for material in basal.realizations[0].materials
        if material.material_id == "ligation-adapter"
    )
    request = _construction_request(
        payload=payload,
        foldback=foldback,
        basal=basal,
        design=design,
        endpoint=ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
        adapter=_material("ligation-adapter", adapter_sequence),
        forward_primer=_material("forward-primer", encoding[:4]),
        reverse_primer=_material(
            "reverse-primer",
            reverse_complement_iupac(encoding[-4:]),
        ),
    )

    result = _discover_raw(request, foldback=foldback, basal=basal, design=design)

    assert result.status is SearchCompletionStatus.INFEASIBLE
    assert result.realizations == ()
    assert {item.code for item in result.failure_reasons} == {
        CompositionRejectionCode.PCR_BASAL_OPEN_INCOMPATIBLE
    }


def test_pcr_evaluator_rejects_wrong_boundary_and_pairing_profile(tmp_path: Path) -> None:
    payload = _payload()
    foldback = _foldback(payload)
    basal = _basal_result(
        payload,
        ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
        nick_strand=Strand.BOTTOM,
    )
    design = _verified_design(tmp_path)
    encoding = design.plan.hairpin_encoding_insert.sequence
    adapter = next(
        item for item in basal.realizations[0].materials if item.material_id == "ligation-adapter"
    )
    request = _construction_request(
        payload=payload,
        foldback=foldback,
        basal=basal,
        design=design,
        endpoint=ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
        adapter=_material(adapter.material_id, adapter.sequence_5prime),
        forward_primer=_material("forward-primer", encoding[:4]),
        reverse_primer=_material("reverse-primer", reverse_complement_iupac(encoding[-4:])),
    )
    foldback_record = foldback.realizations[0]
    basal_record = basal.realizations[0]
    policies = {
        "foldback_policy": foldback.neighborhood.request.enzyme_provisioning,
        "basal_policy": basal.discovery.request.enzyme_provisioning,
    }
    changed_nick = basal_record.basal_nick.model_copy(
        update={"boundary": Boundary(offset=basal_record.basal_nick.boundary.offset + 1)}
    )
    boundary_result = evaluate_combination(
        request,
        foldback=foldback_record,
        basal=basal_record.model_copy(update={"basal_nick": changed_nick}),
        **policies,
    )
    assert boundary_result.rejection_reason is (
        CompositionRejectionCode.PCR_BASAL_OPEN_INCOMPATIBLE
    )
    complex_state = basal_record.adapter_annealed_complex
    assert complex_state is not None
    changed_pair = complex_state.pairs[0].model_copy(
        update={"left_index": complex_state.pairs[0].left_index + 1}
    )
    profile_result = evaluate_combination(
        request,
        foldback=foldback_record,
        basal=basal_record.model_copy(
            update={
                "adapter_annealed_complex": complex_state.model_copy(
                    update={"pairs": (changed_pair, *complex_state.pairs[1:])}
                )
            }
        ),
        **policies,
    )
    assert profile_result.rejection_reason is (
        CompositionRejectionCode.PCR_PAIRING_PROFILE_MISMATCH
    )


def test_hairpin_pcr_reports_incompatible_primer_as_infeasible(
    tmp_path: Path,
) -> None:
    payload = _payload()
    foldback = _foldback(payload)
    basal = _basal_result(
        payload,
        ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
        nick_strand=Strand.BOTTOM,
    )
    design = _verified_design(tmp_path)
    encoding = design.plan.hairpin_encoding_insert.sequence
    adapter = next(
        item for item in basal.realizations[0].materials if item.material_id == "ligation-adapter"
    )
    incompatible_primers = (
        _material("forward-primer", encoding[:4]).model_copy(
            update={"three_prime_end": EndChemistry.PHOSPHATE}
        ),
        _material("forward-primer", "CCCC"),
    )
    for forward_primer in incompatible_primers:
        request = _construction_request(
            payload=payload,
            foldback=foldback,
            basal=basal,
            design=design,
            endpoint=ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
            adapter=_material(adapter.material_id, adapter.sequence_5prime),
            forward_primer=forward_primer,
            reverse_primer=_material("reverse-primer", reverse_complement_iupac(encoding[-4:])),
        )

        result = _discover_raw(request, foldback=foldback, basal=basal, design=design)

        assert result.status is SearchCompletionStatus.INFEASIBLE
        assert result.realizations == ()
        assert {item.code for item in result.failure_reasons} == {
            CompositionRejectionCode.PCR_PRIMER_MISMATCH
        }


def test_pcr_endpoint_addition_preserves_direct_canonical_authority(tmp_path: Path) -> None:
    payload = _payload()
    foldback = _foldback(payload)
    basal = _basal_result(payload)
    design = _verified_design(tmp_path)
    request = _construction_request(
        payload=payload,
        foldback=foldback,
        basal=basal,
        design=design,
    )

    result = _discover_raw(request, foldback=foldback, basal=basal, design=design)

    assert result.result_id == (
        "hop:construction-space-result/"
        "54af957a08cb9549e75aa8af245f008d35964226a1471cb91599ff89c9252e01@1"
    )
    assert (
        hashlib.sha256(canonical_json_bytes(result)).hexdigest()
        == (
            "8e48e743e2d3efdc453f017e58aa0d1ffeda375f07be2b1498fac2ef9a93a45e"  # pragma: allowlist secret  # noqa: E501
        )
    )
    assert tuple(item.materialized_realization_id for item in result.realizations) == (
        "hop:materialized-construction/"
        "1d766561ecf77aacfca0687fba7df04011b508942c62cceee4af4923a281460f@1",
        "hop:materialized-construction/"
        "d0072fe6850917452c03738b239eb71f05181473bb5afd586b6098bdf180e3fa@1",
    )
    assert tuple(item.construction_program.program_id for item in result.realizations) == (
        "hop:construction-program/"
        "139e238ba5151e34dad0b257f6ff82dea68dbfbdd45ce34c8b46e83a0e3aad0d@1",
        "hop:construction-program/"
        "03d1c85221b9ad1f94a56b307f722fbc63fcf0b13ea5e25030502ec81cefa7d3@1",
    )
    assert tuple(item.final_product.reference.final_product_id for item in result.realizations) == (
        "hop:final-product/31ec12c1d24c9c10e6c8bc22e815aac01842be4fc019cc18a2a36962f5117237@1",
        "hop:final-product/31ec12c1d24c9c10e6c8bc22e815aac01842be4fc019cc18a2a36962f5117237@1",
    )
    assert (
        tuple(
            hashlib.sha256(canonical_json_bytes(item)).hexdigest() for item in result.realizations
        )
        == (
            "33a918392060e2598638766f51d00da308741bcd093f2c1a89d9feea67543867",  # pragma: allowlist secret  # noqa: E501
            "e70eff1078aef739899eecd46a3078da885d52686fa4beafa01a6a885a8044f4",  # pragma: allowlist secret  # noqa: E501
        )
    )


def test_clone_endpoint_addition_preserves_pcr_canonical_authority(tmp_path: Path) -> None:
    result, _, _ = _valid_pcr_result(tmp_path)

    assert result.result_id == (
        "hop:construction-space-result/"
        "6f01d7324391f9427e52190635085be7e065229fda8f29125c58d142ea1c1b0a@1"
    )
    assert (
        hashlib.sha256(canonical_json_bytes(result)).hexdigest()
        == (
            "26c2d1bf4d2aa3660f0b75b4508a7f43ef002fca2ede29d8c0b69a1d6e3fcb90"  # pragma: allowlist secret  # noqa: E501
        )
    )
    assert tuple(item.materialized_realization_id for item in result.realizations) == (
        "hop:materialized-construction/"
        "362dc73bc427c0a6045686ea90eba46fabffd0191e97333cb8c38394e269c1a7@1",
        "hop:materialized-construction/"
        "4a1f9f7fdce9208a34fcbef78a16e37622ea923d012a1bdc289938fa3b5169ae@1",
    )
    assert tuple(item.construction_program.program_id for item in result.realizations) == (
        "hop:construction-program/"
        "11988297cf8980429f3269a6bacc94ef388a70857443a831bdd99f6f1494f2ca@1",
        "hop:construction-program/"
        "56ab4dbb9d1531bc91e07772b858929c6d980a7eb00e2b2f490871ea41613751@1",
    )
    assert tuple(item.final_product.reference.final_product_id for item in result.realizations) == (
        "hop:final-product/d19850d0caffdcb47866535ea8b9b8dc296e18b3d5f28c8e9c0c9b1f49a1ccb2@1",
        "hop:final-product/a40b77f7fec01ebae3113ce6f419ab4f7bd046d422836f3f3ae58bbbc71f51fb@1",
    )
    assert (
        tuple(
            hashlib.sha256(canonical_json_bytes(item)).hexdigest() for item in result.realizations
        )
        == (
            "453e9e6cd1d2a670e34dec7c7801a19206d57203a4ffee9b3bf0f919e0350d99",  # pragma: allowlist secret  # noqa: E501
            "9c3ad24fc9e40ec60986965d651a2494ed21fb20878366a2090f6babf2a2c4a4",  # pragma: allowlist secret  # noqa: E501
        )
    )


def test_direct_endpoint_accepts_a_valid_bottom_basal_nick_without_pcr_splitting(
    tmp_path: Path,
) -> None:
    payload = _payload()
    foldback = _foldback(payload)
    basal = _basal_result(payload, nick_strand=Strand.BOTTOM)
    assert basal.discovery.status is SearchCompletionStatus.COMPLETE
    design = _verified_design(tmp_path)
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
        "pcr-bottom" not in strand.strand_id
        for realization in result.realizations
        for state in realization.construction_program.states
        for strand in state.molecules
    )


def test_adapter_ligation_binds_the_exact_pre_state_adapter_material(tmp_path: Path) -> None:
    result, _, _ = _valid_pcr_result(tmp_path)
    program = result.realizations[0].construction_program
    transition = program.transitions[-2]
    authority = transition.pcr_authority
    assert isinstance(authority, AdapterLigationAuthority)
    changed_adapter = authority.adapter.model_copy(update={"material_id": "unrelated-adapter"})
    changed = AdapterLigationAuthority.create(
        pre_state_id=authority.pre_state_id,
        post_state_id=authority.post_state_id,
        adapter=changed_adapter,
        bond=authority.bond,
        product=authority.product,
    )

    with pytest.raises(ValueError, match="exact pre-state adapter material"):
        validate_pcr_transition(
            kind=transition.kind,
            authority=changed,
            pre_state=program.states[-3],
            post_state=program.states[-2],
        )

    changed_transition = ConstructionTransition.create(
        kind=transition.kind,
        pre_state_id=transition.pre_state_id,
        post_state_id=transition.post_state_id,
        pcr_authority=changed,
    )
    changed_program = _unchecked_program(
        program,
        transitions=(*program.transitions[:-2], changed_transition, program.transitions[-1]),
    )
    realization = result.realizations[0]
    with pytest.raises(ValidationError, match="exact pre-state adapter material"):
        MaterializedConstructionRealization.create(
            **_realization_content(realization),
            construction_program=changed_program,
        )


def test_adapter_ligation_preserves_existing_bonds_and_remaps_exact_pairings(
    tmp_path: Path,
) -> None:
    result, _, _ = _valid_pcr_result(tmp_path)
    program = result.realizations[0].construction_program
    transition = program.transitions[-2]
    authority = transition.pcr_authority
    assert isinstance(authority, AdapterLigationAuthority)
    post = program.states[-2]
    forged_bond = post.formed_bonds[0].model_copy(update={"bond": post.formed_bonds[-1].bond})
    changed_states = (
        ConstructionState.create(
            molecules=post.molecules,
            phase=post.phase,
            pairings=post.pairings,
            formed_bonds=(forged_bond, post.formed_bonds[-1]),
        ),
        ConstructionState.create(
            molecules=post.molecules,
            phase=post.phase,
            pairings=tuple(reversed(post.pairings)),
            formed_bonds=post.formed_bonds,
        ),
    )
    for changed_post in changed_states:
        changed = AdapterLigationAuthority.create(
            pre_state_id=authority.pre_state_id,
            post_state_id=changed_post.state_id,
            adapter=authority.adapter,
            bond=authority.bond,
            product=authority.product,
        )
        with pytest.raises(ValueError, match=r"pre-existing bonds|exact remapped pairings"):
            validate_pcr_transition(
                kind=transition.kind,
                authority=changed,
                pre_state=program.states[-3],
                post_state=changed_post,
            )
        changed_transition = ConstructionTransition.create(
            kind=transition.kind,
            pre_state_id=transition.pre_state_id,
            post_state_id=changed_post.state_id,
            pcr_authority=changed,
        )
        terminal_transition = program.transitions[-1]
        terminal_authority = terminal_transition.pcr_authority
        assert isinstance(terminal_authority, PrimerExtensionAuthority)
        changed_terminal_authority = PrimerExtensionAuthority.create(
            pre_state_id=changed_post.state_id,
            post_state_id=terminal_authority.post_state_id,
            forward_primer=terminal_authority.forward_primer,
            reverse_primer=terminal_authority.reverse_primer,
            bindings=terminal_authority.bindings,
            products=terminal_authority.products,
            pairings=terminal_authority.pairings,
            material_function_spans=terminal_authority.material_function_spans,
            endpoint_sequence_fate_spans=terminal_authority.endpoint_sequence_fate_spans,
        )
        changed_terminal_transition = ConstructionTransition.create(
            kind=terminal_transition.kind,
            pre_state_id=changed_post.state_id,
            post_state_id=terminal_transition.post_state_id,
            pcr_authority=changed_terminal_authority,
        )
        changed_program = _unchecked_program(
            program,
            states=(*program.states[:-2], changed_post, program.states[-1]),
            transitions=(
                *program.transitions[:-2],
                changed_transition,
                changed_terminal_transition,
            ),
        )
        realization = result.realizations[0]
        with pytest.raises(
            ValidationError,
            match=r"pre-existing bonds|exact remapped pairings",
        ):
            MaterializedConstructionRealization.create(
                **_realization_content(realization),
                construction_program=changed_program,
            )


def test_primer_extension_requires_canonical_antiparallel_pair_order(tmp_path: Path) -> None:
    result, _, _ = _valid_pcr_result(tmp_path)
    program = result.realizations[0].construction_program
    transition = program.transitions[-1]
    authority = transition.pcr_authority
    assert isinstance(authority, PrimerExtensionAuthority)
    changed_pairs = tuple(reversed(authority.pairings))
    changed_state = ConstructionState.create(
        molecules=authority.products,
        phase=program.states[-1].phase,
        pairings=changed_pairs,
    )
    changed = PrimerExtensionAuthority.create(
        pre_state_id=authority.pre_state_id,
        post_state_id=changed_state.state_id,
        forward_primer=authority.forward_primer,
        reverse_primer=authority.reverse_primer,
        bindings=authority.bindings,
        products=authority.products,
        pairings=changed_pairs,
        material_function_spans=authority.material_function_spans,
        endpoint_sequence_fate_spans=authority.endpoint_sequence_fate_spans,
    )

    with pytest.raises(ValueError, match="canonical antiparallel"):
        validate_pcr_transition(
            kind=transition.kind,
            authority=changed,
            pre_state=program.states[-2],
            post_state=changed_state,
        )
    changed_transition = ConstructionTransition.create(
        kind=transition.kind,
        pre_state_id=transition.pre_state_id,
        post_state_id=changed_state.state_id,
        pcr_authority=changed,
    )
    changed_program = _unchecked_program(
        program,
        states=(*program.states[:-1], changed_state),
        transitions=(*program.transitions[:-1], changed_transition),
    )
    realization = result.realizations[0]
    old_product = realization.final_product
    old_reference = old_product.reference
    assert isinstance(old_reference, DuplexFinalProductReference)
    changed_reference = DuplexFinalProductReference.create(
        endpoint=old_reference.endpoint,
        sequence=old_reference.sequence,
        topology=old_reference.topology,
        end_descriptors=old_reference.end_descriptors,
        strands=old_reference.strands,
        pairings=changed_pairs,
        cohesive_ends=old_reference.cohesive_ends,
    )
    changed_product = MaterializedFinalProduct(
        reference=changed_reference,
        strands=old_product.strands,
        encoding_projection=old_product.encoding_projection,
        pairings=changed_pairs,
        cohesive_ends=old_product.cohesive_ends,
        material_function_spans=old_product.material_function_spans,
        endpoint_sequence_fate_spans=old_product.endpoint_sequence_fate_spans,
    )
    changed_complete = CompleteConstructionRealization.create(
        precursor_sequence=realization.realization.precursor_sequence,
        local_realization_ids=realization.realization.local_realization_ids,
        stage_ids=realization.realization.stage_ids,
        final_product_id=changed_reference.final_product_id,
    )
    content = {
        name: getattr(realization, name)
        for name in type(realization).model_fields
        if name
        not in {
            "materialized_realization_id",
            "construction_program",
            "final_product",
            "realization",
        }
    }
    with pytest.raises(ValidationError, match="canonical antiparallel"):
        MaterializedConstructionRealization.create(
            **content,
            realization=changed_complete,
            construction_program=changed_program,
            final_product=changed_product,
        )


def test_pcr_reaction_program_has_content_bound_endpoint_specific_identity(
    tmp_path: Path,
) -> None:
    result, _, _ = _valid_pcr_result(tmp_path)
    realization = result.realizations[0]
    foldback = realization.foldback_authority
    basal = realization.basal_authority
    assert basal is not None
    prefix = realization.materials[0].sequence_5prime.removesuffix(
        foldback.source_reference_sequence
    )
    adapter = realization.materials[2].sequence_5prime
    direct = derive_direct_reaction_program(
        foldback=foldback,
        basal=basal,
        prefix=prefix,
        return_arm=adapter,
    )
    pcr = derive_pcr_reaction_program(
        foldback=foldback,
        basal=basal,
        prefix=prefix,
        return_arm=adapter,
    )
    changed = derive_pcr_reaction_program(
        foldback=foldback,
        basal=basal,
        prefix=prefix,
        return_arm="A" + adapter[1:],
    )

    assert pcr.program_id != direct.program_id
    assert changed.program_id != pcr.program_id


def test_pcr_route_accounts_for_removed_return_arm_as_transient_material(
    tmp_path: Path,
) -> None:
    result, _, _ = _valid_pcr_result(tmp_path)
    realization = result.realizations[0]
    complement = realization.materials[1]
    records = tuple(
        item
        for item in realization.route_material_dispositions
        if item.material_id == complement.material_id
        and item.disposition is MaterialRetentionDisposition.TRANSIENT
    )

    assert len(records) == 1
    removed = records[0]
    assert (
        complement.sequence_5prime[
            removed.material_span.start.offset : removed.material_span.end.offset
        ]
        == realization.materials[2].sequence_5prime
    )
    assert removed.endpoint_occurrences == ()
    transition_by_id = {
        item.transition_id: item for item in realization.construction_program.transitions
    }
    assert removed.removal_transition_id is not None
    assert (
        transition_by_id[removed.removal_transition_id].kind
        is ConstructionTransitionKind.FRAGMENT_SELECTION
    )


def test_pcr_route_rejects_forged_material_disposition_evidence(tmp_path: Path) -> None:
    result, _, _ = _valid_pcr_result(tmp_path)
    realization = result.realizations[0]
    records = realization.route_material_dispositions
    transient_index = next(
        index
        for index, item in enumerate(records)
        if item.disposition is MaterialRetentionDisposition.TRANSIENT
    )
    transient = records[transient_index]
    for changed in (
        transient.model_copy(
            update={
                "material_span": transient.material_span.model_copy(
                    update={"start": Boundary(offset=transient.material_span.start.offset + 1)}
                )
            }
        ),
        transient.model_copy(
            update={
                "disposition": MaterialRetentionDisposition.RETAINED,
                "removal_transition_id": None,
            }
        ),
        transient.model_copy(
            update={
                "removal_transition_id": (
                    realization.construction_program.transitions[0].transition_id
                )
            }
        ),
    ):
        changed_records = (*records[:transient_index], changed, *records[transient_index + 1 :])
        content = {
            name: getattr(realization, name)
            for name in type(realization).model_fields
            if name not in {"materialized_realization_id", "route_material_dispositions"}
        }
        with pytest.raises(ValidationError, match=r"material|Material"):
            MaterializedConstructionRealization.create(
                **content,
                route_material_dispositions=changed_records,
            )


def test_pcr_transition_replay_rejects_exact_molecular_forgery_matrix(
    tmp_path: Path,
) -> None:
    result, _, _ = _valid_pcr_result(tmp_path)
    program = result.realizations[0].construction_program

    annealing_transition = program.transitions[-3]
    annealing = annealing_transition.pcr_authority
    assert annealing is not None
    annealing_pre = program.states[-4]
    annealing_post = program.states[-3]
    changed_hairpin = annealing_post.molecules[0].model_copy(
        update={"sequence": _substitute_first_base(annealing_post.molecules[0].sequence)}
    )
    changed_adapter = annealing_post.molecules[1].model_copy(
        update={"sequence": _substitute_first_base(annealing_post.molecules[1].sequence)}
    )
    annealing_cases = (
        (
            annealing,
            annealing_pre.model_copy(update={"molecules": ()}),
            annealing_post,
            "one hairpin and one adapter",
        ),
        (
            annealing,
            annealing_pre,
            annealing_post.model_copy(
                update={"molecules": (changed_hairpin, annealing_post.molecules[1])}
            ),
            "preserve the exact closed hairpin",
        ),
        (
            annealing,
            annealing_pre,
            annealing_post.model_copy(
                update={"molecules": (annealing_post.molecules[0], changed_adapter)}
            ),
            "exact declared material",
        ),
        (
            annealing,
            annealing_pre,
            annealing_post.model_copy(
                update={"pairings": tuple(reversed(annealing_post.pairings))}
            ),
            "preserve and replace exact associations",
        ),
        (
            annealing,
            annealing_pre,
            annealing_post.model_copy(update={"formed_bonds": ()}),
            "cannot change covalent bonds",
        ),
    )
    for authority, pre_state, post_state, message in annealing_cases:
        with pytest.raises(ValueError, match=message):
            validate_pcr_transition(
                kind=annealing_transition.kind,
                authority=authority,
                pre_state=pre_state,
                post_state=post_state,
            )

    ligation_transition = program.transitions[-2]
    ligation = ligation_transition.pcr_authority
    assert isinstance(ligation, AdapterLigationAuthority)
    ligation_pre = program.states[-3]
    ligation_post = program.states[-2]
    nonphosphorylated_adapter = ligation_pre.molecules[1].model_copy(
        update={"five_prime_end": EndChemistry.HYDROXYL}
    )
    changed_product = ligation.product.model_copy(
        update={"sequence": _substitute_first_base(ligation.product.sequence)}
    )
    ligation_cases = (
        (
            ligation,
            ligation_pre,
            ligation_post.model_copy(update={"molecules": ()}),
            "one exact declared strand",
        ),
        (
            ligation,
            ligation_pre.model_copy(
                update={"molecules": (ligation_pre.molecules[0], nonphosphorylated_adapter)}
            ),
            ligation_post,
            "hairpin 3-prime OH and adapter 5-prime P",
        ),
        (
            ligation.model_copy(update={"product": changed_product}),
            ligation_pre,
            ligation_post.model_copy(update={"molecules": (changed_product,)}),
            "exact sequence and lineage",
        ),
    )
    for authority, pre_state, post_state, message in ligation_cases:
        with pytest.raises(ValueError, match=message):
            validate_pcr_transition(
                kind=ligation_transition.kind,
                authority=authority,
                pre_state=pre_state,
                post_state=post_state,
            )

    extension_transition = program.transitions[-1]
    extension = extension_transition.pcr_authority
    assert isinstance(extension, PrimerExtensionAuthority)
    extension_pre = program.states[-2]
    extension_post = program.states[-1]
    top, bottom = extension.products
    changed_bottom = bottom.model_copy(update={"sequence": _substitute_first_base(bottom.sequence)})
    changed_function = extension.material_function_spans[0].model_copy(
        update={"material_id": "unrelated-material"}
    )
    changed_binding = extension.bindings[0].model_copy(
        update={
            "template_span": extension.bindings[0].template_span.model_copy(
                update={
                    "start": Boundary(offset=extension.bindings[0].template_span.start.offset + 1)
                }
            )
        }
    )
    nonpayload_fates = tuple(
        item.model_copy(update={"fate": EndpointSequenceFate.RETAINED_CONSTRUCTION})
        for item in extension.endpoint_sequence_fate_spans
    )
    extension_cases = (
        (
            extension,
            extension_pre,
            extension_post.model_copy(update={"molecules": tuple(reversed(extension.products))}),
            "exact ordered duplex strands",
        ),
        (
            extension.model_copy(
                update={
                    "forward_primer": extension.forward_primer.model_copy(
                        update={"three_prime_end": EndChemistry.PHOSPHATE}
                    )
                }
            ),
            extension_pre,
            extension_post,
            "three-prime hydroxyl",
        ),
        (
            extension.model_copy(update={"products": (top, changed_bottom)}),
            extension_pre,
            extension_post.model_copy(update={"molecules": (top, changed_bottom)}),
            "exact reverse complements",
        ),
        (
            extension.model_copy(update={"pairings": extension.pairings[:-1]}),
            extension_pre,
            extension_post.model_copy(update={"pairings": extension.pairings[:-1]}),
            "cover every exact base pair",
        ),
        (
            extension,
            extension_pre,
            extension_post.model_copy(update={"formed_bonds": extension_pre.formed_bonds}),
            "cannot inherit precursor ligation bonds",
        ),
        (
            extension.model_copy(
                update={
                    "material_function_spans": (
                        changed_function,
                        *extension.material_function_spans[1:],
                    )
                }
            ),
            extension_pre,
            extension_post,
            "spans must bind both exact primers",
        ),
        (
            extension.model_copy(
                update={
                    "forward_primer": extension.forward_primer.model_copy(
                        update={
                            "sequence_5prime": _substitute_first_base(
                                extension.forward_primer.sequence_5prime
                            )
                        }
                    )
                }
            ),
            extension_pre,
            extension_post,
            "preserve both exact primer sequences",
        ),
        (
            extension.model_copy(update={"bindings": (changed_binding, extension.bindings[1])}),
            extension_pre,
            extension_post,
            "exact template boundaries",
        ),
        (
            extension.model_copy(update={"endpoint_sequence_fate_spans": nonpayload_fates}),
            extension_pre,
            extension_post,
            "identify the exact payload span",
        ),
    )
    for authority, pre_state, post_state, message in extension_cases:
        with pytest.raises(ValueError, match=message):
            validate_pcr_transition(
                kind=extension_transition.kind,
                authority=authority,
                pre_state=pre_state,
                post_state=post_state,
            )
    with pytest.raises(ValueError, match="kind must match"):
        validate_pcr_transition(
            kind=ConstructionTransitionKind.ANNEALING,
            authority=extension,
            pre_state=extension_pre,
            post_state=extension_post,
        )


def test_pcr_realization_replay_rejects_exact_authority_forgery_matrix(
    tmp_path: Path,
) -> None:
    result, _, _ = _valid_pcr_result(tmp_path)
    realization = result.realizations[0]
    program = realization.construction_program
    basal = realization.basal_authority
    assert basal is not None
    profile = basal.projection.pairing_profile
    assert profile is not None
    annealing = program.transitions[-3].pcr_authority
    assert annealing is not None
    adapter_state = program.states[-3]

    with pytest.raises(ValueError, match="exact basal adapter-pairing authority"):
        validate_adapter_pairing_profile(
            annealing,
            basal=basal.model_copy(
                update={"projection": basal.projection.model_copy(update={"pairing_profile": None})}
            ),
            closed_strand_id=adapter_state.molecules[0].strand_id,
            adapter_strand_id=adapter_state.molecules[1].strand_id,
        )

    changed_nick = basal.basal_nick.model_copy(
        update={"boundary": Boundary(offset=basal.basal_nick.boundary.offset + 1)}
    )
    changed_cleaved = program.states[1].model_copy(
        update={"molecules": tuple(reversed(program.states[1].molecules))}
    )
    changed_denatured = program.states[2].model_copy(
        update={"pairings": program.states[1].pairings}
    )
    changed_selected = program.states[3].model_copy(
        update={"molecules": tuple(reversed(program.states[3].molecules))}
    )
    changed_tail = program.states[-4].model_copy(
        update={"phase": ConstructionStatePhase.ADAPTER_ANNEALED}
    )
    changed_end_transition = program.transitions[0].model_copy(
        update={"kind": ConstructionTransitionKind.END_GENERATION}
    )
    no_adapter_authority = program.transitions[-3].model_copy(update={"pcr_authority": None})
    no_extension_authority = program.transitions[-1].model_copy(update={"pcr_authority": None})
    changed_product_strands = realization.final_product.model_copy(
        update={"strands": tuple(reversed(realization.final_product.strands))}
    )
    changed_projection = realization.final_product.encoding_projection.model_copy(
        update={"orientation": BindingOrientation.REVERSE_COMPLEMENT_5TO3}
    )
    changed_design = realization.design.model_copy(
        update={"encoding_sequence": _substitute_first_base(realization.design.encoding_sequence)}
    )
    changed_functions = realization.final_product.model_copy(
        update={
            "material_function_spans": tuple(
                reversed(realization.final_product.material_function_spans)
            )
        }
    )
    changed_fates = realization.final_product.model_copy(
        update={
            "endpoint_sequence_fate_spans": tuple(
                reversed(realization.final_product.endpoint_sequence_fate_spans)
            )
        }
    )
    cases = (
        (
            realization.model_copy(update={"basal_authority": None}),
            "bottom-strand basal nick authority",
        ),
        (
            realization.model_copy(
                update={"basal_authority": basal.model_copy(update={"basal_nick": changed_nick})}
            ),
            "aligned prefix boundary",
        ),
        (
            realization.model_copy(
                update={
                    "construction_program": program.model_copy(update={"reaction_programs": ()})
                }
            ),
            "exact basal-open local authorities",
        ),
        (
            realization.model_copy(
                update={
                    "construction_program": program.model_copy(
                        update={"states": (program.states[0], changed_cleaved, *program.states[2:])}
                    )
                }
            ),
            "source-fragment authorities",
        ),
        (
            realization.model_copy(
                update={
                    "construction_program": program.model_copy(
                        update={
                            "states": (
                                *program.states[:2],
                                changed_denatured,
                                *program.states[3:],
                            )
                        }
                    )
                }
            ),
            "denaturation may only remove duplex associations",
        ),
        (
            realization.model_copy(
                update={
                    "construction_program": program.model_copy(
                        update={
                            "states": (
                                *program.states[:3],
                                changed_selected,
                                *program.states[4:],
                            )
                        }
                    )
                }
            ),
            "selection must retain the exact source and foldback fragments",
        ),
        (
            realization.model_copy(
                update={
                    "construction_program": program.model_copy(
                        update={
                            "states": (*program.states[:-4], changed_tail, *program.states[-3:])
                        }
                    )
                }
            ),
            "preserve exact foldback, adapter, and duplex phases",
        ),
        (
            realization.model_copy(
                update={
                    "construction_program": program.model_copy(
                        update={"transitions": (changed_end_transition, *program.transitions[1:])}
                    )
                }
            ),
            "cannot contain end-generation evidence",
        ),
        (
            realization.model_copy(
                update={
                    "construction_program": program.model_copy(
                        update={
                            "transitions": (
                                *program.transitions[:-3],
                                no_adapter_authority,
                                *program.transitions[-2:],
                            )
                        }
                    )
                }
            ),
            "exact basal adapter-pairing authority",
        ),
        (
            realization.model_copy(
                update={
                    "construction_program": program.model_copy(
                        update={"transitions": (*program.transitions[:-1], no_extension_authority)}
                    )
                }
            ),
            "exact primer-extension authority",
        ),
        (
            realization.model_copy(update={"final_product": changed_product_strands}),
            "exact terminal duplex graph",
        ),
        (
            realization.model_copy(
                update={
                    "final_product": realization.final_product.model_copy(
                        update={"encoding_projection": changed_projection}
                    )
                }
            ),
            "exact top-strand subspan",
        ),
        (
            realization.model_copy(update={"design": changed_design}),
            "projection must equal the verified design",
        ),
        (
            realization.model_copy(update={"final_product": changed_functions}),
            "spans must replay exact retained lineage",
        ),
        (
            realization.model_copy(update={"final_product": changed_fates}),
            "spans must replay exact design features",
        ),
    )
    for changed, message in cases:
        with pytest.raises(ValueError, match=message):
            validate_pcr_realization(changed)


def test_primer_extension_rejects_shifted_material_function_endpoint_span(
    tmp_path: Path,
) -> None:
    result, _, _ = _valid_pcr_result(tmp_path)
    program = result.realizations[0].construction_program
    transition = program.transitions[-1]
    authority = transition.pcr_authority
    assert isinstance(authority, PrimerExtensionAuthority)
    record = authority.material_function_spans[0]
    shifted = record.model_copy(
        update={
            "endpoint_span": record.endpoint_span.model_copy(
                update={
                    "start": Boundary(offset=record.endpoint_span.start.offset + 1),
                    "end": Boundary(offset=record.endpoint_span.end.offset + 1),
                }
            )
        }
    )
    changed_authority = PrimerExtensionAuthority.create(
        **{
            name: (
                (shifted, *authority.material_function_spans[1:])
                if name == "material_function_spans"
                else getattr(authority, name)
            )
            for name in type(authority).model_fields
            if name != "authority_id"
        }
    )

    with pytest.raises(ValueError, match="exact endpoint lineage"):
        validate_pcr_transition(
            kind=transition.kind,
            authority=changed_authority,
            pre_state=program.states[-2],
            post_state=program.states[-1],
        )

    changed_transition = ConstructionTransition.create(
        kind=transition.kind,
        pre_state_id=transition.pre_state_id,
        post_state_id=transition.post_state_id,
        pcr_authority=changed_authority,
    )
    with pytest.raises(ValidationError, match="exact endpoint lineage"):
        ConstructionProgram.create(
            states=program.states,
            transitions=(*program.transitions[:-1], changed_transition),
            reaction_programs=program.reaction_programs,
            stage_assessments=program.stage_assessments,
        )


@pytest.mark.parametrize(
    "assigned_roles",
    (
        (
            MaterialFunction.SOURCE_REFERENCE,
            MaterialFunction.ADAPTER,
            MaterialFunction.SOURCE_COMPLEMENT,
        ),
        (
            MaterialFunction.SOURCE_COMPLEMENT,
            MaterialFunction.SOURCE_REFERENCE,
            MaterialFunction.ADAPTER,
        ),
        (
            MaterialFunction.SOURCE_COMPLEMENT,
            MaterialFunction.ADAPTER,
            MaterialFunction.SOURCE_REFERENCE,
        ),
        (
            MaterialFunction.ADAPTER,
            MaterialFunction.SOURCE_REFERENCE,
            MaterialFunction.SOURCE_COMPLEMENT,
        ),
        (
            MaterialFunction.ADAPTER,
            MaterialFunction.SOURCE_COMPLEMENT,
            MaterialFunction.SOURCE_REFERENCE,
        ),
    ),
)
def test_primer_extension_rejects_coordinated_material_role_relabeling(
    tmp_path: Path,
    assigned_roles: tuple[MaterialFunction, MaterialFunction, MaterialFunction],
) -> None:
    result, _, _ = _valid_pcr_result(tmp_path)
    program = result.realizations[0].construction_program
    transition = program.transitions[-1]
    authority = transition.pcr_authority
    assert isinstance(authority, PrimerExtensionAuthority)
    route_roles = (
        MaterialFunction.SOURCE_REFERENCE,
        MaterialFunction.SOURCE_COMPLEMENT,
        MaterialFunction.ADAPTER,
    )
    relabeling = dict(zip(route_roles, assigned_roles, strict=True))
    swapped = tuple(
        record.model_copy(update={"function": relabeling.get(record.function, record.function)})
        for record in authority.material_function_spans
    )
    changed_authority = PrimerExtensionAuthority.create(
        **{
            name: swapped if name == "material_function_spans" else getattr(authority, name)
            for name in type(authority).model_fields
            if name != "authority_id"
        }
    )

    with pytest.raises(ValueError, match="exact route material roles"):
        validate_pcr_transition(
            kind=transition.kind,
            authority=changed_authority,
            pre_state=program.states[-2],
            post_state=program.states[-1],
        )

    changed_transition = ConstructionTransition.create(
        kind=transition.kind,
        pre_state_id=transition.pre_state_id,
        post_state_id=transition.post_state_id,
        pcr_authority=changed_authority,
    )
    with pytest.raises(ValidationError, match="exact route material roles"):
        ConstructionProgram.create(
            states=program.states,
            transitions=(*program.transitions[:-1], changed_transition),
            reaction_programs=program.reaction_programs,
            stage_assessments=program.stage_assessments,
        )


def test_final_product_rejects_endpoint_shape_forgery(tmp_path: Path) -> None:
    pcr_result, _, _ = _valid_pcr_result(tmp_path)
    pcr_product = pcr_result.realizations[0].final_product
    payload = _payload()
    foldback = _foldback(payload)
    basal = _basal_result(payload)
    design = _verified_design(tmp_path / "direct-shape")
    direct_result = _discover_raw(
        _construction_request(
            payload=payload,
            foldback=foldback,
            basal=basal,
            design=design,
        ),
        foldback=foldback,
        basal=basal,
        design=design,
    )
    direct_product = direct_result.realizations[0].final_product
    direct_strand = direct_product.strands[0]
    pcr_top, pcr_bottom = pcr_product.strands
    malformed_direct_reference = direct_product.reference.create(
        endpoint=ConstructionEndpoint.SSDNA_HAIRPIN,
        sequence=direct_strand.sequence,
        topology="linear_duplex",
        end_descriptors=(
            direct_strand.five_prime_end.value,
            direct_strand.three_prime_end.value,
            pcr_bottom.five_prime_end.value,
            pcr_bottom.three_prime_end.value,
        ),
    )
    malformed_pcr_reference = direct_product.reference.create(
        endpoint=ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
        sequence=pcr_top.sequence,
        topology="single_stranded_hairpin",
        end_descriptors=(
            pcr_top.five_prime_end.value,
            pcr_top.three_prime_end.value,
        ),
    )
    changed_five_prime = (
        EndChemistry.PHOSPHATE
        if direct_strand.five_prime_end is not EndChemistry.PHOSPHATE
        else EndChemistry.HYDROXYL
    )
    malformed_end_reference = direct_product.reference.create(
        endpoint=ConstructionEndpoint.SSDNA_HAIRPIN,
        sequence=direct_strand.sequence,
        topology="single_stranded_hairpin",
        end_descriptors=(
            changed_five_prime.value,
            direct_strand.three_prime_end.value,
        ),
    )

    with pytest.raises(ValidationError, match="direct ssDNA endpoint shape"):
        MaterializedFinalProduct(
            reference=malformed_direct_reference,
            strands=(direct_strand, pcr_bottom),
            encoding_projection=direct_product.encoding_projection,
        )
    with pytest.raises(ValidationError, match="PCR duplex reference"):
        MaterializedFinalProduct(
            reference=malformed_pcr_reference,
            strands=(pcr_top,),
            encoding_projection=pcr_product.encoding_projection,
        )
    with pytest.raises(ValidationError, match="exact strand-end chemistry"):
        MaterializedFinalProduct(
            reference=malformed_end_reference,
            strands=(direct_strand,),
            encoding_projection=direct_product.encoding_projection,
        )


def test_direct_endpoint_rejects_pcr_only_evidence_fields(tmp_path: Path) -> None:
    pcr_result, _, _ = _valid_pcr_result(tmp_path)
    pcr_realization = pcr_result.realizations[0]
    payload = _payload()
    foldback = _foldback(payload)
    basal = _basal_result(payload)
    design = _verified_design(tmp_path / "direct")
    direct_result = _discover_raw(
        _construction_request(
            payload=payload,
            foldback=foldback,
            basal=basal,
            design=design,
        ),
        foldback=foldback,
        basal=basal,
        design=design,
    )
    direct = direct_result.realizations[0]
    direct_content = {
        name: getattr(direct, name)
        for name in type(direct).model_fields
        if name not in {"materialized_realization_id", "final_product"}
    }
    forged_products = (
        direct.final_product.model_copy(
            update={"pairings": pcr_realization.final_product.pairings}
        ),
        direct.final_product.model_copy(
            update={
                "cohesive_ends": (
                    CohesiveEnd(
                        product_end="left",
                        protruding_strand_id=direct.final_product.strands[0].strand_id,
                        overhang_end=StrandEnd.FIVE_PRIME,
                        sequence="A",
                        source_span=Span(
                            start=Boundary(offset=0),
                            end=Boundary(offset=1),
                        ),
                        primary_cut=Boundary(offset=0),
                        complementary_cut=Boundary(offset=1),
                    ),
                )
            }
        ),
        direct.final_product.model_copy(
            update={
                "material_function_spans": pcr_realization.final_product.material_function_spans
            }
        ),
        direct.final_product.model_copy(
            update={
                "endpoint_sequence_fate_spans": (
                    pcr_realization.final_product.endpoint_sequence_fate_spans
                )
            }
        ),
    )
    for product in forged_products:
        with pytest.raises(ValidationError, match="PCR-only evidence"):
            MaterializedConstructionRealization.create(
                **direct_content,
                final_product=product,
            )

    disposition_content = {
        name: getattr(direct, name)
        for name in type(direct).model_fields
        if name not in {"materialized_realization_id", "route_material_dispositions"}
    }
    with pytest.raises(ValidationError, match="PCR-only material dispositions"):
        MaterializedConstructionRealization.create(
            **disposition_content,
            route_material_dispositions=pcr_realization.route_material_dispositions,
        )
