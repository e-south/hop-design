"""Real complete preparations remain distinct when product identity converges."""

import json

from hop_design import construction
from tests.integration.test_stage_comparison_controls import loop_method_panel as loop_method_panel


def test_query_retains_methods_under_one_stage_product(loop_method_panel):
    _, path = loop_method_panel
    pool = construction.load_scaffold_exploration(path)
    request = {"result_digest": pool.result_digest, "stage": "endpoint", "focus": "loop"}
    choices = json.loads(construction.query_scaffold_variants(pool, request).json_bytes)
    assert len(choices["products"]) == 4
    assert all(len(p["option_labels"]) == 2 for p in choices["products"])
    reference = choices["products"][0]["option_labels"][0]
    request.update(
        reference=reference, controls=[{"stage": "endpoint", "property": "product_identity"}]
    )
    same = json.loads(construction.query_scaffold_variants(pool, request).json_bytes)
    assert len(same["products"]) == 1
    assert len(same["compatible_options"]) == 2
    request["controls"] = [{"stage": "hairpin", "property": "product_identity"}]
    hairpin = json.loads(construction.query_scaffold_variants(pool, request).json_bytes)
    assert len(hairpin["compatible_options"]) == 1
    assert hairpin["query"]["reference"] == reference


def test_identical_endpoint_does_not_automatically_choose_a_method(loop_method_panel):
    _, path = loop_method_panel
    pool = construction.load_scaffold_exploration(path)
    request = {"result_digest": pool.result_digest, "stage": "endpoint", "focus": "loop"}
    first = json.loads(construction.query_scaffold_variants(pool, request).json_bytes)
    choices = construction.query_scaffold_variants(
        pool,
        {
            **request,
            "reference": first["products"][0]["option_labels"][0],
            "controls": [{"stage": "endpoint", "property": "product_identity"}],
        },
    )
    summary = json.loads(choices.json_bytes)
    result = json.loads(
        construction.preview_scaffold_variant(
            pool,
            choices,
            {
                "result_digest": pool.result_digest,
                "query_digest": summary["query_digest"],
                "variant_id": summary["variants"][0]["variant_id"],
                "state": "endpoint",
            },
        ).json_bytes
    )
    assert result["status"] == "preparation_choice_required"
    assert result["inspection"] is None
    assert len(result["candidates"]) == 2
    assert len({c["molecular_identity"]["endpoint"] for c in result["candidates"]}) == 1
