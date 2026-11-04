"""Required members use the admitted pool without weakening its conditional query."""

import json

import pytest

from hop_design import construction


def test_required_members_and_selection_revalidate_the_same_pool(loop_options, tmp_path):
    path, _ = loop_options
    pool = construction.load_scaffold_exploration(path)
    choices = construction.query_scaffold_variants(
        pool, {"result_digest": pool.result_digest, "stage": "hairpin", "focus": "loop"}
    )
    request = {
        "result_digest": pool.result_digest,
        "query_digest": json.loads(choices.json_bytes)["query_digest"],
        "required_members": [
            {"name": "gaaa", "loop_sequence": "GAAA"},
            {"name": "tttc", "loop_sequence": "TTTC"},
        ],
        "stage_controls": [{"stage": "hairpin", "property": "non_loop_sequences", "scope": "set"}],
        "max_group_evaluations": 32,
    }
    assessed = construction.compare_scaffold_variants(pool, choices, request)
    summary = json.loads(assessed.json_bytes)
    assert summary["status"] == "comparison_available"
    assert summary["selected_set"] is None
    assert len(summary["sets"]) == 1
    assert set(summary["sets"][0]["members"]) == {"gaaa", "tttc"}
    reordered = {**request, "required_members": list(reversed(request["required_members"]))}
    assert (
        construction.compare_scaffold_variants(pool, choices, reordered).json_bytes
        == assessed.json_bytes
    )
    saved = assessed.write(tmp_path / "comparison")
    selected = construction.select_scaffold_variant_comparison(
        path, saved, set_label="set-0001", baseline="gaaa"
    ).write(tmp_path / "selected")
    receipt = json.loads((selected / "variant-comparison-selection.json").read_bytes())
    assert receipt["query_digest"] == request["query_digest"]
    assert receipt["members"] == summary["sets"][0]["members"]
    replayed = construction.select_construction_set(selected / "set.json")
    assert (
        json.loads(replayed.json_bytes)["set_id"]
        == json.loads((selected / "summary.json").read_bytes())["set_id"]
    )
    with pytest.raises(ValueError, match="Unknown comparison set"):
        construction.select_scaffold_variant_comparison(
            path, saved, set_label="missing", baseline="gaaa"
        )


def test_missing_member_is_not_silently_dropped(loop_options):
    path, _ = loop_options
    pool = construction.load_scaffold_exploration(path)
    choices = construction.query_scaffold_variants(
        pool, {"result_digest": pool.result_digest, "stage": "hairpin", "focus": "loop"}
    )
    observed = json.loads(choices.json_bytes)
    ga = next(v for v in observed["variants"] if v["sequences"][0]["sequence"] == "GAAA")
    pinned = construction.query_scaffold_variants(
        pool,
        {
            **observed["query"],
            "pins": [{"neighborhood": "loop", "variant_ids": [ga["variant_id"]]}],
        },
    )
    request = {
        "result_digest": pool.result_digest,
        "query_digest": json.loads(pinned.json_bytes)["query_digest"],
        "required_members": [
            {"name": "gaaa", "loop_sequence": "GAAA"},
            {"name": "tttc", "loop_sequence": "TTTC"},
        ],
        "max_group_evaluations": 1,
    }
    result = json.loads(construction.compare_scaffold_variants(pool, pinned, request).json_bytes)
    assert result["sets"] == []
    assert result["members"][1]["status"] == "missing_from_evaluated_pool"
    assert result["missing_members"][0]["reason"] == "excluded_by_query"
    with pytest.raises(ValueError, match="Stale"):
        construction.compare_scaffold_variants(pool, choices, request)


def test_interface_choices_report_achieved_coordinates_and_named_methods(loop_options):
    path, _ = loop_options
    pool = construction.load_scaffold_exploration(path)
    choices = json.loads(
        construction.query_scaffold_variants(
            pool, {"result_digest": pool.result_digest, "stage": "endpoint", "focus": "interfaces"}
        ).json_bytes
    )
    assert choices["preparations"]
    for preparation in choices["preparations"]:
        assert preparation["interface"]["requested_distances_bp"] == {"left": 6, "right": 6}
        assert preparation["interface"]["achieved_distances_bp"] == {"left": 6, "right": 6}
        assert preparation["interface"]["coordinate_basis"] == "recorded_cuts_and_stem_boundaries"
        assert {m["name"] for m in preparation["methods"]} >= {"Nb.BsrDI", "BsaI-HFv2"}
    assert choices["interface_coverage"]["global_minimum"] == "not_assessed"


def test_truncated_grouping_and_material_controls_remain_explicit(loop_options):
    path, _ = loop_options
    pool = construction.load_scaffold_exploration(path)
    choices = construction.query_scaffold_variants(
        pool, {"result_digest": pool.result_digest, "stage": "hairpin", "focus": "loop"}
    )
    request = {
        "result_digest": pool.result_digest,
        "query_digest": json.loads(choices.json_bytes)["query_digest"],
        "required_members": [
            {"name": "a", "dimensions": {"loop_nt": 4}},
            {"name": "b", "dimensions": {"loop_nt": 4}},
        ],
        "max_group_evaluations": 1,
    }
    partial = json.loads(construction.compare_scaffold_variants(pool, choices, request).json_bytes)
    assert partial["sets"] == []
    assert partial["status"] == "group_evaluation_incomplete"
    assert partial["group_coverage"]["unexamined_assignments"] == 3
    protected = json.loads(
        construction.compare_scaffold_variants(
            pool,
            choices,
            {**request, "max_group_evaluations": 4, "preserve_material_roles": ["source_ssdna"]},
        ).json_bytes
    )
    assert protected["sets"] == []
    assert protected["group_coverage"]["rejections"]["preserved_material_changed"] == 2


def test_resealed_comparison_and_changed_source_are_rejected(loop_options, tmp_path):
    import shutil

    from hop_design.serialization import canonical_json_bytes, sha256_digest

    path, _ = loop_options
    pool = construction.load_scaffold_exploration(path)
    choices = construction.query_scaffold_variants(
        pool, {"result_digest": pool.result_digest, "stage": "hairpin", "focus": "loop"}
    )
    request = {
        "result_digest": pool.result_digest,
        "query_digest": json.loads(choices.json_bytes)["query_digest"],
        "required_members": [{"name": "gaaa", "loop_sequence": "GAAA"}],
        "max_group_evaluations": 8,
    }
    packet = construction.compare_scaffold_variants(pool, choices, request)
    saved = packet.write(tmp_path / "comparison")
    summary = json.loads((saved / "summary.json").read_bytes())
    summary["group_coverage"]["evaluated_assignments"] += 1
    altered = canonical_json_bytes(summary)
    (saved / "summary.json").write_bytes(altered)
    manifest = json.loads((saved / "manifest.json").read_bytes())
    manifest["artifacts"]["summary.json"] = sha256_digest(altered)
    (saved / "manifest.json").write_bytes(canonical_json_bytes(manifest))
    with pytest.raises(ValueError, match="disagrees"):
        construction.select_scaffold_variant_comparison(
            path, saved, set_label="set-0001", baseline="gaaa"
        )
    moved = tmp_path / "source"
    shutil.copytree(path, moved)
    (moved / "summary.json").write_text("{}")
    with pytest.raises(ValueError, match=r"digest|manifest|artifact|inventory"):
        construction.select_scaffold_variant_comparison(
            moved, packet, set_label="set-0001", baseline="gaaa"
        )


def test_native_discovery_receipt_uses_the_same_comparison_operations(loop_options, tmp_path):
    path, _ = loop_options
    source = path / "options"
    pool = construction.load_scaffold_exploration(source)
    assert json.loads(pool.json_bytes)["edit_digest"] is None
    choices = construction.query_scaffold_variants(
        pool, {"result_digest": pool.result_digest, "stage": "hairpin", "focus": "loop"}
    )
    assessed = construction.compare_scaffold_variants(
        pool,
        choices,
        {
            "result_digest": pool.result_digest,
            "query_digest": json.loads(choices.json_bytes)["query_digest"],
            "required_members": [
                {"name": "gaaa", "loop_sequence": "GAAA"},
                {"name": "tttc", "loop_sequence": "TTTC"},
            ],
            "max_group_evaluations": 8,
        },
    )
    selected = construction.select_scaffold_variant_comparison(
        source, assessed, set_label="set-0001", baseline="gaaa"
    ).write(tmp_path / "selected")
    assert not (selected / "molecular-edit.json").exists()
    assert set(
        json.loads((selected / "variant-comparison-selection.json").read_bytes())["members"]
    ) == {"gaaa", "tttc"}
