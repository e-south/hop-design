"""
--------------------------------------------------------------------------------
HOP Design
tests/contract/test_source_duplex_preparation.py

Tests exact source-ssDNA primer copying into a replayable source duplex.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from hop_design.models.construction.complete import (
    ExactConstructionMaterial,
    MaterialOrigin,
    PcrPrimer,
    SourceDuplexPreparationAuthority,
    derive_source_duplex_preparation,
)
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.method import BindingOrientation
from hop_design.models.molecular_state import EndChemistry
from hop_design.models.sequence import reverse_complement_iupac


def _material(
    material_id: str,
    sequence: str,
    *,
    five_prime_end: EndChemistry = EndChemistry.HYDROXYL,
    three_prime_end: EndChemistry = EndChemistry.HYDROXYL,
) -> ExactConstructionMaterial:
    return ExactConstructionMaterial(
        material_id=material_id,
        origin=MaterialOrigin.SYNTHESIZED,
        sequence_5prime=sequence,
        five_prime_end=five_prime_end,
        three_prime_end=three_prime_end,
    )


def _inputs() -> tuple[ExactConstructionMaterial, PcrPrimer, PcrPrimer]:
    source = _material("source-ssdna", "ACGTGGAATTCC")
    forward = PcrPrimer(
        oligo=_material("source-forward-primer", "ACGT"),
        annealing_length_nt=4,
    )
    reverse = PcrPrimer(
        oligo=_material(
            "source-reverse-primer",
            "GGAA",
            five_prime_end=EndChemistry.PHOSPHATE,
        ),
        annealing_length_nt=4,
    )
    return source, forward, reverse


def _payload_span(start: int = 4, end: int = 8) -> Span:
    return Span(start=Boundary(offset=start), end=Boundary(offset=end))


def _authority() -> SourceDuplexPreparationAuthority:
    source, forward, reverse = _inputs()
    return derive_source_duplex_preparation(
        source_ssdna=source,
        forward_primer=forward,
        reverse_primer=reverse,
        payload_source_span=_payload_span(),
    )


def test_source_duplex_preparation_replays_products_bindings_and_lineage() -> None:
    authority = _authority()
    source, forward, reverse = _inputs()
    top, bottom = authority.product_state.molecules

    assert authority.authority_id.startswith("hop:source-duplex-preparation/")
    assert authority == _authority()
    assert authority.source_ssdna == source
    assert authority.forward_primer == forward
    assert authority.reverse_primer == reverse
    assert top.sequence == source.sequence_5prime
    assert bottom.sequence == reverse_complement_iupac(source.sequence_5prime)
    assert tuple(strand.strand_id for strand in authority.product_state.molecules) == (
        "source-duplex-top",
        "source-duplex-bottom",
    )
    assert top.five_prime_end is EndChemistry.HYDROXYL
    assert bottom.five_prime_end is EndChemistry.PHOSPHATE
    assert top.three_prime_end is EndChemistry.HYDROXYL
    assert bottom.three_prime_end is EndChemistry.HYDROXYL
    assert tuple(
        (
            binding.product_strand_id,
            binding.material.sequence_5prime,
            binding.material.five_prime_end,
            binding.material.three_prime_end,
            binding.material.origin,
        )
        for binding in authority.produced_material_bindings
    ) == (
        (
            top.strand_id,
            top.sequence,
            top.five_prime_end,
            top.three_prime_end,
            MaterialOrigin.PCR_DERIVED,
        ),
        (
            bottom.strand_id,
            bottom.sequence,
            bottom.five_prime_end,
            bottom.three_prime_end,
            MaterialOrigin.PCR_DERIVED,
        ),
    )
    assert tuple(
        binding.product_state_id for binding in authority.produced_material_bindings
    ) == (authority.product_state.state_id, authority.product_state.state_id)
    assert tuple(item.origin_id for item in top.lineage) == (
        ("source-forward-primer",) * 4
        + ("source-ssdna",) * 4
        + ("source-reverse-primer",) * 4
    )
    assert tuple(item.origin_id for item in bottom.lineage) == tuple(
        reversed(tuple(item.origin_id for item in top.lineage))
    )
    assert len(authority.product_state.pairings) == len(source.sequence_5prime)
    assert tuple(binding.primer_id for binding in authority.bindings) == (
        forward.oligo.material_id,
        reverse.oligo.material_id,
    )
    assert tuple(binding.template_strand_id for binding in authority.bindings) == (
        bottom.strand_id,
        top.strand_id,
    )
    assert tuple(binding.orientation for binding in authority.bindings) == (
        BindingOrientation.REVERSE_COMPLEMENT_5TO3,
        BindingOrientation.REVERSE_COMPLEMENT_5TO3,
    )
    assert (
        authority.bindings[0].template_span.start.offset,
        authority.bindings[0].template_span.end.offset,
    ) == (8, 12)
    assert (
        authority.bindings[1].template_span.start.offset,
        authority.bindings[1].template_span.end.offset,
    ) == (8, 12)


@pytest.mark.parametrize(
    ("mutation", "message"),
    (
        ("forward_mismatch", "forward primer"),
        ("reverse_mismatch", "reverse primer"),
        ("primer_phosphate", "three-prime hydroxyl"),
        ("overlap", "must not overlap"),
        ("duplicate_id", "distinct material ids"),
        ("five_prime_handle", "five-prime handles"),
        ("payload_overlap", "outside the payload"),
    ),
)
def test_source_duplex_preparation_rejects_invalid_inputs(
    mutation: str,
    message: str,
) -> None:
    source, forward, reverse = _inputs()
    if mutation == "forward_mismatch":
        forward = forward.model_copy(
            update={"oligo": forward.oligo.model_copy(update={"sequence_5prime": "TCGT"})}
        )
    elif mutation == "reverse_mismatch":
        reverse = reverse.model_copy(
            update={"oligo": reverse.oligo.model_copy(update={"sequence_5prime": "TGAA"})}
        )
    elif mutation == "primer_phosphate":
        forward = forward.model_copy(
            update={
                "oligo": forward.oligo.model_copy(
                    update={"three_prime_end": EndChemistry.PHOSPHATE}
                )
            }
        )
    elif mutation == "overlap":
        forward = PcrPrimer(
            oligo=_material("source-forward-primer", source.sequence_5prime[:7]),
            annealing_length_nt=7,
        )
        reverse = PcrPrimer(
            oligo=_material(
                "source-reverse-primer",
                reverse_complement_iupac(source.sequence_5prime[-6:]),
            ),
            annealing_length_nt=6,
        )
    elif mutation == "duplicate_id":
        reverse = reverse.model_copy(
            update={"oligo": reverse.oligo.model_copy(update={"material_id": "source-ssdna"})}
        )
    elif mutation == "five_prime_handle":
        forward = PcrPrimer(
            oligo=_material("source-forward-primer", "GGACGT"),
            annealing_length_nt=4,
        )
    elif mutation == "payload_overlap":
        source = _material("source-ssdna", "ACGTGGAATTCC")
    else:  # pragma: no cover - parameter table is closed above
        raise AssertionError(mutation)

    with pytest.raises(ValueError, match=message):
        derive_source_duplex_preparation(
            source_ssdna=source,
            forward_primer=forward,
            reverse_primer=reverse,
            payload_source_span=(
                _payload_span(0, 5) if mutation == "payload_overlap" else _payload_span()
            ),
        )


@pytest.mark.parametrize(
    "mutation",
    (
        "authority_id",
        "binding",
        "product_sequence",
        "product_lineage",
        "pairings",
        "produced_material",
        "produced_state",
    ),
)
def test_source_duplex_preparation_rejects_forged_authority(mutation: str) -> None:
    authority = _authority()
    data = authority.model_dump(mode="python")
    if mutation == "authority_id":
        data["authority_id"] = f"hop:source-duplex-preparation/{'0' * 64}@1"
    elif mutation == "binding":
        data["bindings"][0]["orientation"] = BindingOrientation.SAME_5TO3
    elif mutation == "product_sequence":
        data["product_state"]["molecules"][0]["sequence"] = "TCGTGGAATTCC"
    elif mutation == "product_lineage":
        data["product_state"]["molecules"][0]["lineage"][0]["origin_id"] = "forged"
    elif mutation == "pairings":
        data["product_state"]["pairings"] = data["product_state"]["pairings"][:-1]
    elif mutation == "produced_material":
        data["produced_material_bindings"][0]["material"]["sequence_5prime"] = (
            "TCGTGGAATTCC"
        )
    elif mutation == "produced_state":
        data["produced_material_bindings"][0]["product_state_id"] = (
            f"hop:construction-state/{'0' * 64}@1"
        )
    else:  # pragma: no cover - parameter table is closed above
        raise AssertionError(mutation)

    with pytest.raises(ValidationError):
        SourceDuplexPreparationAuthority.model_validate(data)


def test_source_duplex_preparation_identity_changes_with_molecular_inputs() -> None:
    source, forward, reverse = _inputs()
    baseline = derive_source_duplex_preparation(
        source_ssdna=source,
        forward_primer=forward,
        reverse_primer=reverse,
        payload_source_span=_payload_span(),
    )
    changed_source = source.model_copy(update={"five_prime_end": EndChemistry.PHOSPHATE})

    changed = derive_source_duplex_preparation(
        source_ssdna=changed_source,
        forward_primer=forward,
        reverse_primer=reverse,
        payload_source_span=_payload_span(),
    )

    assert changed.authority_id != baseline.authority_id
