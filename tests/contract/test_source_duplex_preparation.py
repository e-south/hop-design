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
    ConstructionStatePhase,
    ExactConstructionMaterial,
    MaterialResolutionMode,
    MaterialRouteEntry,
    MaterialUse,
    MaterialUseRole,
    PcrPrimer,
    SourceDuplexPreparationAuthority,
    derive_source_duplex_preparation,
)
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.method import BindingOrientation
from hop_design.models.molecular_state import EndChemistry
from hop_design.models.sequence import reverse_complement_iupac


def _material(
    _role: str,
    sequence: str,
    *,
    five_prime_end: EndChemistry = EndChemistry.HYDROXYL,
    three_prime_end: EndChemistry = EndChemistry.HYDROXYL,
) -> ExactConstructionMaterial:
    return ExactConstructionMaterial(
        sequence_5prime=sequence,
        five_prime_end=five_prime_end,
        three_prime_end=three_prime_end,
    )


def _changed_material(
    material: ExactConstructionMaterial,
    **changes: object,
) -> ExactConstructionMaterial:
    content = material.model_dump(mode="python", exclude={"material_id"})
    content.update(changes)
    return ExactConstructionMaterial.model_validate(content)


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
    assert authority.source_ssdna_use.material_id == source.material_id
    assert authority.source_ssdna_use.role is MaterialUseRole.SOURCE_SSDNA
    assert authority.source_ssdna_use.route_entry is MaterialRouteEntry.REQUIRED_EXTERNAL
    assert authority.forward_primer_use.material_id == forward.oligo.material_id
    assert authority.reverse_primer_use.material_id == reverse.oligo.material_id
    assert (
        authority.prepared_top_use.material_id
        == authority.produced_material_bindings[0].material.material_id
    )
    assert (
        authority.prepared_bottom_use.material_id
        == authority.produced_material_bindings[1].material.material_id
    )
    assert authority.prepared_top_use.route_entry is MaterialRouteEntry.MODELED_PRODUCT
    assert authority.prepared_bottom_use.route_entry is MaterialRouteEntry.MODELED_PRODUCT
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
        )
        for binding in authority.produced_material_bindings
    ) == (
        (
            top.strand_id,
            top.sequence,
            top.five_prime_end,
            top.three_prime_end,
        ),
        (
            bottom.strand_id,
            bottom.sequence,
            bottom.five_prime_end,
            bottom.three_prime_end,
        ),
    )
    assert tuple(binding.product_state_id for binding in authority.produced_material_bindings) == (
        authority.product_state.state_id,
        authority.product_state.state_id,
    )
    assert tuple(item.origin_id for item in top.lineage) == (
        authority.prepared_top_use.use_id,
    ) * len(top.sequence)
    assert tuple(item.origin_id for item in bottom.lineage) == (
        authority.prepared_bottom_use.use_id,
    ) * len(bottom.sequence)
    assert tuple(
        item.origin_id for item in authority.produced_material_bindings[0].upstream_lineage
    ) == (
        (authority.forward_primer_use.use_id,) * 4
        + (authority.source_ssdna_use.use_id,) * 4
        + (authority.reverse_primer_use.use_id,) * 4
    )
    assert len(authority.product_state.pairings) == len(source.sequence_5prime)
    assert authority.input_state.phase is ConstructionStatePhase.SOURCE_SSDNA
    assert authority.input_state.molecules == (authority.source_template,)
    assert authority.pre_state_id == authority.input_state.state_id
    assert authority.post_state_id == authority.product_state.state_id
    assert tuple(binding.primer_id for binding in authority.bindings) == (
        authority.reverse_primer_use.use_id,
        authority.forward_primer_use.use_id,
    )
    assert tuple(binding.template_strand_id for binding in authority.bindings) == (
        authority.source_template.strand_id,
        bottom.strand_id,
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


def test_material_identity_uses_molecular_content_not_contextual_role() -> None:
    first = ExactConstructionMaterial(
        sequence_5prime="ACGT",
        five_prime_end=EndChemistry.HYDROXYL,
        three_prime_end=EndChemistry.HYDROXYL,
    )
    same_content = ExactConstructionMaterial(
        sequence_5prime="ACGT",
        five_prime_end=EndChemistry.HYDROXYL,
        three_prime_end=EndChemistry.HYDROXYL,
    )
    different_chemistry = ExactConstructionMaterial(
        sequence_5prime="ACGT",
        five_prime_end=EndChemistry.PHOSPHATE,
        three_prime_end=EndChemistry.HYDROXYL,
    )

    assert first.material_id == same_content.material_id
    assert first.material_id != different_chemistry.material_id
    assert first.material_id.startswith("hop:construction-material/")


def test_material_use_separates_contextual_role_from_molecular_identity() -> None:
    material = _material("shared-primer", "ACGT")

    forward = MaterialUse.create(
        material_id=material.material_id,
        role=MaterialUseRole.ENDPOINT_FORWARD_PRIMER,
        specification_resolution_mode=MaterialResolutionMode.FIXED,
        route_entry=MaterialRouteEntry.REQUIRED_EXTERNAL,
    )
    reverse = MaterialUse.create(
        material_id=material.material_id,
        role=MaterialUseRole.ENDPOINT_REVERSE_PRIMER,
        specification_resolution_mode=MaterialResolutionMode.FIXED,
        route_entry=MaterialRouteEntry.REQUIRED_EXTERNAL,
    )

    assert forward.material_id == reverse.material_id
    assert forward.use_id != reverse.use_id
    assert forward == MaterialUse.create(
        material_id=material.material_id,
        role=MaterialUseRole.ENDPOINT_FORWARD_PRIMER,
        specification_resolution_mode=MaterialResolutionMode.FIXED,
        route_entry=MaterialRouteEntry.REQUIRED_EXTERNAL,
    )


def test_material_identity_rejects_a_caller_label_as_molecular_identity() -> None:
    with pytest.raises(ValidationError, match="content identity"):
        ExactConstructionMaterial(
            material_id="forward-primer",
            sequence_5prime="ACGT",
            five_prime_end=EndChemistry.HYDROXYL,
            three_prime_end=EndChemistry.HYDROXYL,
        )


def test_material_specification_excludes_physical_origin_claims() -> None:
    assert "origin" not in ExactConstructionMaterial.model_fields
    with pytest.raises(ValidationError, match="origin"):
        ExactConstructionMaterial.model_validate(
            {
                "origin": "synthesized",
                "sequence_5prime": "ACGT",
                "five_prime_end": EndChemistry.HYDROXYL,
                "three_prime_end": EndChemistry.HYDROXYL,
            }
        )


@pytest.mark.parametrize(
    ("mutation", "message"),
    (
        ("forward_mismatch", "forward primer"),
        ("reverse_mismatch", "reverse primer"),
        ("primer_phosphate", "three-prime hydroxyl"),
        ("overlap", "must not overlap"),
        ("forged_material_id", "content identity"),
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
            update={"oligo": _changed_material(forward.oligo, sequence_5prime="TCGT")}
        )
    elif mutation == "reverse_mismatch":
        reverse = reverse.model_copy(
            update={"oligo": _changed_material(reverse.oligo, sequence_5prime="TGAA")}
        )
    elif mutation == "primer_phosphate":
        forward = forward.model_copy(
            update={
                "oligo": _changed_material(
                    forward.oligo,
                    three_prime_end=EndChemistry.PHOSPHATE,
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
    elif mutation == "forged_material_id":
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
        "input_state",
        "pre_state",
        "binding",
        "source_use_role",
        "source_use_entry",
        "product_sequence",
        "product_lineage",
        "pairings",
        "produced_material",
        "produced_use_role",
        "upstream_lineage",
        "produced_state",
        "post_state",
    ),
)
def test_source_duplex_preparation_rejects_forged_authority(mutation: str) -> None:
    authority = _authority()
    data = authority.model_dump(mode="python")
    if mutation == "authority_id":
        data["authority_id"] = f"hop:source-duplex-preparation/{'0' * 64}@1"
    elif mutation == "input_state":
        data["input_state"]["molecules"][0]["sequence"] = "TCGTGGAATTCC"
    elif mutation == "pre_state":
        data["pre_state_id"] = f"hop:construction-state/{'0' * 64}@1"
    elif mutation == "binding":
        data["bindings"][0]["orientation"] = BindingOrientation.SAME_5TO3
    elif mutation == "source_use_role":
        data["source_ssdna_use"]["role"] = MaterialUseRole.ENDPOINT_FORWARD_PRIMER
    elif mutation == "source_use_entry":
        data["source_ssdna_use"]["route_entry"] = MaterialRouteEntry.MODELED_PRODUCT
    elif mutation == "product_sequence":
        data["product_state"]["molecules"][0]["sequence"] = "TCGTGGAATTCC"
    elif mutation == "product_lineage":
        data["product_state"]["molecules"][0]["lineage"][0]["origin_id"] = "forged"
    elif mutation == "pairings":
        data["product_state"]["pairings"] = data["product_state"]["pairings"][:-1]
    elif mutation == "produced_material":
        data["produced_material_bindings"][0]["material"]["sequence_5prime"] = "TCGTGGAATTCC"
    elif mutation == "produced_use_role":
        data["produced_material_bindings"][0]["material_use"]["role"] = (
            MaterialUseRole.ENDPOINT_FORWARD_PRIMER
        )
    elif mutation == "upstream_lineage":
        data["produced_material_bindings"][0]["upstream_lineage"] = data[
            "produced_material_bindings"
        ][0]["upstream_lineage"][:-1]
    elif mutation == "produced_state":
        data["produced_material_bindings"][0]["product_state_id"] = (
            f"hop:construction-state/{'0' * 64}@1"
        )
    elif mutation == "post_state":
        data["post_state_id"] = f"hop:construction-state/{'0' * 64}@1"
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
    changed_source = _changed_material(
        source,
        five_prime_end=EndChemistry.PHOSPHATE,
    )

    changed = derive_source_duplex_preparation(
        source_ssdna=changed_source,
        forward_primer=forward,
        reverse_primer=reverse,
        payload_source_span=_payload_span(),
    )

    assert changed.authority_id != baseline.authority_id
