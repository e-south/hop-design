"""Selected molecular cost agrees with the exact endpoint and external order roles."""

import json

from hop_design import construction
from tests.integration.test_design_discovery import intent_document


def test_selected_insert_cost_is_available_before_retrieval(tmp_path):
    choices = construction.discover_designs(
        intent_document(), tmp_path / "choices", max_evaluations=2
    )
    selected = choices.sample(seed=1)
    atlas = choices.atlas(selected)
    cost = json.loads(atlas.json_bytes)["atlas"]["construction_cost"]
    assert cost["materialized_realization_id"] == selected["materialized_realization_id"]
    assert cost["added_nt_by_strand"] == {"top": 32, "bottom": 32}
    assert cost["distinct_orders"] == 5
    assert cost["material_roles"] == 6
    assert any(len(order["roles"]) == 2 for order in cost["orders"])
    assert {
        role for order in cost["orders"] if order["modifications"] for role in order["roles"]
    } == {"source_materialization_reverse_primer", "ligation_adapter"}
    for strand, total in cost["added_nt_by_strand"].items():
        spans = [r for r in cost["added_regions"] if r["strand"] == strand]
        assert sum(r["end"] - r["start"] for r in spans) == total
    assert b"5 distinct oligo orders" in atlas.svg_bytes
    atlas.write(tmp_path / "atlas", print_pages=False)
    assert json.loads((tmp_path / "atlas/construction-cost.json").read_bytes()) == cost
    assert "32 nt" in (tmp_path / "atlas/report.md").read_text()


def test_cost_uses_verified_order_identity(loop_pool):
    from hop_design.design.construction.projections.atlas import project_molecular_atlas
    from hop_design.models.construction.projections.materials import external_oligos

    route = loop_pool._routes[0][1]
    cost = project_molecular_atlas(route).construction_cost
    assert cost is not None
    assert cost.distinct_orders == len(external_oligos(route))
    assert cost.stem_arm
    assert cost.endpoint == route.final_product.reference.endpoint.value
