"""Inspection follows one complete preparation without editing molecular intent."""

import json

import pytest
from typer.testing import CliRunner

from hop_design import construction
from hop_design.cli import app


def test_pinned_preparation_can_inspect_endpoint_without_changing_choices(loop_pool):
    pool = loop_pool
    request = {"result_digest": pool.result_digest, "stage": "hairpin", "focus": "loop"}
    initial = json.loads(construction.query_scaffold_variants(pool, request).json_bytes)
    variant = next(v for v in initial["variants"] if v["sequences"][0]["sequence"] == "TTTC")
    label = variant["option_labels"][0]
    choices = construction.query_scaffold_variants(
        pool,
        {
            **request,
            "reference": label,
            "pins": [{"neighborhood": "loop", "variant_ids": [variant["variant_id"]]}],
            "controls": [{"stage": "hairpin", "property": "non_loop_sequences"}],
        },
    )
    before = choices.json_bytes
    query_digest = json.loads(before)["query_digest"]
    for state in ("endpoint", "hairpin", "endpoint"):
        inspected = construction.inspect_scaffold_variant(
            pool,
            choices,
            {
                "result_digest": pool.result_digest,
                "query_digest": query_digest,
                "option_label": label,
                "state": state,
            },
        )
        observed = json.loads(inspected.json_bytes)
        assert observed["query_digest"] == query_digest
        assert observed["option_label"] == label
        assert observed["inspection"]["state"] == state
        assert observed["selected_product"] is None
        assert choices.json_bytes == before
        assert b"data-neighborhood=" in inspected.svg_bytes


def test_inspection_lists_and_follows_recorded_states_and_source_lineage(loop_pool):
    pool = loop_pool
    choices = construction.query_scaffold_variants(
        pool, {"result_digest": pool.result_digest, "stage": "hairpin", "focus": "loop"}
    )
    query = json.loads(choices.json_bytes)
    request = {
        "result_digest": pool.result_digest,
        "query_digest": query["query_digest"],
        "option_label": query["compatible_options"][0],
        "state": "hairpin",
    }
    first = json.loads(construction.inspect_scaffold_variant(pool, choices, request).json_bytes)
    states = first["molecular_state"]["available_states"]
    assert [s["phase"] for s in states] == [
        "source_ssdna",
        "duplex",
        "cleaved_duplex",
        "denatured_fragments",
        "selected_fragments",
        "annealed_complex",
        "foldback_closed_hairpin",
        "adapter_annealed",
        "adapter_ligated",
        "hairpin_pcr_duplex",
        "clone_ready_duplex",
    ]
    focus = next(
        b["address"] for b in first["molecular_state"]["bases"] if b["neighborhood"] == "stem"
    )
    for state in states:
        viewed = json.loads(
            construction.inspect_scaffold_variant(
                pool, choices, {**request, "state": state["state_id"], "focus": focus}
            ).json_bytes
        )
        molecular = viewed["molecular_state"]
        assert molecular["state"]["state_id"] == state["state_id"]
        assert len(molecular["bases"]) == sum(
            len(s["sequence"]) for s in molecular["state"]["molecules"]
        )
        assert molecular["focus_status"] == "mapped"
    endpoint = json.loads(
        construction.inspect_scaffold_variant(
            pool, choices, {**request, "state": "endpoint", "focus": focus}
        ).json_bytes
    )["molecular_state"]
    assert any(b["neighborhood"] == "loop" for b in endpoint["bases"])
    assert any(b["focus_relation"] == "copied" for b in endpoint["bases"])


@pytest.mark.parametrize(
    "change, message",
    [
        ({"query_digest": "sha256:" + "0" * 64}, "Stale"),
        ({"state": "invented-state"}, "Unknown|unavailable"),
        ({"option_label": "missing-preparation"}, "compatible|Unknown"),
        ({"option_label": ["one", "two"]}, "string"),
        ({"focus": {"state_id": "missing", "strand_id": "missing", "index": 0}}, "address|state"),
    ],
)
def test_inspection_rejects_unbound_requests(loop_pool, change, message):
    pool = loop_pool
    choices = construction.query_scaffold_variants(
        pool, {"result_digest": pool.result_digest, "stage": "hairpin", "focus": "loop"}
    )
    summary = json.loads(choices.json_bytes)
    request = {
        "result_digest": pool.result_digest,
        "query_digest": summary["query_digest"],
        "option_label": summary["compatible_options"][0],
        "state": "hairpin",
    }
    with pytest.raises(ValueError, match=message):
        construction.inspect_scaffold_variant(pool, choices, {**request, **change})


def test_cli_inspection_uses_saved_choices(loop_options, tmp_path):
    path, _ = loop_options
    pool = construction.load_scaffold_exploration(path)
    choices = construction.query_scaffold_variants(
        pool, {"result_digest": pool.result_digest, "stage": "hairpin", "focus": "loop"}
    )
    saved = choices.write(tmp_path / "choices")
    label = json.loads(choices.json_bytes)["compatible_options"][0]
    result = CliRunner().invoke(
        app,
        [
            "construction",
            "inspect-variant",
            str(path),
            str(saved),
            "--option",
            label,
            "--state",
            "endpoint",
            "--out",
            str(tmp_path / "view"),
        ],
    )
    assert result.exit_code == 0, result.output
    projected = json.loads((tmp_path / "view/summary.json").read_bytes())
    assert projected["query_digest"] == json.loads(choices.json_bytes)["query_digest"]
    assert projected["inspection"]["state"] == "endpoint"


def test_focus_distinguishes_removed_from_not_yet_present_material(loop_pool):
    pool = loop_pool
    choices = construction.query_scaffold_variants(
        pool, {"result_digest": pool.result_digest, "stage": "hairpin", "focus": "loop"}
    )
    query = json.loads(choices.json_bytes)
    request = {
        "result_digest": pool.result_digest,
        "query_digest": query["query_digest"],
        "option_label": query["compatible_options"][0],
    }

    def inspect(state, focus=None):
        return json.loads(
            construction.inspect_scaffold_variant(
                pool, choices, {**request, "state": state, "focus": focus}
            ).json_bytes
        )["molecular_state"]

    source = inspect("source_material")
    # The source's 5-prime handle is discarded by this declared release route.
    removed = inspect("endpoint", source["bases"][0]["address"])
    assert removed["focus_status"] == "removed"
    hairpin = inspect("hairpin")
    adapter = next(b for b in hairpin["bases"] if b["material_role"] == "ligation_adapter")
    earlier = inspect("source_material", adapter["address"])
    assert earlier["focus_status"] == "not_yet_present"
    assert all(b["focus_relation"] is None for b in earlier["bases"])


def test_endpoint_overhang_picking_targets_interfaces_not_their_source_region(loop_pool):
    pool = loop_pool
    choices = construction.query_scaffold_variants(
        pool, {"result_digest": pool.result_digest, "stage": "hairpin", "focus": "loop"}
    )
    query = json.loads(choices.json_bytes)
    request = {
        "result_digest": pool.result_digest,
        "query_digest": query["query_digest"],
        "option_label": query["compatible_options"][0],
        "state": "endpoint",
    }
    packet = construction.inspect_scaffold_variant(pool, choices, request)
    bases = json.loads(packet.json_bytes)["molecular_state"]["bases"]
    ends = [b for b in bases if b["neighborhood"] == "interfaces"]
    assert len(ends) == 8  # Two recorded four-base, 5-prime overhangs.
    assert {(b["strand_index"], b["address"]["index"]) for b in ends} == {
        (strand, index) for strand in (0, 1) for index in range(4)
    }
    assert packet.svg_bytes.count(b'data-neighborhood="interfaces"') == 8
