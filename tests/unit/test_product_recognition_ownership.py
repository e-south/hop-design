"""Recognition-site ownership does not change source-adapter contact coordinates."""

import json
from pathlib import Path

import pytest

from hop_design.models.construction.product_request import ProductRequest


def request(*, ownership, gap=6, nick=1, polarity="five_prime"):
    data = json.loads(Path("examples/complete-construction/product-request.json").read_text())
    data["release"]["basal_projection"]["recognition_material"] = ownership
    data["ends"]["left"].update(payload_end_offset_bp=gap, overhang_end=polarity)
    data["basal"]["geometry"].update(nick_offsets_nt=[nick], pairing_constraints=[])
    data["basal"]["end_footprint_pairing"] = {
        "reference": "left_end_source_contacts",
        "proximal": "match",
        "within": "any",
    }
    return ProductRequest.model_validate_json(json.dumps(data))


@pytest.mark.parametrize(
    "polarity,expected",
    [
        ("five_prime", ((5, "C"), (6, "T"), (7, "G"), (8, "A"))),
        ("three_prime", ((5, "T"), (6, "C"), (7, "A"), (8, "G"))),
    ],
)
def test_contact_frame_is_independent_of_recognition_ownership(polarity, expected):
    source = request(ownership="source_duplex", polarity=polarity)
    endpoint = request(ownership="endpoint_material", polarity=polarity)
    assert endpoint.source_end_footprint() == source.source_end_footprint() == expected
    assert endpoint.expanded_pairing_constraints() == source.expanded_pairing_constraints()
    expanded = endpoint.construction_source()
    assert expanded.basal.geometry_domain.future_release.recognition_material == "endpoint_material"
    assert (
        expanded.basal.geometry_domain.pairing_constraints
        == source.construction_source().basal.geometry_domain.pairing_constraints
    )


def test_empty_overlap_keeps_proximal_contact_and_recognition_owner():
    product = request(ownership="endpoint_material", gap=0, nick=4)
    assert product.source_end_footprint() == ()
    source = product.construction_source()
    assert [
        (c.position_from_ligation, c.allowed_class.value)
        for c in source.basal.geometry_domain.pairing_constraints
    ] == [(0, "match")]
    assert source.basal.geometry_domain.future_release.recognition_material == "endpoint_material"


@pytest.mark.parametrize("change", ["multiple-offsets", "other-strand", "other-end"])
def test_ambiguous_or_unsupported_contact_frames_remain_rejected(change):
    data = request(ownership="endpoint_material").model_dump(mode="json", by_alias=True)
    if change == "multiple-offsets":
        data["basal"]["geometry"]["nick_offsets_nt"] = [1, 2]
    elif change == "other-strand":
        data["basal"]["geometry"]["nick_strand"] = "top"
    else:
        data["release"]["basal_projection"]["product_end"] = "left"
    with pytest.raises(ValueError, match="uniquely mapped"):
        ProductRequest.model_validate_json(json.dumps(data)).construction_source()
