"""Hairpin intent returns actual hairpin endpoints through the same selection lifecycle."""

import json

import pytest

from hop_design import construction
from tests.unit.test_construction_intent import STEM


@pytest.mark.parametrize("product", ["hairpin", "adapter_ligated_hairpin"])
def test_hairpin_discovery_and_retrieval_do_not_construct_a_released_insert(product, tmp_path):
    result = construction.discover_designs(
        {"stem_arm": STEM, "product": product}, tmp_path / "designs", max_evaluations=4
    )
    query = result.query()
    assert query["matching_preparations"] > 0
    selected = result.sample(seed=0)
    atlas = result.atlas(selected)
    facts = json.loads(atlas.json_bytes)
    assert [s["frame"] for s in facts["teaching"]["scenes"]] == ["hairpin"]
    summary = facts["atlas"]
    states = summary["states"]
    cost = summary["construction_cost"]
    molecule = states[-1]["state"]["molecules"][0]
    assert cost["added_nt_by_strand"] == {
        molecule["strand_id"]: len(molecule["sequence"]) - 2 * len(STEM)
    }
    assert cost["achieved_ends"] == {}
    assert cost["distinct_orders"] <= cost["material_roles"]
    assert len(states) < 11
    assert all("release" not in s["state"]["phase"] for s in states)
    axes = ("loop_nt", "foldback_arm_bp")
    figure = result.figure(selection=selected, display_axes=axes)
    assert json.loads(dict(figure._files)["display-projection.json"])["displayed"] == list(axes)
    assert json.loads(dict(figure._files)["selection.json"]) == selected
    with pytest.raises(ValueError, match="axis"):
        result.figure(selection=selected, display_axes=("left_gap",))
    handoff = result.retrieve(selected, tmp_path / "preparation")
    assert selected["materialized_realization_id"] in handoff.materialized_realization_ids
    assert construction.load_design_choices(tmp_path / "designs").sample(seed=0) == selected
