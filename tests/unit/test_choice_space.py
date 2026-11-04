"""Choice coordinates remain a projection of complete, stage-qualified witnesses."""

from copy import deepcopy


def candidates():
    def option(label, loop, background, method, product, distance):
        def region(name, word):
            return {
                "variant_id": f"{name}:{word}",
                "sequences": [{"region": name, "strand": 0, "sequence": word}],
                "contacts": [],
                "terminals": [],
            }

        regions = {
            "loop": region("loop", loop),
            "closing": region("closing", "CG"),
            "assembly": region("assembly", background),
            "stem": region("stem", "ACGT"),
            "interfaces": region("interfaces", "AGTC"),
        }
        return {
            "label": label,
            "loop_sequence": loop,
            "molecular_identity": {"hairpin": label, "endpoint": product},
            "variants": {"hairpin": regions, "endpoint": deepcopy(regions)},
            "geometry": {"loop_nt": 4, "loop_side_paired_bp": 9},
            "interface": {"achieved_distances_bp": {"left": distance, "right": 6}},
            "methods": [{"role": "basal_nick", "name": method, "enzyme_id": method}],
        }

    return [
        option("a", "GAAA", "ACGA", "method-a", "product-1", 0),
        option("b", "TTTC", "ACGG", "method-b", "product-2", 6),
        option("c", "GAAA", "ACGG", "method-b", "product-1", 6),
    ]


def test_choice_paths_keep_whole_witnesses_and_group_exact_stage_products():
    from hop_design.design.construction.variants.choice_space import choice_space

    options = candidates()
    before = deepcopy(options)
    result = choice_space(options, ["a", "c"], "endpoint")
    assert result["scope"] == "active_query_complete_options_only"
    assert [p["option_label"] for p in result["paths"]] == ["a", "c"]
    assert result["products"] == [{"molecule_id": "product-1", "option_labels": ["a", "c"]}]
    assert result["paths"][0]["values"]["left_gap"] == 0
    assert result["paths"][1]["values"]["left_gap"] == 6
    assert result["paths"][0]["values"]["background"] != result["paths"][1]["values"]["background"]
    axes = {a["key"]: a for a in result["axes"]}
    assert axes["left_gap"]["kind"] == "numeric"
    assert axes["left_gap"]["stage"] == "released_insert"
    assert axes["loop_word"]["kind"] == "categorical"
    assert axes["loop_word"]["stage"] == "hairpin"
    assert axes["background"]["stage"] == "endpoint"
    assert axes["loop_nt"]["varying"] is False
    assert options == before


def test_background_identity_is_independent_of_loop_method_and_product_identity():
    from hop_design.design.construction.variants.choice_space import choice_space

    options = candidates()
    result = choice_space(options, ["a", "b", "c"], "hairpin")
    paths = result["paths"]
    assert paths[1]["values"]["background"] == paths[2]["values"]["background"]
    assert len(result["products"]) == 3
    axis = next(a for a in result["axes"] if a["key"] == "background")
    assert any("ACGA" in v["label"] for v in axis["values"])
    assert any("ACGG" in v["label"] for v in axis["values"])
    assert all("ACGT" not in v["label"] for v in axis["values"])


def test_missing_regional_evidence_is_unassessed_and_empty_query_stays_empty():
    from hop_design.design.construction.variants.choice_space import choice_space

    options = candidates()
    options[0]["variants"]["endpoint"]["assembly"] = None
    options[0]["interface"] = None
    result = choice_space(options, ["a"], "endpoint")
    assert result["paths"][0]["values"]["background"] is None
    assert result["paths"][0]["values"]["left_gap"] is None
    assert choice_space(options, [], "endpoint")["paths"] == []
    assert choice_space(options, [], "endpoint")["products"] == []


def test_unobserved_composite_selection_stays_explicit_without_inventing_a_background():
    from hop_design.design.construction.variants.choice_space import choice_space
    from hop_design.models.construction.variants.parameters import ParameterSelection

    selection = ParameterSelection(key="background", values=("unobserved",))
    result = choice_space(candidates(), ["a", "b", "c"], "hairpin", selections=(selection,))
    axis = next(a for a in result["axes"] if a["key"] == "background")
    entry = next(v for v in axis["values"] if v["value"] == "unobserved")
    assert entry["detail"] is None
    assert result["availability"]["background"]["unobserved"] == 0
