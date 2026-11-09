"""Necessary relations depend on fresh full catalog content, including metadata."""

import json

import pytest

from hop_design.design.construction.surveys.completion.interfaces import EndPairRelations
from hop_design.models.construction.product_request import ProductRequest
from hop_design.models.construction.surveys.execution import DEFAULT_SEQUENCE_LIMITS
from hop_design.models.enzymes import CharacterizedEnzymeCatalog
from tests.support.context_completion import policy
from tests.unit.test_survey_completion_binding import product


@pytest.mark.parametrize("change", ["order", "metadata", "catalog_id", "cut_offset"])
def test_fresh_catalog_changes_cannot_hit_a_warm_relation(change):
    first = product()
    data = first.model_dump(mode="json", by_alias=True)
    catalog = data["enzyme_catalog"]
    if change == "order":
        catalog["enzymes"].reverse()
    elif change == "metadata":
        catalog["enzymes"][0]["vendor_metadata"] = [{"vendor_name": "Another supplier"}]
    elif change == "catalog_id":
        catalog["catalog_id"] = "example:catalog/another@1"
    else:
        # An unused definition is still part of the caller's complete snapshot.
        unused = {**catalog["enzymes"][0], "enzyme_id": "example:enzyme/unused@1"}
        catalog["enzymes"].append(unused)
        first = ProductRequest.model_validate_json(json.dumps(data))
        unused["cut_offset_reference_strand"] += 1
    second = ProductRequest.model_validate_json(json.dumps(data))
    owner = EndPairRelations(policy("N" * 14), DEFAULT_SEQUENCE_LIMITS)
    expected = EndPairRelations(policy("N" * 14), DEFAULT_SEQUENCE_LIMITS).relation(second)
    previous = owner.relation(first)
    current = owner.relation(second)
    assert current == expected and current is not previous
    assert owner.relation(second) is current


def test_snapshot_does_not_retain_a_live_catalog_hash():
    p = product()
    catalog = p.enzyme_catalog
    unused = catalog.enzymes[0].model_copy(
        update={
            "enzyme_id": "example:enzyme/unused@1",
            "cut_offset_reference_strand": -1,
        }
    )
    catalog = catalog.model_copy(update={"enzymes": (*catalog.enzymes, unused)})
    p = p.model_copy(update={"enzyme_catalog": catalog})
    owner = EndPairRelations(policy("N" * 14), DEFAULT_SEQUENCE_LIMITS)
    previous = owner.relation(p)
    # Even a same-object mutation must be seen freshly. These integers have the
    # same Python hash, so a memo keyed by the frozen model can miss this change.
    object.__setattr__(unused, "cut_offset_reference_strand", -2)
    assert owner.relation(p) is not previous


def test_catalog_subclass_cannot_hide_content_by_overriding_dump_json():
    class CustomCatalog(CharacterizedEnzymeCatalog):
        def model_dump_json(self, **kwargs):
            return "{}"

    p = product()
    first = CustomCatalog.model_validate(p.enzyme_catalog.model_dump())
    second = first.model_copy(update={"catalog_id": "example:catalog/another@1"})
    owner = EndPairRelations(policy("N" * 14), DEFAULT_SEQUENCE_LIMITS)
    previous = owner.relation(p.model_copy(update={"enzyme_catalog": first}))
    assert owner.relation(p.model_copy(update={"enzyme_catalog": second})) is not previous
