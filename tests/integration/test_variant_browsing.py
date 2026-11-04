"""Local preview preserves intent and makes complete-preparation ambiguity explicit."""

import json

import pytest
from typer.testing import CliRunner

from hop_design import construction
from hop_design.cli import app


def test_preview_operation_is_public():
    assert callable(getattr(construction, "preview_scaffold_variant", None))


def test_cli_exposes_preview_as_separate_operation():
    result = CliRunner().invoke(app, ["construction", "preview-variant", "--help"])
    assert result.exit_code == 0, result.output


def test_multiple_products_require_an_explicit_preparation(loop_pool):
    pool = loop_pool
    choices = construction.query_scaffold_variants(
        pool, {"result_digest": pool.result_digest, "stage": "hairpin", "focus": "stem"}
    )
    summary = json.loads(choices.json_bytes)
    assert len(summary["variants"]) == 1
    request = {
        "result_digest": pool.result_digest,
        "query_digest": summary["query_digest"],
        "variant_id": summary["variants"][0]["variant_id"],
        "state": "endpoint",
    }
    pending = json.loads(construction.preview_scaffold_variant(pool, choices, request).json_bytes)
    assert pending["status"] == "preparation_choice_required"
    assert len(pending["candidates"]) == 2
    assert pending["inspection"] is None
    explicit = json.loads(
        construction.preview_scaffold_variant(
            pool, choices, {**request, "option_label": pending["candidates"][1]["label"]}
        ).json_bytes
    )
    assert explicit["status"] == "preview_available"
    assert explicit["inspection"]["molecular_state"]["state"]["phase"] == "clone_ready_duplex"


@pytest.mark.parametrize("selector", ["invented-phase", "adapter_missing"])
def test_missing_state_does_not_fall_back_to_hairpin(loop_pool, selector):
    pool = loop_pool
    choices = construction.query_scaffold_variants(
        pool, {"result_digest": pool.result_digest, "stage": "hairpin", "focus": "loop"}
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
                "state": selector,
            },
        ).json_bytes
    )
    assert result["status"] == "state_unavailable"
    assert result["inspection"] is None


def test_local_preview_preserves_choices_and_processing_phase(loop_pool):
    pool = loop_pool
    choices = construction.query_scaffold_variants(
        pool, {"result_digest": pool.result_digest, "stage": "hairpin", "focus": "loop"}
    )
    before = choices.json_bytes
    summary = json.loads(before)
    assert summary["neighborhoods"]["loop"] == {"status": "variable", "variant_count": 2}
    assert summary["neighborhoods"]["stem"] == {"status": "fixed", "variant_count": 1}
    assert summary["neighborhoods"]["interfaces"] == {"status": "unavailable", "variant_count": 0}
    for variant in summary["variants"]:
        packet = construction.preview_scaffold_variant(
            pool,
            choices,
            {
                "result_digest": pool.result_digest,
                "query_digest": summary["query_digest"],
                "variant_id": variant["variant_id"],
                "state": "cleaved_duplex",
            },
        )
        viewed = json.loads(packet.json_bytes)
        assert viewed["status"] == "preview_available"
        assert viewed["selected_product"] is None
        assert viewed["inspection"]["molecular_state"]["state"]["phase"] == "cleaved_duplex"
        assert viewed["inspection"]["option_label"] == variant["option_labels"][0]
        assert viewed["query_digest"] == summary["query_digest"]
        assert choices.json_bytes == before


def test_preview_cannot_bypass_the_focused_pin(loop_pool):
    pool = loop_pool
    query = {"result_digest": pool.result_digest, "stage": "hairpin", "focus": "loop"}
    summary = json.loads(construction.query_scaffold_variants(pool, query).json_bytes)
    first, other = summary["variants"]
    choices = construction.query_scaffold_variants(
        pool, {**query, "pins": [{"neighborhood": "loop", "variant_ids": [first["variant_id"]]}]}
    )
    pinned = json.loads(choices.json_bytes)
    request = {
        "result_digest": pool.result_digest,
        "query_digest": pinned["query_digest"],
        "variant_id": other["variant_id"],
        "state": "endpoint",
    }
    result = json.loads(construction.preview_scaffold_variant(pool, choices, request).json_bytes)
    assert result["status"] == "excluded_by_constraints"
    assert result["inspection"] is None
    assert result["candidates"] == []
    with pytest.raises(ValueError, match="compatible"):
        construction.preview_scaffold_variant(
            pool, choices, {**request, "option_label": other["option_labels"][0]}
        )


def test_comparison_focus_preserves_stem_position_with_new_material_ancestry(loop_pool):
    pool = loop_pool
    choices = construction.query_scaffold_variants(
        pool, {"result_digest": pool.result_digest, "stage": "hairpin", "focus": "loop"}
    )
    summary = json.loads(choices.json_bytes)
    first, second = summary["variants"]
    request = {
        "result_digest": pool.result_digest,
        "query_digest": summary["query_digest"],
        "variant_id": first["variant_id"],
        "state": "hairpin",
    }
    before = json.loads(construction.preview_scaffold_variant(pool, choices, request).json_bytes)
    base = next(
        b for b in before["inspection"]["molecular_state"]["bases"] if b["region"] == "stem_primary"
    )
    after = json.loads(
        construction.preview_scaffold_variant(
            pool,
            choices,
            {
                **request,
                "variant_id": second["variant_id"],
                "focus": base["address"],
                "focus_option_label": before["option_label"],
                "focus_mode": "comparison",
                "view_from": {"option_label": before["option_label"], "state": "hairpin"},
            },
        ).json_bytes
    )
    assert after["focus_transfer"] == "comparison_position"
    focused = next(
        b
        for b in after["inspection"]["molecular_state"]["bases"]
        if b["focus_relation"] == "same_address"
    )
    assert focused["base"] == base["base"]
    assert focused["region"] == base["region"]
    assert focused["origin"]["origin_id"] != base["origin"]["origin_id"]
    assert any(
        link["reference"] == base["address"] and link["target"] == focused["address"]
        for link in after["transition"]["links"]
    )
    assert after["query_digest"] == before["query_digest"]
    assert after["selected_product"] is None


def test_preview_cli_matches_api_and_rejects_stale_inputs(loop_options, tmp_path):
    pool = construction.load_scaffold_exploration(loop_options[0])
    choices = construction.query_scaffold_variants(
        pool, {"result_digest": pool.result_digest, "stage": "hairpin", "focus": "loop"}
    )
    summary = json.loads(choices.json_bytes)
    request = {
        "result_digest": pool.result_digest,
        "query_digest": summary["query_digest"],
        "variant_id": summary["variants"][0]["variant_id"],
        "state": "cleaved_duplex",
        "focus_mode": "comparison",
        "view_from": {"option_label": summary["compatible_options"][0], "state": "duplex"},
    }
    previous = tmp_path / "previous.json"
    previous.write_text(json.dumps(request["view_from"]))
    expected = construction.preview_scaffold_variant(pool, choices, request)
    saved = choices.write(tmp_path / "choices")
    result = CliRunner().invoke(
        app,
        [
            "construction",
            "preview-variant",
            str(loop_options[0]),
            str(saved),
            "--variant",
            request["variant_id"],
            "--state",
            request["state"],
            "--focus-mode",
            "comparison",
            "--view-from",
            str(previous),
            "--out",
            str(tmp_path / "preview"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert (tmp_path / "preview/summary.json").read_bytes() == expected.json_bytes
    for edit, message in [
        ({"query_digest": "sha256:" + "0" * 64}, "Stale"),
        ({"variant_id": "sha256:" + "0" * 64}, "Unknown"),
        ({"relax": True}, "Extra inputs"),
    ]:
        with pytest.raises(ValueError, match=message):
            construction.preview_scaffold_variant(pool, choices, {**request, **edit})


def test_focus_requires_shared_material_identity_across_preparations(loop_pool):
    pool = loop_pool
    choices = construction.query_scaffold_variants(
        pool, {"result_digest": pool.result_digest, "stage": "hairpin", "focus": "loop"}
    )
    summary = json.loads(choices.json_bytes)
    variants = summary["variants"]
    request = {
        "result_digest": pool.result_digest,
        "query_digest": summary["query_digest"],
        "variant_id": variants[0]["variant_id"],
        "state": "hairpin",
    }
    first = json.loads(construction.preview_scaffold_variant(pool, choices, request).json_bytes)
    for role, status in [
        ("ligation_adapter", "shared_material"),
        ("source_oligo", "cleared_no_verified_correspondence"),
    ]:
        # Source provenance is exposed through the prepared duplex role in this fixture.
        base = next(
            b
            for b in first["inspection"]["molecular_state"]["bases"]
            if (
                b["material_role"] == role
                if role == "ligation_adapter"
                else b["neighborhood"] == "loop"
            )
        )
        next_request = {
            **request,
            "variant_id": variants[1]["variant_id"],
            "state": "clone_ready_duplex",
            "focus": base["address"],
            "focus_option_label": first["option_label"],
        }
        viewed = json.loads(
            construction.preview_scaffold_variant(pool, choices, next_request).json_bytes
        )
        assert viewed["status"] == "preview_available"
        assert viewed["focus_transfer"] == status
        assert bool(viewed["inspection"]["molecular_state"]["focus"]) == (
            status == "shared_material"
        )
