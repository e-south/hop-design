"""Exact loop composition changes the constructed molecule, not just its label."""

import json
from pathlib import Path

import pytest

from hop_design import construction


def sequence_brief(tmp_path):
    value = json.loads(Path("examples/scaffold-comparison/grouped.json").read_bytes())
    value["discovery"]["product"]["foldback"]["geometry"].update(
        loop_lengths_nt=[3], loop_sequences=["AAA", "ATA"]
    )
    for member in value["required_members"]:
        member["dimensions"]["loop_nt"] = 3
        member["loop_sequence"] = "AAA" if member["name"].startswith("loop3") else "ATA"
    path = tmp_path / "sequences.json"
    path.write_text(json.dumps(value))
    return path


def test_loop_words_reach_complete_selected_products(tmp_path):
    path = sequence_brief(tmp_path)
    packet = construction.execute_scaffold_comparison(path)
    summary = json.loads(packet.json_bytes)
    assert summary["status"] == "comparison_available"
    assert {o["loop_sequence"] for o in summary["options"]} == {"AAA", "ATA"}
    out = packet.write(tmp_path / "results")
    chosen = construction.select_scaffold_comparison(
        out, set_label="set-0001", baseline="loop3-bsai"
    )
    files = dict(chosen._files)
    for name, word in [
        ("loop3-bsai", "AAA"),
        ("loop3-bsmbi", "AAA"),
        ("loop4-bsai", "ATA"),
        ("loop4-bsmbi", "ATA"),
    ]:
        portrait = json.loads(files[f"members/{name}/portrait/projection.json"])
        span = portrait["loop_span"]
        sequence = portrait["state"]["molecules"][0]["sequence"]
        assert sequence[span["start"]["offset"] : span["end"]["offset"]] == word


@pytest.mark.parametrize("mutation", ["length", "alphabet", "inherited-domain"])
def test_loop_intent_conflicts_are_explained_before_search(tmp_path, mutation):
    path = sequence_brief(tmp_path)
    request = json.loads(path.read_bytes())
    if mutation == "length":
        request["required_members"][0]["loop_sequence"] = "AAAA"
    elif mutation == "alphabet":
        request["required_members"][0]["loop_sequence"] = "AAN"
    else:
        request["required_members"][0]["loop_sequence"] = "CCC"
    path.write_text(json.dumps(request))
    if mutation in ("length", "alphabet"):
        with pytest.raises(ValueError):
            construction.prepare_scaffold_comparison(path)
    else:
        preview = json.loads(construction.prepare_scaffold_comparison(path).json_bytes)
        assert preview["status"] == "conflicting_requirements"
        assert any("loop_sequence" in c["requested_field"] for c in preview["conflicts"])


def test_loop_word_search_retains_incomplete_coverage(tmp_path):
    path = sequence_brief(tmp_path)
    request = json.loads(path.read_bytes())
    request["discovery"]["max_continuations_per_branch"] = 1
    path.write_text(json.dumps(request))
    summary = json.loads(construction.execute_scaffold_comparison(path).json_bytes)
    assert summary["sets"] == []
    assert summary["coverage"]["unexamined_pairs"] > 0
    assert len(summary["members"]) == 4


def test_loop_words_and_dimensions_intersect_without_discarding_requirements(tmp_path):
    path = sequence_brief(tmp_path)
    request = json.loads(path.read_bytes())
    geometry = request["discovery"]["product"]["foldback"]["geometry"]
    geometry.update(loop_lengths_nt=[3, 4], loop_sequences=["AAA", "AAAA"])
    for member in request["required_members"]:
        member["loop_sequence"] = "AAA"
    request["discovery"]["scaffold"]["loop_nt"] = {"minimum": 3, "maximum": 3}
    path.write_text(json.dumps(request))
    summary = json.loads(construction.prepare_scaffold_comparison(path).json_bytes)
    assert summary["status"] == "ready"
    branches = summary["discovery"]["branches"]
    assert branches
    # The source expands only permitted words consistent with the hard dimensions.
    assert summary["dimensions"]["loop_nt"]["effective_values"] == [3]


def test_exact_loop_word_can_reject_one_complete_preparation_method(tmp_path):
    path = sequence_brief(tmp_path)
    request = json.loads(path.read_bytes())
    request["discovery"]["product"]["foldback"]["geometry"].update(
        loop_lengths_nt=[6], loop_sequences=["GGTCTC"]
    )
    request["required_members"] = request["required_members"][:2]
    request["groups"] = request["groups"][:1]
    for member in request["required_members"]:
        member.update(loop_sequence="GGTCTC", dimensions={"loop_nt": 6})
    path.write_text(json.dumps(request))
    summary = json.loads(construction.execute_scaffold_comparison(path).json_bytes)
    assert summary["sets"] == []
    assert summary["members"][0]["option_labels"] == []
    assert len(summary["members"][1]["option_labels"]) == 1
    assert summary["options"][0]["loop_sequence"] == "GGTCTC"
    assert summary["coverage"]["unexamined_pairs"] == 0
    failure = summary["examined_failures"][0]
    assert failure["scope"] == "selected_combination"
    assert failure["rejection_reasons"] == ["global-actionable-site-conflict"]
    site = failure["actionable_site_conflicts"][0]
    assert site["enzyme_name"] == "BsaI-HFv2"
    assert site["recognition_sequence"] == "GGTCTC"
    assert site["molecule_id"] == "complete-hairpin-pcr"
