"""
--------------------------------------------------------------------------------
HOP Design
tests/integration/test_adapter_annealing_completion.py

Checks complete adapter annealing against local requirements and source bases.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

import json
from pathlib import Path

import pytest

from hop_design.models.construction import (
    BasalPairAllowance,
    ConstructionEndpoint,
    SearchCompletionStatus,
)
from hop_design.models.construction.complete import (
    ConstrainedAdapterPolicy,
    DerivedEndpointPrimerPolicy,
    EndpointAuxiliaryPolicy,
    MaterialResolutionMode,
)
from hop_design.models.construction.complete.pcr.pairing import complete_adapter_pairing
from hop_design.models.construction.complete.pcr.validation import validate_adapter_pairing_state
from hop_design.models.junction import Strand
from hop_design.models.sequence import reverse_complement_iupac
from tests.integration.test_complete_construction_discovery import (
    _basal_result,
    _construction_request,
    _discover_raw,
    _verified_design,
)
from tests.integration.test_complete_construction_pcr import _foldback, _payload, _valid_pcr_result


def test_complete_route_rejects_an_undischarged_adapter_obligation(tmp_path: Path) -> None:
    result, _, _ = _valid_pcr_result(tmp_path)
    item = result.realizations[0]
    authority = item.construction_program.transitions[-3].pcr_authority
    state = item.construction_program.states[-3]
    basal = item.basal_authority
    obligation = type(basal.projection.annealing_obligation).create(
        pairing_state=basal.projection.pairing_state,
        minimum_annealing_nt=15,
        mismatch_warning_fraction=0.2,
    )
    basal = basal.model_copy(
        update={
            "projection": basal.projection.model_copy(update={"annealing_obligation": obligation})
        }
    )

    with pytest.raises(ValueError, match="annealing"):
        validate_adapter_pairing_state(
            authority,
            basal=basal,
            closed_strand_id=state.molecules[0].strand_id,
            adapter_strand_id=state.molecules[1].strand_id,
        )


def _adapter_case(tmp_path: Path, source_prefix: str):
    payload = _payload()
    foldback = _foldback(payload)
    basal = _basal_result(
        payload,
        ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
        nick_strand=Strand.BOTTOM,
        recognition_pattern=reverse_complement_iupac(source_prefix),
        cut_offset_reference_strand=0,
        minimum_adapter_annealing_nt=15,
    )
    design = _verified_design(tmp_path)
    request = _construction_request(
        payload=payload,
        foldback=foldback,
        basal=basal,
        design=design,
        endpoint=ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
        endpoint_auxiliaries=EndpointAuxiliaryPolicy(
            adapter=ConstrainedAdapterPolicy(
                mode=MaterialResolutionMode.CONSTRAIN,
                three_prime_handle_sequence="GATCTG",
            ),
            forward_primer=DerivedEndpointPrimerPolicy(
                mode=MaterialResolutionMode.DERIVE, annealing_length_nt=4
            ),
            reverse_primer=DerivedEndpointPrimerPolicy(
                mode=MaterialResolutionMode.DERIVE, annealing_length_nt=6
            ),
        ),
    )

    return request, foldback, basal, design


@pytest.mark.parametrize("source_prefix", ("TGCAGTCTGACAAAA", "ACGTGCAGTCTGACAAAA"))
def test_route_completes_adapter_pairing_before_appending_the_handle(
    tmp_path: Path, source_prefix: str
) -> None:
    request, foldback, basal, design = _adapter_case(tmp_path, source_prefix)
    result = _discover_raw(request, foldback=foldback, basal=basal, design=design)

    assert result.status is SearchCompletionStatus.COMPLETE
    assert result.realizations
    for item in result.realizations:
        assert item.materials[2].sequence_5prime == "TTTTGTCAGACTGCAGATCTG"
        authority = item.construction_program.transitions[-3].pcr_authority
        assert authority.hairpin_span.start.offset == len(source_prefix) - 15
        assert authority.hairpin_span.end.offset == len(source_prefix)
        assert authority.adapter_span.start.offset == 0
        assert authority.adapter_span.end.offset == 15
        assert len(authority.pairings) == 15
        assert [(pair.left_index, pair.right_index) for pair in authority.pairings] == [
            (len(source_prefix) - 1 - index, index) for index in range(15)
        ]


@pytest.mark.parametrize("adapter_sequence", ("TTTTGATCTG", "TTTTCTCAGACTGCAGATCTG"))
def test_fixed_adapter_must_supply_the_required_distal_pairs(
    tmp_path: Path, adapter_sequence: str
) -> None:
    request, foldback, basal, design = _adapter_case(tmp_path, "TGCAGTCTGACAAAA")
    data = request.model_dump(mode="json", by_alias=True)
    data["materialization"]["endpoint_auxiliaries"]["adapter"] = {
        "mode": "fixed",
        "material": {
            "sequence_5prime": adapter_sequence,
            "five_prime_end": "phosphate",
            "three_prime_end": "hydroxyl",
        },
    }
    fixed = type(request).model_validate_json(json.dumps(data))

    result = _discover_raw(fixed, foldback=foldback, basal=basal, design=design)

    assert result.status is SearchCompletionStatus.INFEASIBLE
    assert not result.realizations
    assert {reason.code for reason in result.failure_reasons} == {"pcr-adapter-mismatch"}


def test_distal_completion_preserves_the_selected_proximal_mismatch() -> None:
    basal = _basal_result(
        _payload(),
        nick_strand=Strand.BOTTOM,
        recognition_pattern="TTTTGTCAGACTGCA",
        cut_offset_reference_strand=0,
        minimum_adapter_annealing_nt=15,
        pairing_allowances=(
            BasalPairAllowance.MATCH,
            BasalPairAllowance.MISMATCH,
            BasalPairAllowance.MATCH,
            BasalPairAllowance.MATCH,
        ),
    )

    assert basal.realizations
    for item in basal.realizations:
        paired = complete_adapter_pairing(item)
        assert paired.adapter_sequence_5prime[:4] == item.proximal_adapter_sequence
        assert paired.adapter_sequence_5prime[4:] == "GTCAGACTGCA"
        assert paired.pairing_pattern == "MXMM" + "M" * 11
        assert paired.source_sequence_5prime == "TGCAGTCTGACAAAA"


def test_basal_result_cannot_lower_the_requested_annealing_requirement(tmp_path: Path) -> None:
    _, _, basal, _ = _adapter_case(tmp_path, "TGCAGTCTGACAAAA")
    changed = []
    for item in basal.realizations:
        obligation = type(item.projection.annealing_obligation).create(
            pairing_state=item.projection.pairing_state,
            minimum_annealing_nt=4,
            mismatch_warning_fraction=0.2,
        )
        content = {
            name: getattr(item, name)
            for name in type(item).model_fields
            if name != "basal_realization_id"
        }
        content["projection"] = item.projection.model_copy(
            update={"annealing_obligation": obligation}
        )
        changed.append(type(item).create(**content))

    with pytest.raises(ValueError, match="requested annealing"):
        type(basal).create(discovery=basal.discovery, realizations=tuple(changed))
