"""Public exploration projects measured construction choices and original permissions."""

import json

from hop_design import construction


def test_targeted_evaluation_replays_constraints_and_preserves_rejected_complete_candidates(
    tmp_path,
):
    from pathlib import Path

    value = json.loads(Path("examples/molecular-editing/request.json").read_bytes())
    value.update(
        schema="hop.scaffold-discovery/v5",
        parameters=[
            {"key": "self_paired_arm_bp", "minimum": 7, "maximum": 7},
            {"key": "loop_word", "values": ["GAAA"]},
            {"key": "noncanonical_pairs", "minimum": 1, "maximum": 1},
        ],
    )
    path = tmp_path / "request.json"
    path.write_text(json.dumps(value))
    packet = construction.discover_scaffolds(path)
    summary = json.loads(packet.json_bytes)
    assert summary["options"] == []
    exclusions = summary["branches"][0]["parameter_exclusions"]
    assert exclusions
    assert exclusions[0]["reasons"][0]["parameter"] == "noncanonical_pairs"
    saved = packet.write(tmp_path / "evaluated")
    pool = construction.load_scaffold_exploration(saved)
    choices = json.loads(
        construction.query_scaffold_variants(
            pool,
            {
                "result_digest": pool.result_digest,
                "stage": "hairpin",
                "focus": "loop",
            },
        ).json_bytes
    )
    assert choices["compatible_options"] == []
    assert choices["choice_space"]["axes"]  # permissions do not disappear with no witnesses
    assert choices["choice_space"]["branch_coverage"][0]["parameter_exclusions"] == exclusions


def test_complete_pool_has_foldback_parameters_method_roles_and_positional_bases(loop_pool):
    query = {
        "schema": "hop.scaffold-variant-query/v2",
        "result_digest": loop_pool.result_digest,
        "stage": "hairpin",
        "focus": "loop",
        "parameters": [{"key": "self_paired_arm_bp", "minimum": 7, "maximum": 7}],
    }
    result = json.loads(construction.query_scaffold_variants(loop_pool, query).json_bytes)
    assert len(result["compatible_options"]) == 2
    axes = {a["key"]: a for a in result["choice_space"]["axes"]}
    assert axes["foldback_arm_bp"]["symbol"] == "A"
    assert axes["join_offset_nt"]["symbol"] == "D"
    assert axes["self_paired_arm_bp"]["relationship"] == "R = A - D"
    assert axes["basal_source_base_0"]["position_from_ligation"] == 0
    for path in result["choice_space"]["paths"]:
        assert path["values"]["foldback_arm_bp"] == 9
        assert path["values"]["join_offset_nt"] == 2
        assert path["values"]["self_paired_arm_bp"] == 7
        assert path["values"]["basal_nick_offset_nt"] == 0
        assert path["values"]["foldback_method"] == "example:enzyme/nt.bpu10i@1"
        assert path["values"]["basal_method"] == "example:enzyme/nb.bsrdi@1"
        assert path["values"]["release_method"] == "example:enzyme/bsai-hfv2@1"
        assert path["values"]["basal_pair_class_0"] == "match"
        assert path["values"]["left_end_word"] == "AGTC"
    assert result["choice_space"]["branch_coverage"]


def test_atlas_parameters_address_recorded_bases_and_expose_local_contact_axes(loop_pool):
    choices = construction.query_scaffold_variants(
        loop_pool,
        {
            "result_digest": loop_pool.result_digest,
            "stage": "hairpin",
            "focus": "loop",
        },
    )
    summary = json.loads(choices.json_bytes)
    packet = construction.inspect_scaffold_atlas(
        loop_pool,
        choices,
        {
            "result_digest": loop_pool.result_digest,
            "query_digest": summary["query_digest"],
            "option_label": summary["compatible_options"][0],
        },
    )
    result = json.loads(packet.json_bytes)
    locations = {p["key"]: p for p in result["parameter_locations"]}
    assert len(locations["foldback_arm_bp"]["reference_addresses"]) == 18
    assert len(locations["join_offset_nt"]["reference_addresses"]) == 4
    assert len(locations["self_paired_arm_bp"]["reference_addresses"]) == 14
    assert len(locations["loop_word"]["reference_addresses"]) == 4
    assert len(locations["basal_pair_class_0"]["reference_addresses"]) == 2
    known = {
        (b["address"]["state_id"], b["address"]["strand_id"], b["address"]["index"])
        for s in result["atlas"]["states"]
        for b in s["bases"]
    }
    for location in locations.values():
        assert all(
            (a["state_id"], a["strand_id"], a["index"]) in known for a in location["occurrences"]
        )
    assert len({a["state_id"] for a in locations["loop_word"]["occurrences"]}) > 4
    assert b"data-parameter-keys=" in packet.svg_bytes


def test_local_support_keeps_partial_coordinates_separate_from_complete_paths(loop_pool):
    choices = json.loads(
        construction.query_scaffold_variants(
            loop_pool,
            {
                "result_digest": loop_pool.result_digest,
                "stage": "hairpin",
                "focus": "loop",
            },
        ).json_bytes
    )
    local = choices["choice_space"]["local_support"]
    assert local
    foldback = [p for p in local if p["scope"] == "foldback_local_only"]
    assert {p["values"]["loop_word"] for p in foldback} == {"GAAA", "TTTC"}
    assert all("left_gap" not in p["values"] and "molecule_id" not in p for p in local)
    assert all(p["complete_preparation_status"] == "not_established_by_local_record" for p in local)
    assert all(p["branch_ids"] and p["local_realization_id"] for p in local)
