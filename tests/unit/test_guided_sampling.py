"""Guided samples teach distinct molecules while preserving complete witnesses."""

from typing import ClassVar

import pytest

from hop_design.design.construction.navigation.guided_sampling import guided_sample
from tests.unit.test_molecular_families import path


class Choices:
    resolution: ClassVar[dict] = {"intent": {"product": "hairpin"}}

    def __init__(self, paths):
        self.paths = paths

    def query(self, query=None):
        return {
            "paths": self.paths,
            "query": query or {"parameters": []},
            "snapshot_digest": "sha256:" + "a" * 64,
        }

    def select(self, identity, *, query=None):
        return {"materialized_realization_id": identity, "query": query or {"parameters": []}}


def test_guidance_visits_another_family_without_counting_routes_as_products():
    rows = [path("a", "one"), path("b", "one"), path("c", "two", loop=6, extension=5)]
    receipt = guided_sample(Choices(rows), seed=4, history=("a",), stage="hairpin")
    assert receipt["selection"]["materialized_realization_id"] == "c"
    assert receipt["status"] == "different_family"
    assert receipt["eligible_products"] == 2
    assert receipt["eligible_preparations"] == 3
    assert receipt == guided_sample(
        Choices(list(reversed(rows))), seed=4, history=("a",), stage="hairpin"
    )


def test_guidance_explains_preparation_only_change_and_singletons():
    receipt = guided_sample(Choices([path("a", "same"), path("b", "same")]), seed=0, history=("a",))
    assert receipt["selection"]["materialized_realization_id"] == "b"
    assert receipt["status"] == "preparation_alternative"
    assert "same molecule" in receipt["explanation"].lower()
    singleton = guided_sample(Choices([path("a", "same")]), seed=0, history=("a",))
    assert singleton["status"] == "only_preparation"


def test_ineligible_products_are_never_sampled_and_no_match_does_not_relax():
    rows = [path("a", "one"), path("b", "two", matches=False, loop=6)]
    assert guided_sample(Choices(rows), seed=3)["selection"]["materialized_realization_id"] == "a"
    with pytest.raises(ValueError, match="No complete"):
        guided_sample(Choices([rows[1]]), seed=3)
    with pytest.raises(ValueError, match="history"):
        guided_sample(Choices(rows), seed=3, history=("another-edition",))
