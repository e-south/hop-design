"""A uniquely located end may have no bases in the adapter-contact region."""

import json
from pathlib import Path

import pytest

from hop_design.models.construction.product_request import ProductRequest


def product(nick_offsets=(4,), strand="bottom", polarity="five_prime"):
    path = Path.cwd() / "examples/complete-construction/product-request.json"
    data = json.loads(path.read_text())
    data["ends"]["left"]["payload_end_offset_bp"] = 0
    data["ends"]["left"]["overhang_end"] = polarity
    data["basal"]["geometry"].update(
        nick_offsets_nt=list(nick_offsets),
        nick_strand=strand,
        pairing_constraints=[],
    )
    data["basal"]["end_footprint_pairing"] = {
        "reference": "left_end_source_contacts",
        "proximal": "match",
        "within": "any",
    }
    return ProductRequest.model_validate_json(json.dumps(data))


@pytest.mark.parametrize("nick,overlap", [(3, 1), (4, 0), (5, 0)])
@pytest.mark.parametrize("polarity", ["five_prime", "three_prime"])
def test_unique_empty_overlap_preserves_proximal_match(nick, overlap, polarity):
    request = product((nick,), polarity=polarity)
    assert len(request.source_end_footprint()) == overlap
    source = request.construction_source()
    assert source.basal is not None
    contacts = source.basal.geometry_domain.pairing_constraints
    assert [(c.position_from_ligation, c.allowed_class.value) for c in contacts] == [(0, "match")]
    assert len(request.implied_source_contact_bases()) == overlap
    assert source.composition.release is not None and request.ends is not None
    assert source.composition.release.left == request.ends.left


@pytest.mark.parametrize("offsets,strand", [((3, 4), "bottom"), ((4,), "top")])
def test_unmapped_frame_remains_invalid(offsets, strand):
    with pytest.raises(ValueError, match="uniquely mapped"):
        product(offsets, strand).construction_source()


def test_empty_overlap_preserves_absolute_bases_and_proximal_conflicts():
    data = product().model_dump(mode="json", by_alias=True)
    data["basal"]["geometry"]["pairing_constraints"] = [
        {
            "position_from_ligation": 0,
            "allowed_class": "match",
            "allowed_source_bases": ["C"],
            "allowed_adapter_bases": ["G"],
        }
    ]
    request = ProductRequest.model_validate_json(json.dumps(data))
    contact = request.expanded_pairing_constraints()[0]
    assert contact.allowed_source_bases == ("C",)
    assert contact.allowed_adapter_bases == ("G",)
    data["basal"]["geometry"]["pairing_constraints"][0]["allowed_class"] = "wobble"
    with pytest.raises(ValueError, match="conflicts"):
        ProductRequest.model_validate_json(json.dumps(data)).expanded_pairing_constraints()
