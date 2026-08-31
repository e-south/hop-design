"""
--------------------------------------------------------------------------------
HOP Design
tests/contract/test_source_preparation_resolution.py

Tests deterministic derive, constrain, and fixed source-preparation policies.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import pytest

from hop_design.models.construction.complete import (
    ConstrainedPrimerPolicy,
    DerivedPrimerPolicy,
    DerivedSourceSsdnaPolicy,
    ExactConstructionMaterial,
    FixedPrimerPolicy,
    FixedSourceSsdnaPolicy,
    MaterialOrigin,
    MaterialResolutionMode,
    PcrPrimer,
    SourceDuplexPreparationPolicy,
    resolve_source_duplex_preparation,
)
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.molecular_state import EndChemistry


def _span(start: int, end: int) -> Span:
    return Span(start=Boundary(offset=start), end=Boundary(offset=end))


def _material(
    material_id: str,
    sequence: str,
    *,
    five_prime_end: EndChemistry = EndChemistry.HYDROXYL,
) -> ExactConstructionMaterial:
    return ExactConstructionMaterial(
        material_id=material_id,
        origin=MaterialOrigin.SYNTHESIZED,
        sequence_5prime=sequence,
        five_prime_end=five_prime_end,
        three_prime_end=EndChemistry.HYDROXYL,
    )


def test_derived_source_preparation_materializes_exact_orderable_inputs() -> None:
    policy = SourceDuplexPreparationPolicy(
        source_ssdna=DerivedSourceSsdnaPolicy(
            mode=MaterialResolutionMode.DERIVE,
            five_prime_end=EndChemistry.HYDROXYL,
            three_prime_end=EndChemistry.HYDROXYL,
        ),
        forward_primer=DerivedPrimerPolicy(
            mode=MaterialResolutionMode.DERIVE,
            annealing_length_nt=4,
        ),
        reverse_primer=DerivedPrimerPolicy(
            mode=MaterialResolutionMode.DERIVE,
            annealing_length_nt=4,
        ),
    )

    authority = resolve_source_duplex_preparation(
        policy=policy,
        source_sequence="ACGTGGAATTCC",
        payload_source_span=_span(4, 8),
        reference_five_prime_end=EndChemistry.HYDROXYL,
        complement_five_prime_end=EndChemistry.PHOSPHATE,
    )

    assert authority.source_ssdna.sequence_5prime == "ACGTGGAATTCC"
    assert authority.forward_primer.oligo.sequence_5prime == "ACGT"
    assert authority.reverse_primer.oligo.sequence_5prime == "GGAA"
    assert authority.forward_primer.oligo.five_prime_end is EndChemistry.HYDROXYL
    assert authority.reverse_primer.oligo.five_prime_end is EndChemistry.PHOSPHATE
    assert authority.forward_primer.annealing_length_nt == 4
    assert authority.reverse_primer.annealing_length_nt == 4
    assert authority == resolve_source_duplex_preparation(
        policy=policy,
        source_sequence="ACGTGGAATTCC",
        payload_source_span=_span(4, 8),
        reference_five_prime_end=EndChemistry.HYDROXYL,
        complement_five_prime_end=EndChemistry.PHOSPHATE,
    )


def test_constrained_source_primers_choose_the_shortest_valid_lengths() -> None:
    policy = SourceDuplexPreparationPolicy(
        source_ssdna=DerivedSourceSsdnaPolicy(
            mode=MaterialResolutionMode.DERIVE,
            five_prime_end=EndChemistry.HYDROXYL,
            three_prime_end=EndChemistry.HYDROXYL,
        ),
        forward_primer=ConstrainedPrimerPolicy(
            mode=MaterialResolutionMode.CONSTRAIN,
            min_annealing_length_nt=3,
            max_annealing_length_nt=5,
        ),
        reverse_primer=ConstrainedPrimerPolicy(
            mode=MaterialResolutionMode.CONSTRAIN,
            min_annealing_length_nt=2,
            max_annealing_length_nt=4,
        ),
    )

    authority = resolve_source_duplex_preparation(
        policy=policy,
        source_sequence="ACGTGGAATTCC",
        payload_source_span=_span(5, 8),
        reference_five_prime_end=EndChemistry.PHOSPHATE,
        complement_five_prime_end=EndChemistry.HYDROXYL,
    )

    assert authority.forward_primer.annealing_length_nt == 3
    assert authority.reverse_primer.annealing_length_nt == 2
    assert authority.forward_primer.oligo.sequence_5prime == "ACG"
    assert authority.reverse_primer.oligo.sequence_5prime == "GG"


def test_fixed_source_preparation_replays_caller_materials() -> None:
    source = _material("fixed-source", "ACGTGGAATTCC")
    forward = PcrPrimer(
        oligo=_material("fixed-forward", "ACGT"),
        annealing_length_nt=4,
    )
    reverse = PcrPrimer(
        oligo=_material(
            "fixed-reverse",
            "GGAA",
            five_prime_end=EndChemistry.PHOSPHATE,
        ),
        annealing_length_nt=4,
    )
    policy = SourceDuplexPreparationPolicy(
        source_ssdna=FixedSourceSsdnaPolicy(
            mode=MaterialResolutionMode.FIXED,
            material=source,
        ),
        forward_primer=FixedPrimerPolicy(
            mode=MaterialResolutionMode.FIXED,
            primer=forward,
        ),
        reverse_primer=FixedPrimerPolicy(
            mode=MaterialResolutionMode.FIXED,
            primer=reverse,
        ),
    )

    authority = resolve_source_duplex_preparation(
        policy=policy,
        source_sequence=source.sequence_5prime,
        payload_source_span=_span(4, 8),
        reference_five_prime_end=EndChemistry.HYDROXYL,
        complement_five_prime_end=EndChemistry.PHOSPHATE,
    )

    assert authority.source_ssdna == source
    assert authority.forward_primer == forward
    assert authority.reverse_primer == reverse


@pytest.mark.parametrize(
    ("mutation", "message"),
    (
        ("source_sequence", "fixed source ssDNA"),
        ("primer_chemistry", "required five-prime chemistry"),
        ("constrained_length", "outside the payload"),
    ),
)
def test_source_preparation_resolution_fails_closed(
    mutation: str,
    message: str,
) -> None:
    if mutation == "source_sequence":
        policy = SourceDuplexPreparationPolicy(
            source_ssdna=FixedSourceSsdnaPolicy(
                mode=MaterialResolutionMode.FIXED,
                material=_material("fixed-source", "ACGTGGAATTCA"),
            ),
            forward_primer=DerivedPrimerPolicy(
                mode=MaterialResolutionMode.DERIVE,
                annealing_length_nt=4,
            ),
            reverse_primer=DerivedPrimerPolicy(
                mode=MaterialResolutionMode.DERIVE,
                annealing_length_nt=4,
            ),
        )
    elif mutation == "primer_chemistry":
        policy = SourceDuplexPreparationPolicy(
            source_ssdna=DerivedSourceSsdnaPolicy(
                mode=MaterialResolutionMode.DERIVE,
                five_prime_end=EndChemistry.HYDROXYL,
                three_prime_end=EndChemistry.HYDROXYL,
            ),
            forward_primer=FixedPrimerPolicy(
                mode=MaterialResolutionMode.FIXED,
                primer=PcrPrimer(
                    oligo=_material(
                        "fixed-forward",
                        "ACGT",
                        five_prime_end=EndChemistry.PHOSPHATE,
                    ),
                    annealing_length_nt=4,
                ),
            ),
            reverse_primer=DerivedPrimerPolicy(
                mode=MaterialResolutionMode.DERIVE,
                annealing_length_nt=4,
            ),
        )
    elif mutation == "constrained_length":
        policy = SourceDuplexPreparationPolicy(
            source_ssdna=DerivedSourceSsdnaPolicy(
                mode=MaterialResolutionMode.DERIVE,
                five_prime_end=EndChemistry.HYDROXYL,
                three_prime_end=EndChemistry.HYDROXYL,
            ),
            forward_primer=ConstrainedPrimerPolicy(
                mode=MaterialResolutionMode.CONSTRAIN,
                min_annealing_length_nt=5,
                max_annealing_length_nt=6,
            ),
            reverse_primer=DerivedPrimerPolicy(
                mode=MaterialResolutionMode.DERIVE,
                annealing_length_nt=4,
            ),
        )
    else:  # pragma: no cover - parameter table is closed above
        raise AssertionError(mutation)

    with pytest.raises(ValueError, match=message):
        resolve_source_duplex_preparation(
            policy=policy,
            source_sequence="ACGTGGAATTCC",
            payload_source_span=_span(4, 8),
            reference_five_prime_end=EndChemistry.HYDROXYL,
            complement_five_prime_end=EndChemistry.PHOSPHATE,
        )
