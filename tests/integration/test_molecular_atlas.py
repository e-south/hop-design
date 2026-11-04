"""The route atlas composes exact inspections without changing molecular intent."""

import json
from xml.etree import ElementTree as ET

import pytest
from typer.testing import CliRunner

from hop_design import construction
from hop_design.cli import app


def atlas_request(pool):
    choices = construction.query_scaffold_variants(
        pool, {"result_digest": pool.result_digest, "stage": "hairpin", "focus": "loop"}
    )
    summary = json.loads(choices.json_bytes)
    return choices, {
        "result_digest": pool.result_digest,
        "query_digest": summary["query_digest"],
        "option_label": summary["compatible_options"][0],
    }


def test_atlas_composes_all_exact_states_and_state_qualified_occurrences(loop_pool):
    choices, request = atlas_request(loop_pool)
    original = choices.json_bytes
    packet = construction.inspect_scaffold_atlas(loop_pool, choices, request)
    assert isinstance(packet, construction.ScaffoldAtlas)
    result = json.loads(packet.json_bytes)
    atlas = result["atlas"]
    assert result["selected_product"] is None
    assert result["query_digest"] == request["query_digest"]
    assert choices.json_bytes == original
    assert len(atlas["states"]) == 11
    assert len(atlas["transitions"]) == 10
    occurrences = set()
    unqualified = []
    for state in atlas["states"]:
        inspected = construction.inspect_scaffold_variant(
            loop_pool, choices, {**request, "state": state["state"]["state_id"]}
        )
        assert state == json.loads(inspected.json_bytes)["molecular_state"]
        for base in state["bases"]:
            address = base["address"]
            key = (atlas["materialized_realization_id"], *address.values())
            assert key not in occurrences
            occurrences.add(key)
            unqualified.append((address["strand_id"], address["index"]))
    assert len(set(unqualified)) < len(unqualified)  # Names recur across processing states.
    svg = ET.fromstring(packet.svg_bytes)
    drawn = [g for g in svg.iter() if "data-base-index" in g.attrib]
    assert len(drawn) == len(occurrences)
    assert len({g.attrib["data-occurrence"] for g in drawn}) == len(occurrences)
    assert {g.attrib["data-state-id"] for g in drawn} == {
        s["state"]["state_id"] for s in atlas["states"]
    }
    anchors = {}
    for row in (g for g in svg.iter() if "data-atlas-state" in g.attrib):
        stem = [g for g in row.iter() if g.attrib.get("data-neighborhood") == "stem"]
        x = min(float(next(e for e in g if e.tag.endswith("}rect")).attrib["x"]) for g in stem)
        column = row.attrib["data-atlas-column"]
        if column != "full":
            anchors.setdefault(column, []).append(x + float(row.attrib.get("data-atlas-x", 0)))
    assert all(len(set(values)) == 1 for values in anchors.values())
    assert len(atlas["inputs"]) == 5  # Source primers, adapter, hairpin PCR primers.
    assert all(i["material"]["sequence_5prime"] for i in atlas["inputs"])
    assert all(i["authority_id"] for i in atlas["inputs"])
    assert sum(i["binding_context"] == "derived_template" for i in atlas["inputs"]) == 1
    bindings = [e for e in svg.iter() if "data-primer-binding" in e.attrib]
    assert len(bindings) == 2  # Future templates are staged at introduction, not falsely bound.
    assert {e.attrib["data-primer-binding"] for e in bindings} == {
        i["material_use"]["use_id"]
        for i in atlas["inputs"]
        if i["binding_state_id"] == i["pre_state_id"]
    }
    assert any(t["correspondence"]["unmapped_reference"] for t in atlas["transitions"])
    assert any(
        link["relation"] == "copied"
        for t in atlas["transitions"]
        for link in t["correspondence"]["links"]
    )


def test_all_state_browsing_preserves_query_and_transfers_verified_positions(loop_pool):
    choices, request = atlas_request(loop_pool)
    summary = json.loads(choices.json_bytes)
    variants = [v for v in summary["variants"] if len(v["option_labels"]) == 1]
    first, second = variants[:2]
    initial = construction.preview_scaffold_variant(
        loop_pool,
        choices,
        {
            **{k: request[k] for k in ("result_digest", "query_digest")},
            "variant_id": first["variant_id"],
            "state": "all",
        },
    )
    result = json.loads(initial.json_bytes)
    assert result["status"] == "preview_available"
    assert len(result["inspection"]["atlas"]["states"]) == 11
    focus = next(
        b["address"]
        for b in result["inspection"]["atlas"]["states"][0]["bases"]
        if b["neighborhood"] == "stem"
    )
    changed = json.loads(
        construction.preview_scaffold_variant(
            loop_pool,
            choices,
            {
                "result_digest": request["result_digest"],
                "query_digest": request["query_digest"],
                "variant_id": second["variant_id"],
                "state": "all",
                "focus": focus,
                "focus_option_label": first["option_labels"][0],
                "focus_mode": "comparison",
                "view_from": {"option_label": first["option_labels"][0], "state": "all"},
            },
        ).json_bytes
    )
    assert changed["status"] == "preview_available"
    assert changed["focus_transfer"] in ("shared_material", "comparison_position")
    assert len(changed["atlas_transitions"]) == 11
    assert all(s["focus_status"] == "mapped" for s in changed["inspection"]["atlas"]["states"])
    assert changed["query_digest"] == request["query_digest"]


@pytest.mark.parametrize(
    "change, message",
    [
        ({"query_digest": "sha256:" + "0" * 64}, "Stale"),
        ({"option_label": "absent"}, "compatible"),
        ({"focus": {"state_id": "absent", "strand_id": "absent", "index": 0}}, "state"),
    ],
)
def test_atlas_rejects_unbound_requests(loop_pool, change, message):
    choices, request = atlas_request(loop_pool)
    with pytest.raises(ValueError, match=message):
        construction.inspect_scaffold_atlas(loop_pool, choices, {**request, **change})


def test_cli_atlas_matches_public_api(loop_options, loop_pool, tmp_path):
    choices, request = atlas_request(loop_pool)
    path = choices.write(tmp_path / "choices")
    result = CliRunner().invoke(
        app,
        [
            "construction",
            "atlas",
            str(loop_options[0]),
            str(path),
            "--option",
            request["option_label"],
            "--out",
            str(tmp_path / "atlas"),
        ],
    )
    assert result.exit_code == 0, result.output
    expected = construction.inspect_scaffold_atlas(loop_pool, choices, request)
    assert (tmp_path / "atlas/summary.json").read_bytes() == expected.json_bytes
    assert (tmp_path / "atlas/projection.svg").read_bytes() == expected.svg_bytes
    assert (tmp_path / "atlas/projection.pdf").read_bytes() == expected.pdf_bytes
    layout = json.loads((tmp_path / "atlas/print-layout.json").read_bytes())
    assert layout["minimum_sequence_font_pt"] >= 8
    assert len(layout["pages"]) > 1
    pages = sorted((tmp_path / "atlas/pages").glob("*.svg"))
    assert len(pages) == len(layout["pages"])
    printed = [
        e.get("data-occurrence")
        for page in pages
        for e in ET.fromstring(page.read_bytes()).iter()
        if e.get("data-occurrence")
    ]
    original = [
        e.get("data-occurrence")
        for e in ET.fromstring(expected.svg_bytes).iter()
        if e.get("data-occurrence")
    ]
    # Horizontal continuations change DOM order across paired strands; addresses
    # still identify exactly the same unique nucleotide occurrences.
    assert sorted(printed) == sorted(original)
    assert len(printed) == len(set(printed))
    assert all(page["width_pt"] == 504 and page["height_pt"] <= 720 for page in layout["pages"])
    report = (tmp_path / "atlas/report.md").read_text()
    assert "7-inch pages" in report
    assert "coordinate continuations" in report
    assert "longest recorded strand" not in report


def test_atlas_distinguishes_generating_constraints_achieved_dimensions_and_comparison(loop_pool):
    initial, _ = atlas_request(loop_pool)
    value = json.loads(initial.json_bytes)
    reference, target = value["compatible_options"][:2]
    choices = construction.query_scaffold_variants(
        loop_pool, {**value["query"], "reference": reference}
    )
    query = json.loads(choices.json_bytes)
    packet = construction.inspect_scaffold_atlas(
        loop_pool,
        choices,
        {
            "result_digest": loop_pool.result_digest,
            "query_digest": query["query_digest"],
            "option_label": target,
        },
    )
    result = json.loads(packet.json_bytes)
    assert result["envelope"]["observed"]["loop_nt"] == 4
    assert result["envelope"]["generating_domains"]["foldback"]["loop_lengths_nt"] == [4]
    assert result["envelope"]["observed_stage_id"] in {
        s["state"]["state_id"] for s in result["atlas"]["states"]
    }
    assert result["comparison"]["reference"] == reference
    assert result["comparison"]["material_roles"]
    assert b"source reverse primer" in packet.svg_bytes
    assert b"source reverse primer \xc2\xb7 changed versus reference" in packet.svg_bytes
    assert b"Source oligo changed versus reference" in packet.svg_bytes
    svg = ET.fromstring(packet.svg_bytes)
    assert all(
        float(e.attrib["data-region-width"]) == 13
        for e in svg.iter()
        if "data-region-fill" in e.attrib
    )
    assert len(result["comparison"]["transitions"]) == 11
    assert dict(packet._files)["request.json"] == loop_pool._request
    assert "readiness" in result["envelope"]
    nick_names = {v["name"] for v in result["envelope"]["method_permissions"]["basal_nick"]}
    assert not any(name.startswith("BsaI") for name in nick_names)
