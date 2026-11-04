"""Structural families explain grouping without inflating molecular diversity."""

from hop_design.design.construction.navigation.molecular_groups import molecular_families


def choices(paths):
    return {
        "paths": paths,
        "query": {"schema": "hop.interface-survey-query/v1", "parameters": []},
        "snapshot_digest": "sha256:" + "a" * 64,
    }


def path(preparation, product, *, loop=4, extension=6, matches=True):
    return {
        "materialized_realization_id": preparation,
        "molecular_identity": {"hairpin": product, "endpoint": product},
        "matches": matches,
        "values": {"loop_nt": loop, "loop_side_paired_bp": extension, "loop_word": "AAAA"},
    }


def test_product_marks_keep_preparations_separate_and_all_members_recoverable():
    rows = [path("route-a", "same"), path("route-b", "same"), path("route-c", "different")]
    atlas = molecular_families(choices([*rows, rows[0]]), stage="hairpin")
    assert len(atlas["products"]) == 2
    assert len(atlas["families"]) == 1
    assert atlas["layout"]["kind"] == "mosaic"
    product = next(p for p in atlas["products"] if p["identity"] == "same")
    assert product["preparations"] == ["route-a", "route-b"]
    assert atlas == molecular_families(choices(list(reversed(rows))), stage="hairpin")


def test_varied_geometry_has_named_axes_and_ineligible_products_remain_context():
    rows = [path("a", "one"), path("b", "two", loop=6, extension=5, matches=False)]
    atlas = molecular_families(choices(rows), stage="hairpin")
    assert len(atlas["families"]) == 2
    assert atlas["layout"] == {
        "kind": "feature_map",
        "x": "loop_nt",
        "y": "foldback_arm_bp",
    }
    assert (
        next(p for p in atlas["products"] if p["identity"] == "two")["state"]
        == "supported_elsewhere"
    )
    assert next(p for p in atlas["products"] if p["identity"] == "one")["state"] == "supported"


def test_stage_changes_product_grouping_without_using_upstream_geometry_as_insert_geometry():
    rows = [path("a", "hairpin-a"), path("b", "hairpin-b", loop=6)]
    for row in rows:
        row["molecular_identity"]["endpoint"] = "same-insert"
        row["values"].update(left_gap=0, right_gap=0, left_end_word="AGTC", right_end_word="AACC")
    atlas = molecular_families(choices(rows), stage="endpoint")
    assert len(atlas["products"]) == len(atlas["families"]) == 1
    assert "loop_nt" not in atlas["families"][0]["features"]
    assert atlas["products"][0]["preparations"] == ["a", "b"]


def test_equivalent_arm_names_group_without_changing_the_input():
    import copy

    row = path("a", "one")
    expected = molecular_families(choices([row]), stage="hairpin")
    equivalent = copy.deepcopy(row)
    equivalent["values"]["foldback_arm_bp"] = equivalent["values"].pop("loop_side_paired_bp")
    before = copy.deepcopy(equivalent)
    assert molecular_families(choices([equivalent]), stage="hairpin") == expected
    assert equivalent == before


def test_context_distributions_name_the_denominator_and_do_not_turn_missing_into_zero():
    rows = [path("a", "same"), path("b", "same", matches=False), path("c", "other", loop=6)]
    missing = path("d", "unknown")
    missing["values"].pop("loop_nt")
    result = molecular_families(choices([*rows, missing, rows[0]]), stage="hairpin")
    distribution = result["distributions"][0]
    assert distribution["key"] == "loop_nt"
    assert distribution["unit"] == "nt"
    assert distribution["stage"] == "hairpin"
    assert distribution["counted"] == "preparations"
    assert distribution["denominator"] == {"recorded": 4, "eligible": 3}
    assert distribution["missing"] == {"recorded": 1, "eligible": 1}
    assert distribution["bins"] == [
        {"value": 4, "recorded": 2, "eligible": 1},
        {"value": 6, "recorded": 1, "eligible": 1},
    ]


def test_coincident_families_name_the_recorded_feature_that_distinguishes_them():
    rows = [path("a", "one"), path("b", "two"), path("c", "three", loop=6, extension=5)]
    for row, tail in zip(rows, (0, 2, 0), strict=True):
        row["values"]["five_prime_unpaired_nt"] = tail
    families = molecular_families(choices(rows), stage="hairpin")["families"]
    assert len({f["label"] for f in families}) == 3
    coincident = [f for f in families if f["features"]["loop_nt"] == [4]]
    assert all("tail" in f["label"].lower() for f in coincident)
    assert {tuple(f["preparations"]) for f in families} == {("a",), ("b",), ("c",)}


def test_same_end_words_do_not_hide_recorded_loop_differences_between_insert_products():
    rows = [path("a", "one"), path("b", "two")]
    for row, loop in zip(rows, ("GAAA", "TTTC"), strict=True):
        row["values"].update(
            left_gap=0, right_gap=0, left_end_word="AGTC", right_end_word="AACC", loop_word=loop
        )
    atlas = molecular_families(choices(rows), stage="endpoint")
    assert {p["label"] for p in atlas["products"]} == {
        "AGTC · AACC · loop GAAA",
        "AGTC · AACC · loop TTTC",
    }
    assert len(atlas["families"]) == 1
