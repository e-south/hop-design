"""Intersect end-relative permissions with explicit and required contact classes."""

import json
from pathlib import Path

import pytest

from hop_design.models.construction.product_pairing import EndFootprintPairing
from hop_design.models.construction.product_request import ProductRequest
from hop_design.models.construction.targets import BasalPairAllowance, BasalPairConstraint


@pytest.mark.parametrize("within,absolute", [("any", "match"), ("match", "any")])
def test_end_relative_and_absolute_permissions_intersect(within, absolute):
    rule = EndFootprintPairing.model_validate_json(
        json.dumps({"reference": "left_end_source_contacts", "proximal": "match", "within": within})
    )
    constraint = BasalPairConstraint(
        position_from_ligation=2,
        allowed_class=BasalPairAllowance(absolute),
        allowed_adapter_bases=("G",),
    )
    contacts = rule.expand(((2, "C"), (3, "A")), (constraint,))
    assert contacts[2].allowed_class is BasalPairAllowance.MATCH
    assert contacts[2].allowed_adapter_bases == ("G",)
    assert contacts[3].allowed_class is BasalPairAllowance(within)


def test_zero_gap_permissions_preserve_route_required_proximal_match():
    path = (
        Path(__file__).resolve().parents[2] / "examples/complete-construction/product-request.json"
    )
    data = json.loads(path.read_text())
    data["ends"]["left"]["payload_end_offset_bp"] = 0
    data["basal"]["geometry"]["pairing_constraints"] = []
    data["basal"]["end_footprint_pairing"] = {
        "reference": "left_end_source_contacts",
        "proximal": "match",
        "within": "any",
    }
    product = ProductRequest.model_validate_json(json.dumps(data))
    source = product.construction_source()
    assert source.basal is not None
    contacts = source.basal.geometry_domain.pairing_constraints
    assert [c.allowed_class.value for c in contacts] == ["match", "any", "any", "any"]
    assert product.model_dump(mode="json")["basal"]["end_footprint_pairing"]["within"] == "any"


def test_disjoint_contact_classes_remain_a_scoped_conflict():
    rule = EndFootprintPairing.model_validate_json(
        json.dumps(
            {
                "reference": "left_end_source_contacts",
                "proximal": "match",
                "within": "wobble",
            }
        )
    )
    with pytest.raises(ValueError, match="conflicts"):
        rule.expand(
            ((2, "C"),),
            (
                BasalPairConstraint(
                    position_from_ligation=2,
                    allowed_class=BasalPairAllowance.MATCH,
                ),
            ),
        )
