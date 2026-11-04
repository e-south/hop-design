"""Preparation failures preserve binding, chemistry, and length distinctions."""

import json

import pytest

from hop_design.models.construction.complete import (
    SourceDuplexPreparationPolicy,
    SourcePreparationResolutionError,
    resolve_source_duplex_preparation,
)
from hop_design.models.molecular_state import EndChemistry
from tests.contract.test_source_preparation_resolution import _span


@pytest.mark.parametrize(
    ("mutation", "code", "field", "requested", "available"),
    [
        (
            "primer-sequence",
            "fixed-primer-binding-mismatch",
            "forward_primer.primer.oligo.sequence_5prime",
            "AAAA",
            "ACGT",
        ),
        (
            "primer-chemistry",
            "fixed-primer-end-chemistry-mismatch",
            "forward_primer.primer.oligo.five_prime_end",
            "phosphate",
            "hydroxyl",
        ),
        (
            "source-sequence",
            "fixed-source-sequence-mismatch",
            "source_ssdna.material.sequence_5prime",
            "ACGTGGAATTCA",
            "ACGTGGAATTCC",
        ),
        (
            "constrained-length",
            "primer-annealing-span-exceeded",
            "forward_primer.min_annealing_length_nt",
            5,
            4,
        ),
    ],
)
def test_resolution_diagnostic_distinguishes_authored_constraint(
    mutation, code, field, requested, available
):
    material = {
        "sequence_5prime": "ACGT",
        "five_prime_end": "hydroxyl",
        "three_prime_end": "hydroxyl",
    }
    source = {"mode": "derive", "five_prime_end": "hydroxyl", "three_prime_end": "hydroxyl"}
    forward = {"mode": "fixed", "primer": {"oligo": material, "annealing_length_nt": 4}}
    if mutation == "primer-sequence":
        material["sequence_5prime"] = requested
    elif mutation == "primer-chemistry":
        material["five_prime_end"] = requested
    elif mutation == "source-sequence":
        source = {"mode": "fixed", "material": {**material, "sequence_5prime": requested}}
    else:
        forward = {"mode": "constrain", "min_annealing_length_nt": 5, "max_annealing_length_nt": 6}
    policy = SourceDuplexPreparationPolicy.model_validate_json(
        json.dumps(
            {
                "source_ssdna": source,
                "forward_primer": forward,
                "reverse_primer": {"mode": "derive", "annealing_length_nt": 4},
            }
        )
    )
    with pytest.raises(SourcePreparationResolutionError) as error:
        resolve_source_duplex_preparation(
            policy=policy,
            source_sequence="ACGTGGAATTCC",
            payload_source_span=_span(4, 8),
            reference_five_prime_end=EndChemistry.HYDROXYL,
            complement_five_prime_end=EndChemistry.PHOSPHATE,
        )
    diagnostic = error.value.diagnostic
    assert diagnostic.code == code
    assert diagnostic.stage == "source-duplex-preparation"
    assert diagnostic.field == f"materialization.source_preparation.{field}"
    assert diagnostic.requested == requested
    assert diagnostic.available == available


def test_diagnostic_is_strict_frozen_and_rejects_false_length_claims():
    from hop_design.models.construction.complete.preparation_diagnostics import (
        PreparationConstraintDiagnostic,
    )

    content = {
        "code": "primer-annealing-span-exceeded",
        "field": "materialization.source_preparation.forward_primer.annealing_length_nt",
        "requirement": "at-most",
        "requested": 20,
        "available": 10,
        "message": "Binding exceeds the available span.",
    }
    diagnostic = PreparationConstraintDiagnostic.model_validate(content)
    with pytest.raises(ValueError, match="frozen"):
        diagnostic.available = 9
    for bad in (
        {"requested": "20"},
        {"requirement": "equals"},
        {"available": 20},
        {"available": -1},
        {"code": "invented"},
        {"stage": "endpoint-auxiliary-preparation"},
        {"field": "materialization.endpoint_auxiliaries.forward_primer.annealing_length_nt"},
        {"repair": "shorten primer"},
    ):
        with pytest.raises(ValueError):
            PreparationConstraintDiagnostic.model_validate({**content, **bad})
