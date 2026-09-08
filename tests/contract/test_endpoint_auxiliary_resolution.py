"""
--------------------------------------------------------------------------------
HOP Design
tests/contract/test_endpoint_auxiliary_resolution.py

Tests endpoint auxiliary policies against exact basal and PCR-template facts.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import json

import pytest

from hop_design.models.construction import ConstructionEndpoint
from hop_design.models.construction.complete import (
    ConstrainedAdapterPolicy,
    ConstrainedEndpointPrimerPolicy,
    DerivedAdapterPolicy,
    DerivedEndpointPrimerPolicy,
    EndpointAuxiliaryPolicy,
    ExactConstructionMaterial,
    FixedAdapterPolicy,
    MaterialResolutionMode,
)
from hop_design.models.construction.complete.auxiliary import (
    EndpointAuxiliaryResolutionError,
    EndpointAuxiliaryResolutionFailure,
    resolve_endpoint_auxiliaries,
)
from hop_design.models.construction.complete.auxiliary.pairing import (
    resolve_adapter_pairing_sequence,
)
from hop_design.models.construction.targets import BasalPairConstraint
from hop_design.models.junction import Strand
from hop_design.models.molecular_state import EndChemistry
from hop_design.models.sequence import reverse_complement_iupac
from tests.integration.test_complete_construction_discovery import _basal_result
from tests.integration.test_complete_construction_pcr import _payload


def test_constrained_adapter_and_derived_primers_resolve_exact_materials() -> None:
    basal = _basal_result(
        _payload(),
        ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
        nick_strand=Strand.BOTTOM,
    ).realizations[0]
    proximal_adapter = basal.proximal_adapter_sequence
    pcr_core = "CAAAAGACATCAGATGCTGATGTC"
    handle = "GATCTG"
    policy = EndpointAuxiliaryPolicy(
        adapter=ConstrainedAdapterPolicy(
            mode=MaterialResolutionMode.CONSTRAIN,
            three_prime_handle_sequence=handle,
        ),
        forward_primer=DerivedEndpointPrimerPolicy(
            mode=MaterialResolutionMode.DERIVE,
            annealing_length_nt=5,
        ),
        reverse_primer=DerivedEndpointPrimerPolicy(
            mode=MaterialResolutionMode.DERIVE,
            annealing_length_nt=6,
        ),
    )

    resolved = resolve_endpoint_auxiliaries(
        policy=policy,
        basal=basal,
        pcr_core_sequence=pcr_core,
        source_primer_region_length_nt=5,
    )

    template = pcr_core + proximal_adapter + handle
    assert resolved.adapter.sequence_5prime == proximal_adapter + handle
    assert resolved.adapter.five_prime_end is EndChemistry.PHOSPHATE
    assert resolved.adapter.three_prime_end is EndChemistry.HYDROXYL
    assert resolved.forward_primer.annealing_sequence == template[:5]
    assert resolved.reverse_primer.annealing_sequence == reverse_complement_iupac(template[-6:])
    assert resolved.resolution_modes == (
        MaterialResolutionMode.CONSTRAIN,
        MaterialResolutionMode.DERIVE,
        MaterialResolutionMode.DERIVE,
    )


def test_endpoint_primer_annealing_cannot_cross_the_source_construction_region() -> None:
    basal = _basal_result(
        _payload(),
        ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
        nick_strand=Strand.BOTTOM,
    ).realizations[0]
    policy = EndpointAuxiliaryPolicy(
        adapter=ConstrainedAdapterPolicy(
            mode=MaterialResolutionMode.CONSTRAIN,
            three_prime_handle_sequence="GATCTG",
        ),
        forward_primer=DerivedEndpointPrimerPolicy(
            mode=MaterialResolutionMode.DERIVE,
            annealing_length_nt=5,
        ),
        reverse_primer=DerivedEndpointPrimerPolicy(
            mode=MaterialResolutionMode.DERIVE,
            annealing_length_nt=4,
        ),
    )

    with pytest.raises(EndpointAuxiliaryResolutionError) as error:
        resolve_endpoint_auxiliaries(
            policy=policy,
            basal=basal,
            pcr_core_sequence="AAAAGACATCAGATGCTGATGTC",
            source_primer_region_length_nt=4,
        )

    assert error.value.failure is EndpointAuxiliaryResolutionFailure.PRIMER
    assert str(error.value) == (
        "Endpoint primer annealing must remain within invariant construction sequence."
    )


def test_constrained_endpoint_primers_choose_the_shortest_valid_terminal_binding() -> None:
    basal = _basal_result(
        _payload(),
        ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
        nick_strand=Strand.BOTTOM,
    ).realizations[0]
    pcr_core = "CCAAAAGACATCAGATGCTGATGTC"
    policy = EndpointAuxiliaryPolicy(
        adapter=ConstrainedAdapterPolicy(
            mode=MaterialResolutionMode.CONSTRAIN,
            three_prime_handle_sequence="GATCTG",
        ),
        forward_primer=ConstrainedEndpointPrimerPolicy(
            mode=MaterialResolutionMode.CONSTRAIN,
            min_annealing_length_nt=3,
            max_annealing_length_nt=6,
            five_prime_handle_sequence="AT",
        ),
        reverse_primer=ConstrainedEndpointPrimerPolicy(
            mode=MaterialResolutionMode.CONSTRAIN,
            min_annealing_length_nt=4,
            max_annealing_length_nt=7,
            five_prime_handle_sequence="GC",
        ),
    )

    resolved = resolve_endpoint_auxiliaries(
        policy=policy,
        basal=basal,
        pcr_core_sequence=pcr_core,
        source_primer_region_length_nt=6,
    )

    template = pcr_core + resolved.adapter.sequence_5prime
    assert resolved.forward_primer.annealing_length_nt == 3
    assert resolved.forward_primer.oligo.sequence_5prime == f"AT{template[:3]}"
    assert resolved.reverse_primer.annealing_length_nt == 4
    assert resolved.reverse_primer.oligo.sequence_5prime == (
        f"GC{reverse_complement_iupac(template[-4:])}"
    )


def test_fixed_adapter_rejects_incompatible_three_prime_chemistry() -> None:
    basal = _basal_result(
        _payload(),
        ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
        nick_strand=Strand.BOTTOM,
    ).realizations[0]
    proximal_adapter = basal.proximal_adapter_sequence
    policy = EndpointAuxiliaryPolicy(
        adapter=FixedAdapterPolicy(
            mode=MaterialResolutionMode.FIXED,
            material=ExactConstructionMaterial.model_validate(
                {
                    "sequence_5prime": proximal_adapter,
                    "five_prime_end": EndChemistry.PHOSPHATE,
                    "three_prime_end": EndChemistry.PHOSPHATE,
                }
            ),
        ),
        forward_primer=DerivedEndpointPrimerPolicy(
            mode=MaterialResolutionMode.DERIVE,
            annealing_length_nt=4,
        ),
        reverse_primer=DerivedEndpointPrimerPolicy(
            mode=MaterialResolutionMode.DERIVE,
            annealing_length_nt=4,
        ),
    )

    with pytest.raises(EndpointAuxiliaryResolutionError) as error:
        resolve_endpoint_auxiliaries(
            policy=policy,
            basal=basal,
            pcr_core_sequence="AAAAGACATCAGATGCTGATGTC",
            source_primer_region_length_nt=4,
        )

    assert error.value.failure is EndpointAuxiliaryResolutionFailure.ADAPTER
    assert (
        str(error.value) == "Adapter must preserve complete basal annealing and ligation chemistry."
    )


def test_adapter_resolution_rejects_a_source_that_disagrees_with_its_basal_bases() -> None:
    basal = _basal_result(_payload(), nick_strand=Strand.BOTTOM).realizations[0]
    policy = EndpointAuxiliaryPolicy(
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
    )

    with pytest.raises(EndpointAuxiliaryResolutionError, match="exact basal neighborhood") as error:
        resolve_endpoint_auxiliaries(
            policy=policy,
            basal=basal,
            pcr_core_sequence="AACCGGTTAACCGGTT",
            source_primer_region_length_nt=4,
        )

    assert error.value.failure is EndpointAuxiliaryResolutionFailure.ADAPTER


def test_default_adapter_policy_keeps_its_canonical_bytes() -> None:
    policy = DerivedAdapterPolicy(mode=MaterialResolutionMode.DERIVE)
    assert policy.model_dump_json() == '{"mode":"derive"}'


@pytest.mark.parametrize("positions", ((6, 6), (7, 6)))
def test_distal_constraints_require_unique_ascending_positions(positions: tuple[int, int]) -> None:
    with pytest.raises(ValueError, match="distinct ascending"):
        DerivedAdapterPolicy.model_validate_json(
            '{"mode":"derive","distal_pairing_constraints":['
            + ",".join(
                f'{{"position_from_ligation":{position},"allowed_class":"match"}}'
                for position in positions
            )
            + "]}"
        )


@pytest.mark.parametrize(
    ("constraint", "fixed_sequence", "expected"),
    (
        ({"allowed_class": "mismatch", "allowed_adapter_bases": ["A"]}, None, "TTTTGTAAGACTGCA"),
        ({"allowed_class": "any"}, "TTTTGTTAGACTGCA", "TTTTGTTAGACTGCA"),
        ({"allowed_class": "wobble", "allowed_source_bases": ["A"]}, None, None),
        ({"allowed_class": "wobble"}, "TTTTGTCAGACTGCA", None),
    ),
)
def test_distal_resolution_honors_literal_base_and_pair_constraints(
    constraint: dict, fixed_sequence: str | None, expected: str | None
) -> None:
    basal = _basal_result(
        _payload(),
        nick_strand=Strand.BOTTOM,
        recognition_pattern="TTTTGTCAGACTGCA",
        cut_offset_reference_strand=0,
        minimum_adapter_annealing_nt=15,
    ).realizations[0]
    pair = BasalPairConstraint.model_validate_json(
        json.dumps({"position_from_ligation": 6, **constraint})
    )
    if expected is None:
        with pytest.raises(ValueError, match="distal pairing constraint"):
            resolve_adapter_pairing_sequence(
                basal,
                source_prefix="TGCAGTCTGACAAAA",
                constraints=(pair,),
                fixed_sequence=fixed_sequence,
            )
    else:
        assert (
            resolve_adapter_pairing_sequence(
                basal,
                source_prefix="TGCAGTCTGACAAAA",
                constraints=(pair,),
                fixed_sequence=fixed_sequence,
            )
            == expected
        )
