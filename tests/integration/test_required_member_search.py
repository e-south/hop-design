"""Required selectors guide one bounded search budget rather than post-filtering it."""

import json
from pathlib import Path

from hop_design import construction


def ttc_request(tmp_path, *, duplicate=False):
    value = json.loads(Path("examples/scaffold-comparison/grouped.json").read_bytes())
    value.update(schema="hop.comparison-brief/v3", purpose="distinct_substrates")
    value.pop("groups")
    value.pop("between_groups")
    value["required_members"] = [{"name": "required-ttc", "loop_sequence": "TTC"}]
    if duplicate:
        value["required_members"].append({"name": "another-name", "loop_sequence": "TTC"})
    request = value["discovery"]
    request["product"]["foldback"]["geometry"].update(
        loop_lengths_nt=[3], loop_sequences=["AAA", "ATA", "GAA", "TTC"]
    )
    request["product"]["foldback"]["search"].update(
        stop="result_quota", result_quota=1, max_realizations=1
    )
    request["max_branches"] = 1
    request["max_continuations_per_branch"] = 1
    path = tmp_path / "brief.json"
    path.write_text(json.dumps(value))
    return path


def test_required_ttc_precedes_optional_words_under_unchanged_budget(tmp_path):
    path = ttc_request(tmp_path)
    original = path.read_bytes()
    packet = construction.execute_scaffold_comparison(path)
    result = json.loads(packet.json_bytes)
    assert result["status"] == "comparison_available"
    assert {o["loop_sequence"] for o in result["options"]} == {"TTC"}
    assert result["coverage"]["evaluated_branches"] == 1
    assert result["coverage"]["exploration_complete"] is False
    assert result["search_schedule"]["tasks"][0]["purpose"] == "required"
    assert any(t["status"] == "unexamined" for t in result["search_schedule"]["tasks"])
    assert path.read_bytes() == original
    out = packet.write(tmp_path / "out")
    saved = json.loads((out / "discovery/intent/request.json").read_bytes())
    assert saved["product"]["foldback"]["geometry"]["loop_sequences"] == [
        "AAA",
        "ATA",
        "GAA",
        "TTC",
    ]
    assert saved["required_targets"][0]["loop_sequence"] == "TTC"
    selected = construction.select_scaffold_comparison(
        out, set_label="set-0001", baseline="required-ttc"
    )
    assert len(json.loads(selected.json_bytes)["members"]) == 1


def test_duplicate_selectors_share_search_effort_and_insufficient_members_remain_visible(tmp_path):
    path = ttc_request(tmp_path, duplicate=True)
    result = json.loads(construction.execute_scaffold_comparison(path).json_bytes)
    assert len(result["options"]) == 1
    assert result["coverage"]["evaluated_branches"] == 1
    assert len(result["search_schedule"]["targets"]) == 1
    assert result["sets"] == []
    assert result["group_coverage"]["rejections"] == {"repeated_preparation": 1}
    assert all(len(m["option_labels"]) == 1 for m in result["members"])


def test_renaming_members_preserves_execution_and_broader_selector_reuses_options(tmp_path):
    path = ttc_request(tmp_path)
    first = construction.execute_scaffold_comparison(path)
    value = json.loads(path.read_bytes())
    value["required_members"][0]["name"] = "new-name"
    path.write_text(json.dumps(value))
    renamed = construction.execute_scaffold_comparison(path)
    assert (
        dict(first._files)["discovery/summary.json"]
        == dict(renamed._files)["discovery/summary.json"]
    )
    value["required_members"].append({"name": "any-three", "dimensions": {"loop_nt": 3}})
    path.write_text(json.dumps(value))
    result = json.loads(construction.execute_scaffold_comparison(path).json_bytes)
    assert result["coverage"]["evaluated_branches"] == 1
    reused = [t for t in result["search_schedule"]["tasks"] if t["status"] == "reused"]
    assert reused
    assert all(all(t["reused_options"].values()) for t in reused)


def test_required_search_does_not_relax_hard_domains(tmp_path):
    path = ttc_request(tmp_path)
    value = json.loads(path.read_bytes())
    value["required_members"][0]["loop_sequence"] = "CCC"
    path.write_text(json.dumps(value))
    result = json.loads(construction.execute_scaffold_comparison(path).json_bytes)
    assert result["execution"] == "not_started"
    assert result["status"] == "conflicting_requirements"


def test_earlier_comparison_versions_keep_their_search_meaning(tmp_path):
    path = ttc_request(tmp_path)
    value = json.loads(path.read_bytes())
    value.update(
        schema="hop.comparison-brief/v2", purpose="grouped_substrates", between_groups="distinct"
    )
    value["groups"] = [
        {"name": "ttc", "members": ["required-ttc"], "product_relationship": "identical"}
    ]
    path.write_text(json.dumps(value))
    result = json.loads(construction.execute_scaffold_comparison(path).json_bytes)
    assert {o["loop_sequence"] for o in result["options"]} == {"AAA"}
    assert result["sets"] == []
    assert "search_schedule" not in result
